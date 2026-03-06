"""
MetricsService for computing and querying analytics metrics.

Handles:
- Turn-level metric computation
- Session-level aggregation
- Daily rollups
- Querying metrics for dashboards
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
from django.db.models import Avg, Count, Sum, Q, F, Max, Min
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings

from analytics.models import TurnMetric, SessionMetric, DailyMetric
from analytics.evaluators.registry import registry
from agent.models import Conversation, Message


# Get analytics configuration
ANALYTICS_CONFIG = getattr(settings, 'ANALYTICS_CONFIG', {})
ENABLE_LOCAL_MODELS = ANALYTICS_CONFIG.get('enable_local_models', True)
ENABLE_LLM_JUDGES = ANALYTICS_CONFIG.get('enable_llm_judges', True)
LLM_SAMPLING_RATE = ANALYTICS_CONFIG.get('llm_sampling_rate', 0.1)


class MetricsService:
    """
    Service for computing and querying analytics metrics.

    Usage:
        service = MetricsService()
        service.compute_turn_metrics(message, stage=3)
        service.compute_session_metrics(conversation)
        service.rollup_daily_metrics(date.today())
    """

    def compute_turn_metrics(
        self,
        message: Message,
        stage: int = 3
    ) -> List[TurnMetric]:
        """
        Compute metrics for a single turn (message).

        Args:
            message: Message instance (must be assistant role)
            stage: Max evaluation stage to run (1=rules, 2=ML, 3=LLM)

        Returns:
            List of created TurnMetric instances
        """
        if message.role != 'assistant':
            # Only evaluate assistant messages
            return []

        conversation = message.conversation
        agent = conversation.agent

        # Get previous message (user message)
        messages = list(conversation.messages.order_by('created_at'))
        message_index = messages.index(message)
        user_message = messages[message_index - 1] if message_index > 0 else None

        # Compute response latency (seconds between user message and assistant reply)
        latency_seconds = None
        if user_message:
            delta = message.created_at - user_message.created_at
            latency_seconds = delta.total_seconds()

        # Prepare turn data for evaluators
        turn_data = {
            'user_text': user_message.text if user_message else '',
            'assistant_text': message.text,
            'context': message.metadata.get('retrieved_context', '') if message.metadata else '',
            # Business metric inputs
            'answer_failed': message.answer_failed,
            'user_rating': message.rating,
            'latency_seconds': latency_seconds,
        }

        # Get metrics to compute based on stage
        turn_metrics = registry.list(level='turn')

        # Filter by stage and settings
        if not ENABLE_LOCAL_MODELS:
            turn_metrics = [m for m in turn_metrics if m.stage != 2]
        if not ENABLE_LLM_JUDGES:
            turn_metrics = [m for m in turn_metrics if m.stage != 3]

        turn_metrics = [m for m in turn_metrics if m.stage <= stage]

        results = []

        for metric_def in turn_metrics:
            if not metric_def.compute_turn:
                continue

            try:
                value = metric_def.compute_turn(turn_data)

                # Skip sentinel values (-1.0 = not applicable / not sampled)
                if value == -1.0:
                    continue

                # Save to database
                turn_metric = TurnMetric.objects.create(
                    conversation=conversation,
                    message=message,
                    metric_name=metric_def.name,
                    value=value,
                    agent_id=agent.id,
                    agent_version=agent.version,
                    model=agent.config.get('model', {}).get('name', ''),
                    timestamp=message.created_at
                )

                results.append(turn_metric)

            except Exception as e:
                print(f"Error computing {metric_def.name} for message {message.id}: {e}")
                # Continue with other metrics even if one fails

        return results

    def compute_session_metrics(
        self,
        conversation: Conversation
    ) -> List[SessionMetric]:
        """
        Compute session-level metrics for a conversation.

        This includes:
        1. Reducing turn metrics to session averages
        2. Computing session-only metrics (e.g., repetition)

        Args:
            conversation: Conversation instance

        Returns:
            List of created SessionMetric instances
        """
        agent = conversation.agent
        results = []

        # 1. Reduce turn metrics to session averages
        turn_metric_names = set(
            TurnMetric.objects.filter(
                conversation=conversation
            ).values_list('metric_name', flat=True).distinct()
        )

        for metric_name in turn_metric_names:
            turn_metrics = TurnMetric.objects.filter(
                conversation=conversation,
                metric_name=metric_name
            )

            if turn_metrics.exists():
                avg_value = turn_metrics.aggregate(Avg('value'))['value__avg']
                count = turn_metrics.count()

                session_metric = SessionMetric.objects.create(
                    conversation=conversation,
                    metric_name=f"{metric_name}_mean",
                    value=avg_value,
                    count=count,
                    agent_id=agent.id,
                    agent_version=agent.version,
                    model=agent.config.get('model', {}).get('name', ''),
                    timestamp=conversation.created_at
                )

                results.append(session_metric)

        # 2. Compute session-level metrics
        messages = list(conversation.messages.order_by('created_at'))
        session_data = {
            'messages': [
                {'role': msg.role, 'text': msg.text}
                for msg in messages
            ],
            'duration_seconds': (
                conversation.updated_at - conversation.created_at
            ).total_seconds() if conversation.updated_at else 0,
            'turn_metrics': self._get_turn_metrics_dict(conversation)
        }

        session_metrics = registry.list(level='session')

        for metric_def in session_metrics:
            if not metric_def.reduce_session:
                continue

            try:
                value = metric_def.reduce_session(session_data)

                # Skip sentinel values (-1.0 = not applicable, e.g. no rated turns)
                if value == -1.0:
                    continue

                session_metric = SessionMetric.objects.create(
                    conversation=conversation,
                    metric_name=metric_def.name,
                    value=value,
                    count=1,
                    agent_id=agent.id,
                    agent_version=agent.version,
                    model=agent.config.get('model', {}).get('name', ''),
                    timestamp=conversation.created_at
                )

                results.append(session_metric)

            except Exception as e:
                print(f"Error computing {metric_def.name} for conversation {conversation.id}: {e}")

        return results

    def rollup_daily_metrics(
        self,
        target_date: date,
        agent_id: Optional[int] = None
    ) -> List[DailyMetric]:
        """
        Rollup session metrics to daily aggregates.

        Args:
            target_date: Date to rollup
            agent_id: Optional agent filter

        Returns:
            List of created/updated DailyMetric instances
        """
        start_of_day = timezone.make_aware(
            datetime.combine(target_date, datetime.min.time())
        )
        end_of_day = start_of_day + timedelta(days=1)

        # Build filters
        filters = Q(timestamp__gte=start_of_day, timestamp__lt=end_of_day)
        if agent_id:
            filters &= Q(agent_id=agent_id)

        # Get all session metrics for the day
        session_metrics = SessionMetric.objects.filter(filters)

        if not session_metrics.exists():
            return []

        # Group by metric_name, agent_id, model
        grouped = session_metrics.values(
            'metric_name', 'agent_id', 'model'
        ).annotate(
            avg_value=Avg('value'),
            total_count=Sum('count')
        )

        results = []

        for group in grouped:
            daily_metric, created = DailyMetric.objects.update_or_create(
                date=target_date,
                metric_name=group['metric_name'],
                agent_id=group['agent_id'],
                model=group['model'],
                defaults={
                    'value': group['avg_value'],
                    'count': group['total_count']
                }
            )

            results.append(daily_metric)

        return results

    def _get_turn_metrics_dict(self, conversation: Conversation) -> Dict[str, List[float]]:
        """
        Get turn metrics organized by metric name.

        Returns:
            Dict mapping metric_name to list of values
        """
        turn_metrics = TurnMetric.objects.filter(
            conversation=conversation
        ).values('metric_name', 'value')

        result = {}
        for tm in turn_metrics:
            metric_name = tm['metric_name']
            if metric_name not in result:
                result[metric_name] = []
            result[metric_name].append(tm['value'])

        return result

    # Query methods for dashboards

    def get_kpis(
        self,
        start_date: date,
        end_date: date,
        agent_id: Optional[int] = None,
        agent_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Get key performance indicators for dashboard.

        Args:
            start_date: Start date
            end_date: End date
            agent_id: Optional single agent filter
            agent_ids: Optional list of agent IDs to filter

        Returns:
            Dict with KPI values and metadata
        """
        # Normalize agent_id(s) to list
        if agent_ids:
            agent_filter = agent_ids
        elif agent_id:
            agent_filter = [agent_id]
        else:
            agent_filter = None

        cache_key = f"kpis:{start_date}:{end_date}:{'-'.join(str(a) for a in agent_filter) if agent_filter else 'all'}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        # Build filters
        filters = Q(date__gte=start_date, date__lte=end_date)
        if agent_filter:
            filters &= Q(agent_id__in=agent_filter)

        # Query metrics
        kpis = {
            # ── AI quality proxies ───────────────────────────────────────────
            'answer_relevance': self._get_metric_avg(
                filters, 'answer_relevance_mean'
            ),
            'faithfulness': self._get_metric_avg(
                filters, 'faithfulness_mean'
            ),
            'coherence': self._get_metric_avg(
                filters, 'coherence_mean'
            ),
            'toxicity': self._get_metric_avg(
                filters, 'toxicity_mean'
            ),
            'composite_quality': self._get_metric_avg(
                filters, 'composite_quality'
            ),
            # ── Business / operational metrics ───────────────────────────────
            'answer_failure_rate': self._get_metric_avg(
                filters, 'answer_failure_rate'
            ),
            'knowledge_gap_rate': self._get_metric_avg(
                filters, 'knowledge_gap_rate'
            ),
            'user_satisfaction_score': self._get_metric_avg(
                filters, 'user_satisfaction_score'
            ),
            'user_abandonment_rate': self._get_metric_avg(
                filters, 'user_abandonment'
            ),
            'avg_session_depth': self._get_metric_avg(
                filters, 'session_depth'
            ),
            'product_surface_rate': self._get_metric_avg(
                filters, 'product_surface_mean'
            ),
            'avg_response_latency': self._get_metric_avg(
                filters, 'response_latency_mean'
            ),
            'total_conversations': (
                SessionMetric.objects.filter(
                    timestamp__date__gte=start_date,
                    timestamp__date__lte=end_date,
                    agent_id__in=agent_filter,
                ).values('conversation').distinct().count()
                if agent_filter else
                SessionMetric.objects.filter(
                    timestamp__date__gte=start_date,
                    timestamp__date__lte=end_date,
                ).values('conversation').distinct().count()
            ),
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }

        # Cache for 5 minutes
        cache.set(cache_key, kpis, 300)

        return kpis

    def get_timeseries(
        self,
        metric_name: str,
        start_date: date,
        end_date: date,
        agent_id: Optional[int] = None,
        granularity: str = 'daily'
    ) -> List[Dict[str, Any]]:
        """
        Get time series data for a metric.

        Args:
            metric_name: Metric to query
            start_date: Start date
            end_date: End date
            agent_id: Optional agent filter
            granularity: 'daily' or 'weekly'

        Returns:
            List of dicts with date and value
        """
        filters = Q(
            date__gte=start_date,
            date__lte=end_date,
            metric_name=metric_name
        )
        if agent_id:
            filters &= Q(agent_id=agent_id)

        daily_metrics = DailyMetric.objects.filter(filters).values(
            'date', 'value', 'count'
        ).order_by('date')

        return list(daily_metrics)

    def get_distribution(
        self,
        metric_name: str,
        start_date: date,
        end_date: date,
        agent_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get distribution/histogram of a metric.

        Args:
            metric_name: Metric to query
            start_date: Start date
            end_date: End date
            agent_id: Optional agent filter

        Returns:
            Dict with percentiles and histogram data
        """
        # Get all values (use __date lookups for inclusive day-boundary matching)
        filters = Q(
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date,
            metric_name=metric_name
        )
        if agent_id:
            filters &= Q(agent_id=agent_id)

        values = list(
            SessionMetric.objects.filter(filters).values_list('value', flat=True)
        )

        if not values:
            return {'stats': {}, 'values': []}

        # Compute stats
        import numpy as np
        stats = {
            'mean': float(np.mean(values)),
            'median': float(np.median(values)),
            'std': float(np.std(values)),
            'min': float(np.min(values)),
            'max': float(np.max(values)),
            'p10': float(np.percentile(values, 10)),
            'p25': float(np.percentile(values, 25)),
            'p75': float(np.percentile(values, 75)),
            'p90': float(np.percentile(values, 90)),
            'count': len(values)
        }

        return {
            'stats': stats,
            'values': values[:1000]  # Limit for performance
        }

    def _get_metric_avg(self, filters: Q, metric_name: str) -> Optional[float]:
        """Helper to get average of a metric"""
        result = DailyMetric.objects.filter(
            filters, metric_name=metric_name
        ).aggregate(avg=Avg('value'))

        return result['avg']

    def get_conversations_with_metrics(
        self,
        start_date: date,
        end_date: date,
        agent_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get conversations with their metrics.

        Args:
            start_date: Start date
            end_date: End date
            agent_id: Optional agent filter
            limit: Max conversations to return
            offset: Pagination offset

        Returns:
            Dict with conversations and metrics
        """
        # Build filters
        filters = Q(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        if agent_id:
            filters &= Q(agent_id=agent_id)

        # Get conversations with metrics
        conversations = Conversation.objects.filter(filters).select_related(
            'agent', 'user'
        ).prefetch_related('session_metrics').order_by('-created_at')[offset:offset + limit]

        results = []

        for conv in conversations:
            # Get metrics for this conversation
            metrics = {}
            for sm in conv.session_metrics.all():
                metrics[sm.metric_name] = sm.value

            results.append({
                'id': conv.id,
                'agent_id': conv.agent_id,
                'agent_name': conv.agent.name,
                'created_at': conv.started_at,
                'message_count': conv.messages.count(),
                'metrics': metrics
            })

        total_count = Conversation.objects.filter(filters).count()

        return {
            'results': results,
            'count': len(results),
            'total': total_count,
            'has_more': total_count > (offset + limit)
        }

    def get_session_metrics(self, conversation_id: str) -> Dict[str, float]:
        """
        Get all metrics for a specific conversation.

        Args:
            conversation_id: Conversation UUID

        Returns:
            Dict mapping metric_name to value
        """
        metrics = SessionMetric.objects.filter(
            conversation_id=conversation_id
        ).values('metric_name', 'value')

        return {m['metric_name']: m['value'] for m in metrics}

    def get_turn_metrics(self, message_id: int) -> Dict[str, float]:
        """
        Get all metrics for a specific message.

        Args:
            message_id: Message ID

        Returns:
            Dict mapping metric_name to value
        """
        metrics = TurnMetric.objects.filter(
            message_id=message_id
        ).values('metric_name', 'value')

        return {m['metric_name']: m['value'] for m in metrics}

    def get_outliers(
        self,
        metric_name: str,
        start_date: date,
        end_date: date,
        agent_id: Optional[int] = None,
        threshold: float = 90,
        direction: str = 'both',
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get conversations that are outliers on a specific metric.

        Args:
            metric_name: Metric to analyze
            start_date: Start date
            end_date: End date
            agent_id: Optional agent filter
            threshold: Percentile threshold (e.g., 90 = top/bottom 10%)
            direction: 'high', 'low', or 'both'
            limit: Max results to return

        Returns:
            List of outlier conversations with metrics
        """
        # Build filters (use __date lookups for inclusive day-boundary matching)
        filters = Q(
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date,
            metric_name=metric_name
        )
        if agent_id:
            filters &= Q(agent_id=agent_id)

        # Get all values for percentile calculation
        values = list(
            SessionMetric.objects.filter(filters).values_list('value', flat=True)
        )

        if not values:
            return []

        # Calculate percentile thresholds
        import numpy as np
        high_threshold = np.percentile(values, threshold)
        low_threshold = np.percentile(values, 100 - threshold)

        # Get outlier conversations
        outlier_filters = filters

        if direction == 'high':
            outlier_filters &= Q(value__gte=high_threshold)
        elif direction == 'low':
            outlier_filters &= Q(value__lte=low_threshold)
        else:  # both
            outlier_filters &= Q(value__gte=high_threshold) | Q(value__lte=low_threshold)

        outliers = SessionMetric.objects.filter(
            outlier_filters
        ).select_related('conversation', 'conversation__agent').order_by('-value')[:limit]

        results = []

        for session_metric in outliers:
            conv = session_metric.conversation
            percentile = float(
                (np.searchsorted(sorted(values), session_metric.value) / len(values)) * 100
            )

            results.append({
                'conversation_id': conv.id,
                'agent_id': conv.agent_id,
                'agent_name': conv.agent.name,
                'metric_name': metric_name,
                'value': session_metric.value,
                'percentile': percentile,
                'created_at': conv.started_at,
                'message_count': conv.messages.count()
            })

        return results
