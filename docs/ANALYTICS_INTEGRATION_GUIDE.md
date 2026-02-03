# Analytics Integration Guide
## Porting Chat-Verifier Analytics to Agent Builder Platform

**Last Updated:** January 20, 2026

---

## Overview

This guide details how to integrate the comprehensive analytics system from the chat-verifier dashboard_backend into the Agent Builder Platform. The goal is to provide workspace-scoped analytics with real-time and batch processing capabilities.

---

## Table of Contents

1. [Integration Strategy](#integration-strategy)
2. [Database Schema Migration](#database-schema-migration)
3. [Porting Evaluators](#porting-evaluators)
4. [Metrics Service Implementation](#metrics-service-implementation)
5. [API Endpoints](#api-endpoints)
6. [Celery Tasks](#celery-tasks)
7. [Real-Time Metrics](#real-time-metrics)
8. [Testing Strategy](#testing-strategy)

---

## Integration Strategy

### Approach: Embedded Integration

**Rationale:**
- Single codebase for easier maintenance
- Shared authentication and multi-tenancy
- No network overhead between services
- Simpler deployment

### Key Differences from Chat-Verifier

| Aspect | Chat-Verifier | Agent Builder |
|--------|---------------|---------------|
| Framework | FastAPI | Django + DRF |
| Data Source | External API (Kogents) | Internal (Conversation model) |
| Multi-tenancy | None | Workspace-based |
| Real-time | Batch only | WebSocket + Batch |
| ORM | SQLAlchemy | Django ORM |

---

## Database Schema Migration

### Step 1: Create Analytics App

```bash
cd server
python manage.py startapp analytics
```

### Step 2: Define Metrics Models

**File:** `server/analytics/models/metrics.py`
```python
from django.db import models
from django.contrib.postgres.indexes import BrinIndex
from workspace.models import Workspace
from agent.models import Conversation, Message, Agent


class TurnMetric(models.Model):
    """Turn-level metrics (per message)"""

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='turn_metrics'
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='turn_metrics'
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='metrics'
    )

    metric_name = models.CharField(max_length=100, db_index=True)
    value = models.FloatField()

    # Context dimensions for filtering
    agent_id = models.UUIDField()
    agent_version = models.IntegerField(default=1)
    model = models.CharField(max_length=100, blank=True)

    # Optional dimensions
    country = models.CharField(max_length=10, blank=True)
    channel = models.CharField(max_length=50, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'analytics_turn_metrics'
        indexes = [
            models.Index(fields=['workspace', 'timestamp']),
            models.Index(fields=['conversation', 'metric_name']),
            models.Index(fields=['metric_name', 'timestamp']),
            models.Index(fields=['agent_id', 'metric_name']),
            BrinIndex(fields=['timestamp']),  # Efficient for time-series
        ]


class SessionMetric(models.Model):
    """Session-level aggregated metrics"""

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='session_metrics'
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='session_metrics'
    )

    metric_name = models.CharField(max_length=100, db_index=True)
    value = models.FloatField()
    count = models.IntegerField(default=1)  # For averaging

    # Context
    agent_id = models.UUIDField()
    agent_version = models.IntegerField(default=1)
    model = models.CharField(max_length=100, blank=True)

    # Filters
    country = models.CharField(max_length=10, blank=True)
    channel = models.CharField(max_length=50, blank=True)

    timestamp = models.DateTimeField(db_index=True)

    class Meta:
        db_table = 'analytics_session_metrics'
        indexes = [
            models.Index(fields=['workspace', 'timestamp']),
            models.Index(fields=['metric_name', 'agent_id', 'timestamp']),
            BrinIndex(fields=['timestamp']),
        ]


class DailyMetric(models.Model):
    """Daily aggregated metrics"""

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='daily_metrics'
    )

    date = models.DateField(db_index=True)
    metric_name = models.CharField(max_length=100, db_index=True)

    value = models.FloatField()
    count = models.IntegerField()  # Sample size

    # Dimensions for filtering
    agent_id = models.UUIDField(null=True, blank=True)
    model = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=10, blank=True)
    channel = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_daily_metrics'
        unique_together = [
            ('workspace', 'date', 'metric_name', 'agent_id', 'model', 'country', 'channel')
        ]
        indexes = [
            models.Index(fields=['workspace', 'date']),
            models.Index(fields=['date', 'metric_name']),
            models.Index(fields=['agent_id', 'date']),
        ]


class WeeklyMetric(models.Model):
    """Weekly aggregated metrics"""

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='weekly_metrics'
    )

    week_start = models.DateField(db_index=True)
    metric_name = models.CharField(max_length=100)

    value = models.FloatField()
    count = models.IntegerField()

    agent_id = models.UUIDField(null=True, blank=True)
    model = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'analytics_weekly_metrics'
        unique_together = [
            ('workspace', 'week_start', 'metric_name', 'agent_id', 'model')
        ]


class MetricAlert(models.Model):
    """Threshold-based alerts"""

    STATUS_OK = 'ok'
    STATUS_WARN = 'warn'
    STATUS_CRITICAL = 'critical'

    STATUS_CHOICES = [
        (STATUS_OK, 'OK'),
        (STATUS_WARN, 'Warning'),
        (STATUS_CRITICAL, 'Critical'),
    ]

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    agent_id = models.UUIDField(null=True, blank=True)

    metric_name = models.CharField(max_length=100)
    threshold_type = models.CharField(max_length=20)  # 'above', 'below'
    threshold_value = models.FloatField()

    current_value = models.FloatField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    triggered_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'analytics_alerts'
        ordering = ['-triggered_at']
```

### Step 3: Evaluation Job Tracking

**File:** `server/analytics/models/evaluation.py`
```python
import uuid
from django.db import models
from workspace.models import Workspace


class EvaluationJob(models.Model):
    """Track evaluation pipeline jobs"""

    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)

    job_type = models.CharField(max_length=50)  # 'turn_evaluation', 'session_rollup', 'daily_rollup'
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    # Date range being processed
    start_date = models.DateField()
    end_date = models.DateField()

    # Progress tracking
    total_items = models.IntegerField(default=0)
    processed_items = models.IntegerField(default=0)
    failed_items = models.IntegerField(default=0)

    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Error tracking
    error_message = models.TextField(blank=True)

    # Configuration
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'analytics_evaluation_jobs'
        ordering = ['-created_at']
```

### Step 4: Create Migrations

```bash
python manage.py makemigrations analytics
python manage.py migrate analytics
```

---

## Porting Evaluators

### Step 1: Create Evaluator Registry

**File:** `server/analytics/evaluators/registry.py`
```python
from typing import Dict, List, Callable
from dataclasses import dataclass


@dataclass
class MetricDefinition:
    """Definition of a metric"""
    name: str
    display_name: str
    description: str
    level: str  # 'turn', 'session', 'daily'
    stage: int  # 1=rule-based, 2=local-ml, 3=llm-judge

    compute_turn: Callable = None  # Function to compute turn-level metric
    reduce_session: Callable = None  # Function to aggregate turns to session
    rollup_daily: Callable = None  # Function to aggregate sessions to daily


class MetricsRegistry:
    """Central registry for all metrics"""

    def __init__(self):
        self._metrics: Dict[str, MetricDefinition] = {}

    def register(self, metric: MetricDefinition):
        """Register a metric"""
        self._metrics[metric.name] = metric

    def get(self, name: str) -> MetricDefinition:
        """Get metric by name"""
        return self._metrics.get(name)

    def list(self, level: str = None, stage: int = None) -> List[MetricDefinition]:
        """List all metrics, optionally filtered"""
        metrics = list(self._metrics.values())

        if level:
            metrics = [m for m in metrics if m.level == level]

        if stage:
            metrics = [m for m in metrics if m.stage == stage]

        return metrics


# Global registry instance
registry = MetricsRegistry()
```

### Step 2: Rule-Based Evaluators (Stage 1)

**File:** `server/analytics/evaluators/rule_based.py`
```python
import re
from typing import Dict, Any
from langdetect import detect, LangDetectException


def detect_pii(text: str) -> bool:
    """Detect Personally Identifiable Information"""

    patterns = [
        # Email
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        # Phone (US format)
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        # SSN
        r'\b\d{3}-\d{2}-\d{4}\b',
        # Credit card (basic)
        r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
    ]

    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True

    return False


def detect_language(text: str) -> str:
    """Detect language of text"""
    try:
        return detect(text)
    except LangDetectException:
        return 'unknown'


def count_language_switches(messages: list) -> int:
    """Count language switches in conversation"""
    if not messages:
        return 0

    languages = [detect_language(msg['text']) for msg in messages]
    switches = sum(1 for i in range(1, len(languages)) if languages[i] != languages[i-1])

    return switches


def compute_pii_flag(turn_data: Dict[str, Any]) -> float:
    """Compute PII flag for a turn"""
    assistant_message = turn_data.get('assistant_text', '')
    return 1.0 if detect_pii(assistant_message) else 0.0


def compute_language_switches(session_data: Dict[str, Any]) -> float:
    """Compute language switches for session"""
    messages = session_data.get('messages', [])
    return float(count_language_switches(messages))


# Register metrics
from analytics.evaluators.registry import registry, MetricDefinition

registry.register(MetricDefinition(
    name='pii_flag',
    display_name='PII Detected',
    description='Whether personally identifiable information was detected',
    level='turn',
    stage=1,
    compute_turn=compute_pii_flag
))

registry.register(MetricDefinition(
    name='language_switches',
    display_name='Language Switches',
    description='Number of language changes in conversation',
    level='session',
    stage=1,
    reduce_session=compute_language_switches
))
```

### Step 3: Local ML Evaluators (Stage 2)

**File:** `server/analytics/evaluators/local_ml.py`
```python
from typing import Dict, Any
import numpy as np

# Lazy load heavy models
_toxicity_model = None
_sentence_transformer = None


def get_toxicity_model():
    """Lazy load toxicity model"""
    global _toxicity_model
    if _toxicity_model is None:
        from detoxify import Detoxify
        _toxicity_model = Detoxify('original')
    return _toxicity_model


def get_sentence_transformer():
    """Lazy load sentence transformer"""
    global _sentence_transformer
    if _sentence_transformer is None:
        from sentence_transformers import SentenceTransformer
        _sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
    return _sentence_transformer


def compute_toxicity(turn_data: Dict[str, Any]) -> float:
    """Compute toxicity score for a turn"""
    assistant_text = turn_data.get('assistant_text', '')

    if not assistant_text:
        return 0.0

    model = get_toxicity_model()
    results = model.predict(assistant_text)

    # Return max toxicity across all categories
    toxicity = max(
        results.get('toxicity', 0),
        results.get('severe_toxicity', 0),
        results.get('obscene', 0),
        results.get('threat', 0),
        results.get('insult', 0),
        results.get('identity_attack', 0)
    )

    return float(toxicity)


def compute_coherence(turn_data: Dict[str, Any]) -> float:
    """Compute coherence score using sentence embeddings"""
    user_text = turn_data.get('user_text', '')
    assistant_text = turn_data.get('assistant_text', '')

    if not user_text or not assistant_text:
        return 0.5  # Neutral

    model = get_sentence_transformer()

    # Get embeddings
    embeddings = model.encode([user_text, assistant_text])

    # Cosine similarity
    similarity = np.dot(embeddings[0], embeddings[1]) / (
        np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
    )

    # Scale to 0-1
    coherence = (similarity + 1) / 2

    return float(coherence)


def compute_repetition(session_data: Dict[str, Any]) -> float:
    """Compute repetition score for session"""
    messages = session_data.get('messages', [])
    assistant_messages = [
        msg['text'] for msg in messages
        if msg['role'] == 'assistant'
    ]

    if len(assistant_messages) < 2:
        return 0.0

    # Simple n-gram overlap check
    def get_trigrams(text):
        words = text.lower().split()
        return set(tuple(words[i:i+3]) for i in range(len(words)-2))

    all_trigrams = []
    unique_trigrams = set()

    for msg in assistant_messages:
        trigrams = get_trigrams(msg)
        all_trigrams.extend(trigrams)
        unique_trigrams.update(trigrams)

    if not all_trigrams:
        return 0.0

    # Repetition = 1 - (unique / total)
    repetition = 1.0 - (len(unique_trigrams) / len(all_trigrams))

    return float(repetition)


# Register metrics
from analytics.evaluators.registry import registry, MetricDefinition

registry.register(MetricDefinition(
    name='toxicity',
    display_name='Toxicity Score',
    description='Toxicity level of assistant response',
    level='turn',
    stage=2,
    compute_turn=compute_toxicity
))

registry.register(MetricDefinition(
    name='coherence',
    display_name='Coherence',
    description='How well response relates to user query',
    level='turn',
    stage=2,
    compute_turn=compute_coherence
))

registry.register(MetricDefinition(
    name='repetition',
    display_name='Repetition',
    description='Amount of repetitive content in conversation',
    level='session',
    stage=2,
    reduce_session=compute_repetition
))
```

### Step 4: LLM-as-Judge Evaluators (Stage 3)

**File:** `server/analytics/evaluators/llm_judges.py`
```python
from typing import Dict, Any
import openai
from django.conf import settings
import json

# Configure OpenAI
openai.api_key = settings.OPENAI_API_KEY


def compute_answer_relevance(turn_data: Dict[str, Any]) -> float:
    """Evaluate answer relevance using GPT-4o-mini"""

    user_text = turn_data.get('user_text', '')
    assistant_text = turn_data.get('assistant_text', '')

    if not user_text or not assistant_text:
        return 0.5

    prompt = f"""Rate the relevance of the assistant's response to the user's question on a scale of 0.0 to 1.0.

User Question: {user_text}

Assistant Response: {assistant_text}

Respond with ONLY a JSON object in this format:
{{"relevance": 0.85, "reasoning": "brief explanation"}}"""

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an impartial judge evaluating chatbot responses."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=150
        )

        result = json.loads(response.choices[0].message.content)
        return float(result.get('relevance', 0.5))

    except Exception as e:
        print(f"Error in answer_relevance evaluation: {e}")
        return 0.5  # Neutral on error


def compute_faithfulness(turn_data: Dict[str, Any]) -> float:
    """Evaluate faithfulness to retrieved context"""

    context = turn_data.get('context', '')
    assistant_text = turn_data.get('assistant_text', '')

    if not context or not assistant_text:
        return 1.0  # No context = no grounding required

    prompt = f"""Evaluate if the assistant's response is faithful to the provided context. Rate from 0.0 (completely fabricated) to 1.0 (fully grounded).

Context:
{context}

Assistant Response:
{assistant_text}

Respond with ONLY a JSON object:
{{"faithfulness": 0.9, "unsupported_claims": ["claim1"], "reasoning": "explanation"}}"""

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an impartial judge evaluating factual accuracy."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=200
        )

        result = json.loads(response.choices[0].message.content)
        return float(result.get('faithfulness', 1.0))

    except Exception as e:
        print(f"Error in faithfulness evaluation: {e}")
        return 1.0


# Register metrics
from analytics.evaluators.registry import registry, MetricDefinition

registry.register(MetricDefinition(
    name='answer_relevance',
    display_name='Answer Relevance',
    description='How well response answers the question (LLM-judged)',
    level='turn',
    stage=3,
    compute_turn=compute_answer_relevance
))

registry.register(MetricDefinition(
    name='faithfulness',
    display_name='Faithfulness',
    description='How well response is grounded in context (LLM-judged)',
    level='turn',
    stage=3,
    compute_turn=compute_faithfulness
))
```

---

## Metrics Service Implementation

**File:** `server/analytics/services/metrics_service.py`
```python
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from django.db.models import Avg, Count, Sum, Q, F
from django.utils import timezone
from django.core.cache import cache

from analytics.models import TurnMetric, SessionMetric, DailyMetric
from analytics.evaluators.registry import registry
from workspace.models import Workspace
from agent.models import Conversation, Message


class MetricsService:
    """Service for computing and querying metrics"""

    def __init__(self, workspace: Workspace):
        self.workspace = workspace

    def compute_turn_metrics(self, message: Message, stage: int = 3):
        """
        Compute metrics for a single turn (message)

        Args:
            message: Message instance
            stage: Max evaluation stage (1=rules, 2=local-ml, 3=llm-judge)
        """
        # Prepare turn data
        conversation = message.conversation
        messages = list(conversation.messages.order_by('created_at'))
        message_index = messages.index(message)

        # Get user message (previous message)
        user_message = messages[message_index - 1] if message_index > 0 else None

        turn_data = {
            'user_text': user_message.text if user_message else '',
            'assistant_text': message.text,
            'context': message.metadata.get('retrieved_context', '') if message.metadata else '',
        }

        # Get turn-level metrics up to specified stage
        turn_metrics = registry.list(level='turn')
        turn_metrics = [m for m in turn_metrics if m.stage <= stage]

        results = []

        for metric_def in turn_metrics:
            if metric_def.compute_turn:
                try:
                    value = metric_def.compute_turn(turn_data)

                    # Save to database
                    turn_metric = TurnMetric.objects.create(
                        workspace=self.workspace,
                        conversation=conversation,
                        message=message,
                        metric_name=metric_def.name,
                        value=value,
                        agent_id=conversation.agent_id,
                        agent_version=conversation.agent.version,
                        model=conversation.agent.config.get('model', {}).get('name', ''),
                        timestamp=message.created_at
                    )

                    results.append(turn_metric)

                except Exception as e:
                    print(f"Error computing {metric_def.name}: {e}")

        return results

    def compute_session_metrics(self, conversation: Conversation):
        """Compute session-level metrics for a conversation"""

        # Prepare session data
        messages = list(conversation.messages.order_by('created_at'))

        session_data = {
            'messages': [
                {'role': msg.role, 'text': msg.text}
                for msg in messages
            ],
            'duration_seconds': (
                conversation.updated_at - conversation.created_at
            ).total_seconds() if conversation.updated_at else 0,
        }

        # Get existing turn metrics for reduction
        turn_metrics = TurnMetric.objects.filter(
            conversation=conversation
        ).values('metric_name').annotate(
            avg_value=Avg('value'),
            count=Count('id')
        )

        results = []

        # Reduce turn metrics to session
        for tm in turn_metrics:
            SessionMetric.objects.create(
                workspace=self.workspace,
                conversation=conversation,
                metric_name=f"{tm['metric_name']}_mean",
                value=tm['avg_value'],
                count=tm['count'],
                agent_id=conversation.agent_id,
                agent_version=conversation.agent.version,
                model=conversation.agent.config.get('model', {}).get('name', ''),
                timestamp=conversation.created_at
            )

        # Compute session-level metrics
        session_metrics = registry.list(level='session')

        for metric_def in session_metrics:
            if metric_def.reduce_session:
                try:
                    value = metric_def.reduce_session(session_data)

                    session_metric = SessionMetric.objects.create(
                        workspace=self.workspace,
                        conversation=conversation,
                        metric_name=metric_def.name,
                        value=value,
                        count=1,
                        agent_id=conversation.agent_id,
                        agent_version=conversation.agent.version,
                        model=conversation.agent.config.get('model', {}).get('name', ''),
                        timestamp=conversation.created_at
                    )

                    results.append(session_metric)

                except Exception as e:
                    print(f"Error computing {metric_def.name}: {e}")

        return results

    def rollup_daily_metrics(self, date: datetime.date):
        """Rollup session metrics to daily aggregates"""

        start_of_day = timezone.make_aware(
            datetime.combine(date, datetime.min.time())
        )
        end_of_day = start_of_day + timedelta(days=1)

        # Get all session metrics for the day
        session_metrics = SessionMetric.objects.filter(
            workspace=self.workspace,
            timestamp__gte=start_of_day,
            timestamp__lt=end_of_day
        )

        # Group by metric_name and dimensions
        grouped = session_metrics.values(
            'metric_name', 'agent_id', 'model'
        ).annotate(
            avg_value=Avg('value'),
            total_count=Sum('count')
        )

        results = []

        for group in grouped:
            daily_metric, created = DailyMetric.objects.update_or_create(
                workspace=self.workspace,
                date=date,
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

    def get_kpis(
        self,
        start_date: datetime.date,
        end_date: datetime.date,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get key performance indicators for dashboard"""

        cache_key = f"kpis:{self.workspace.id}:{start_date}:{end_date}:{agent_id}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        # Build query filters
        filters = Q(
            workspace=self.workspace,
            date__gte=start_date,
            date__lte=end_date
        )

        if agent_id:
            filters &= Q(agent_id=agent_id)

        # Key metrics
        metrics = {
            'answer_relevance': DailyMetric.objects.filter(
                filters, metric_name='answer_relevance_mean'
            ).aggregate(avg=Avg('value'))['avg'],

            'faithfulness': DailyMetric.objects.filter(
                filters, metric_name='faithfulness_mean'
            ).aggregate(avg=Avg('value'))['avg'],

            'toxicity': DailyMetric.objects.filter(
                filters, metric_name='toxicity_mean'
            ).aggregate(avg=Avg('value'))['avg'],

            'coherence': DailyMetric.objects.filter(
                filters, metric_name='coherence_mean'
            ).aggregate(avg=Avg('value'))['avg'],

            'total_conversations': SessionMetric.objects.filter(
                workspace=self.workspace,
                timestamp__gte=start_date,
                timestamp__lte=end_date
            ).values('conversation').distinct().count(),
        }

        # Cache for 5 minutes
        cache.set(cache_key, metrics, 300)

        return metrics

    def get_timeseries(
        self,
        metric_name: str,
        start_date: datetime.date,
        end_date: datetime.date,
        agent_id: Optional[str] = None,
        granularity: str = 'daily'
    ) -> List[Dict[str, Any]]:
        """Get time series data for a metric"""

        filters = Q(
            workspace=self.workspace,
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
        start_date: datetime.date,
        end_date: datetime.date,
        agent_id: Optional[str] = None,
        bins: int = 20
    ) -> Dict[str, Any]:
        """Get distribution/histogram of a metric"""

        # Get all values
        filters = Q(
            workspace=self.workspace,
            conversation__created_at__gte=start_date,
            conversation__created_at__lte=end_date,
            metric_name=metric_name
        )

        if agent_id:
            filters &= Q(agent_id=agent_id)

        values = list(
            SessionMetric.objects.filter(filters).values_list('value', flat=True)
        )

        if not values:
            return {'bins': [], 'counts': [], 'stats': {}}

        # Compute histogram
        import numpy as np
        counts, bin_edges = np.histogram(values, bins=bins)

        # Compute stats
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
        }

        return {
            'bins': bin_edges.tolist(),
            'counts': counts.tolist(),
            'stats': stats
        }
```

I'll continue with the API endpoints, Celery tasks, and testing in the next response. Would you like me to continue?

