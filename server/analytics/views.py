"""
Analytics Dashboard API ViewSet.

Provides endpoints for:
- KPI overview
- Time series data
- Distribution/histograms
- Conversation lists with metrics
- Session detail/replay
- Metric catalog
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from django.db.models import Q
from datetime import date, timedelta
from typing import Optional

from analytics.serializers import (
    KPISerializer,
    TimeSeriesSerializer,
    DistributionSerializer,
    ConversationListSerializer,
    SessionDetailSerializer,
    MetricDefinitionSerializer,
    DateRangeFilterSerializer,
    MetricQuerySerializer,
    OutlierConversationSerializer,
)
from analytics.services import MetricsService
from analytics.evaluators.registry import registry
from agent.models import Agent, Conversation, Message


class AnalyticsDashboardViewSet(viewsets.ViewSet):
    """
    Analytics Dashboard API.

    Provides endpoints for retrieving agent performance metrics,
    conversation analytics, and quality insights.
    """

    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = MetricsService()

    def _get_user_agents(self):
        """Get all agents accessible to the current user via their datasets."""
        from catalog.models import DataSet
        user_dataset_ids = DataSet.objects.filter(
            users=self.request.user
        ).values_list('id', flat=True)
        return Agent.objects.filter(
            dataset_id__in=user_dataset_ids,
            deleted_at__isnull=True
        )

    def _validate_agent_access(self, agent_id: str) -> bool:
        """Check if user has access to the specified agent."""
        if not agent_id:
            return True

        return self._get_user_agents().filter(id=agent_id).exists()

    def _get_default_date_range(self):
        """Get default date range (last 30 days)."""
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        return start_date, end_date

    @action(detail=False, methods=['get'], url_path='overview')
    def overview(self, request):
        """
        GET /api/analytics/overview/

        Get KPI summary for dashboard overview.

        Query params:
        - start_date: YYYY-MM-DD (default: 30 days ago)
        - end_date: YYYY-MM-DD (default: today)
        - agent_id: UUID (optional, filter by specific agent)

        Returns:
        - Quality metrics (answer_relevance, faithfulness, coherence, etc.)
        - Volume metrics (total_conversations)
        - Date range used
        """
        # Parse query parameters
        filter_serializer = DateRangeFilterSerializer(data=request.query_params)

        if not filter_serializer.is_valid():
            # Use defaults if not provided
            start_date, end_date = self._get_default_date_range()
            agent_id = request.query_params.get('agent_id')
        else:
            start_date = filter_serializer.validated_data['start_date']
            end_date = filter_serializer.validated_data['end_date']
            agent_id = filter_serializer.validated_data.get('agent_id')

        # Validate agent access
        if agent_id and not self._validate_agent_access(agent_id):
            return Response(
                {'error': 'Agent not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Build cache key
        cache_key = f"analytics:kpi:{request.user.id}:{agent_id or 'all'}:{start_date}:{end_date}"

        # Try cache first (5-minute TTL)
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        # Compute KPIs
        kpis = self.service.get_kpis(
            start_date=start_date,
            end_date=end_date,
            agent_id=agent_id
        )

        # Filter to user's agents only
        if not agent_id:
            user_agent_ids = list(
                self._get_user_agents().values_list('id', flat=True)
            )
            # Re-compute with user's agents filter
            kpis = self.service.get_kpis(
                start_date=start_date,
                end_date=end_date,
                agent_ids=user_agent_ids
            )

        # Serialize
        serializer = KPISerializer(data=kpis)
        serializer.is_valid(raise_exception=True)

        # Cache for 5 minutes
        cache.set(cache_key, serializer.data, timeout=300)

        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='timeseries')
    def timeseries(self, request):
        """
        GET /api/analytics/timeseries/

        Get time series data for a specific metric.

        Query params:
        - metric_name: str (required)
        - start_date: YYYY-MM-DD (required)
        - end_date: YYYY-MM-DD (required)
        - agent_id: UUID (optional)
        - granularity: 'daily' or 'weekly' (default: daily)

        Returns:
        - metric_name
        - data: [{date, value, count}, ...]
        - date_range
        """
        # Validate query parameters
        query_serializer = MetricQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return Response(
                query_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        metric_name = query_serializer.validated_data['metric_name']
        start_date = query_serializer.validated_data['start_date']
        end_date = query_serializer.validated_data['end_date']
        agent_id = query_serializer.validated_data.get('agent_id')
        granularity = query_serializer.validated_data.get('granularity', 'daily')

        # Validate agent access
        if agent_id and not self._validate_agent_access(agent_id):
            return Response(
                {'error': 'Agent not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get time series data
        data = self.service.get_timeseries(
            metric_name=metric_name,
            start_date=start_date,
            end_date=end_date,
            agent_id=agent_id,
            granularity=granularity
        )

        # Build response
        response_data = {
            'metric_name': metric_name,
            'data': data,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }

        serializer = TimeSeriesSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='distribution')
    def distribution(self, request):
        """
        GET /api/analytics/distribution/

        Get distribution/histogram for a specific metric.

        Query params:
        - metric_name: str (required)
        - start_date: YYYY-MM-DD (required)
        - end_date: YYYY-MM-DD (required)
        - agent_id: UUID (optional)

        Returns:
        - metric_name
        - stats: {mean, median, std, min, max, p10, p25, p75, p90, count}
        - values: [list of all values]
        """
        query_serializer = MetricQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return Response(
                query_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        metric_name = query_serializer.validated_data['metric_name']
        start_date = query_serializer.validated_data['start_date']
        end_date = query_serializer.validated_data['end_date']
        agent_id = query_serializer.validated_data.get('agent_id')

        # Validate agent access
        if agent_id and not self._validate_agent_access(agent_id):
            return Response(
                {'error': 'Agent not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get distribution data
        distribution = self.service.get_distribution(
            metric_name=metric_name,
            start_date=start_date,
            end_date=end_date,
            agent_id=agent_id
        )
        distribution['metric_name'] = metric_name

        serializer = DistributionSerializer(data=distribution)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='conversations')
    def conversations(self, request):
        """
        GET /api/analytics/conversations/

        Get paginated list of conversations with metrics.

        Query params:
        - start_date: YYYY-MM-DD (optional)
        - end_date: YYYY-MM-DD (optional)
        - agent_id: UUID (optional)
        - page: int (default: 1)
        - page_size: int (default: 20, max: 100)
        - sort_by: str (default: created_at)
        - order: 'asc' or 'desc' (default: desc)

        Returns:
        - results: [{id, agent_id, agent_name, created_at, message_count, metrics}, ...]
        - count: int (items in this page)
        - total: int (total items)
        - has_more: bool
        """
        # Parse pagination
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        sort_by = request.query_params.get('sort_by', 'started_at')
        order = request.query_params.get('order', 'desc')

        # Parse filters
        agent_id = request.query_params.get('agent_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        # Validate agent access
        if agent_id and not self._validate_agent_access(agent_id):
            return Response(
                {'error': 'Agent not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Build queryset - only user's agents
        user_agent_ids = list(
            self._get_user_agents().values_list('id', flat=True)
        )

        queryset = Conversation.objects.filter(
            agent_id__in=user_agent_ids
        )

        # Apply filters
        if agent_id:
            queryset = queryset.filter(agent_id=agent_id)

        if start_date:
            queryset = queryset.filter(started_at__date__gte=start_date)

        if end_date:
            queryset = queryset.filter(started_at__date__lte=end_date)

        # Get total count
        total = queryset.count()

        # Apply sorting — map frontend field names to actual model fields
        field_map = {'created_at': 'started_at'}
        model_sort_by = field_map.get(sort_by, sort_by)
        sort_field = model_sort_by if order == 'asc' else f'-{model_sort_by}'
        queryset = queryset.order_by(sort_field)

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        conversations = queryset[start_idx:end_idx]

        # Build results with metrics
        results = []
        for conv in conversations:
            # Get session metrics for this conversation
            session_metrics = self.service.get_session_metrics(conv.id)

            results.append({
                'id': conv.id,
                'agent_id': conv.agent_id,
                'agent_name': conv.agent.name,
                'created_at': conv.started_at,
                'message_count': conv.messages.count(),
                'metrics': session_metrics
            })

        # Build response
        response_data = {
            'results': results,
            'count': len(results),
            'total': total,
            'has_more': end_idx < total
        }

        serializer = ConversationListSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='detail')
    def conversation_detail(self, request, pk=None):
        """
        GET /api/analytics/conversations/{id}/detail/

        Get detailed session with all messages and metrics (for replay).

        Returns:
        - conversation_id
        - agent_id, agent_name
        - created_at, updated_at
        - message_count
        - session_metrics: {metric_name: value}
        - messages: [{id, role, text, created_at, metrics, metadata}, ...]
        """
        # Get conversation
        try:
            conversation = Conversation.objects.get(id=pk)
        except (Conversation.DoesNotExist, ValueError, TypeError):
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate access — check via dataset membership
        from catalog.models import DataSet
        user_dataset_ids = DataSet.objects.filter(
            users=request.user
        ).values_list('id', flat=True)
        if conversation.data_set_id not in list(user_dataset_ids):
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get session metrics
        session_metrics = self.service.get_session_metrics(conversation.id)

        # Get all messages with turn metrics
        messages = []
        for msg in conversation.messages.all().order_by('created_at'):
            turn_metrics = self.service.get_turn_metrics(msg.id)

            messages.append({
                'id': msg.id,
                'role': msg.role,
                'text': msg.text,
                'created_at': msg.created_at,
                'metrics': turn_metrics,
                'metadata': getattr(msg, 'metadata', {})
            })

        # Build response
        response_data = {
            'conversation_id': conversation.id,
            'agent_id': conversation.agent_id,
            'agent_name': conversation.agent.name,
            'created_at': conversation.started_at,
            'updated_at': conversation.started_at,
            'message_count': len(messages),
            'session_metrics': session_metrics,
            'messages': messages
        }

        serializer = SessionDetailSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='metrics')
    def metrics_catalog(self, request):
        """
        GET /api/analytics/metrics/

        Get list of all available metrics with metadata.

        Query params:
        - level: 'turn' or 'session' (optional)
        - stage: 1, 2, or 3 (optional)

        Returns:
        - List of metric definitions with:
          - name
          - display_name
          - description
          - level (turn/session)
          - stage (1/2/3)
        """
        # Parse filters
        level = request.query_params.get('level')
        stage = request.query_params.get('stage')
        stage = int(stage) if stage else None

        # Get metrics from registry
        metrics = registry.list(level=level, stage=stage)

        # Convert to dict format
        metrics_data = [
            {
                'name': metric.name,
                'display_name': metric.display_name,
                'description': metric.description,
                'level': metric.level,
                'stage': metric.stage
            }
            for metric in metrics
        ]

        # Serialize
        serializer = MetricDefinitionSerializer(data=metrics_data, many=True)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='outliers')
    def outliers(self, request):
        """
        GET /api/analytics/outliers/

        Get conversations that are statistical outliers on specific metrics.

        Query params:
        - metric_name: str (required)
        - start_date: YYYY-MM-DD (required)
        - end_date: YYYY-MM-DD (required)
        - agent_id: UUID (optional)
        - threshold: float (default: 90, get top/bottom percentile)
        - direction: 'high' or 'low' (default: both)
        - limit: int (default: 10, max: 50)

        Returns:
        - List of outlier conversations with:
          - conversation_id
          - agent_name
          - metric_name
          - value
          - percentile
          - created_at
          - message_count
        """
        # Validate query parameters
        query_serializer = MetricQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return Response(
                query_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        metric_name = query_serializer.validated_data['metric_name']
        start_date = query_serializer.validated_data['start_date']
        end_date = query_serializer.validated_data['end_date']
        agent_id = query_serializer.validated_data.get('agent_id')

        # Parse additional params
        threshold = float(request.query_params.get('threshold', 90))
        direction = request.query_params.get('direction', 'both')
        limit = min(int(request.query_params.get('limit', 10)), 50)

        # Validate agent access
        if agent_id and not self._validate_agent_access(agent_id):
            return Response(
                {'error': 'Agent not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get outliers
        outliers = self.service.get_outliers(
            metric_name=metric_name,
            start_date=start_date,
            end_date=end_date,
            agent_id=agent_id,
            threshold=threshold,
            direction=direction,
            limit=limit
        )

        # Filter to user's agents
        user_agent_ids = set(
            self._get_user_agents().values_list('id', flat=True)
        )
        outliers = [
            o for o in outliers
            if o.get('agent_id') in user_agent_ids
        ]

        serializer = OutlierConversationSerializer(data=outliers, many=True)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)
