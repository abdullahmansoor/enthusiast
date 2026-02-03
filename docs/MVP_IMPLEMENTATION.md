# MVP Implementation Guide
## Agent Builder + Analytics (6 Weeks)

**Last Updated:** January 20, 2026

---

## Prerequisites

```bash
# System requirements
Python 3.11+
Node.js 20+
PostgreSQL 15+ with pgvector
Redis 7+
Docker & Docker Compose

# API Keys
OpenAI API key (required)
```

---

## Week 1: Foundation Setup

### Day 1-2: Project Cleanup and Dependencies

```bash
cd /home/anas/other-projs/enthusiast

# Create feature branch
git checkout -b feature/mvp-agent-builder-analytics

# Backend dependencies
cd server
pip install -r requirements.txt

# Add new dependencies for analytics
pip install detoxify sentence-transformers langdetect
pip install drf-spectacular  # Better API docs than drf-yasg

# Update requirements
pip freeze > requirements.txt
```

**Update `server/requirements.txt` to include:**
```
detoxify>=0.5.1
sentence-transformers>=2.2.2
langdetect>=1.0.9
drf-spectacular>=0.26.0
```

### Day 3: Update Agent Model

**File:** `server/agent/models/agent.py`

```python
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField

User = get_user_model()


class Agent(models.Model):
    """Enhanced agent with flexible JSON configuration"""

    STATUS_DRAFT = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_ARCHIVED = 'archived'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_ARCHIVED, 'Archived'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic info
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True)

    # Configuration (flexible JSON)
    config = models.JSONField(default=dict, blank=True)

    # Versioning
    version = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # User tracking
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_agents'
    )

    # Analytics (denormalized for performance)
    total_conversations = models.IntegerField(default=0)
    avg_rating = models.FloatField(null=True, blank=True)

    @staticmethod
    def get_default_config():
        """Return default agent configuration"""
        return {
            "model": {
                "provider": "openai",
                "name": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2000,
                "top_p": 1.0
            },
            "system_prompt": "You are a helpful AI assistant. Answer questions accurately and concisely.",
            "retrieval": {
                "enabled": True,
                "top_k": 5,
                "score_threshold": 0.7
            },
            "conversation_starters": [
                "How can I help you today?",
                "What would you like to know?"
            ],
            "constraints": {
                "max_conversation_length": 50,
                "max_response_tokens": 1000,
                "response_timeout_seconds": 30
            }
        }

    def save(self, *args, **kwargs):
        # Ensure config has default structure
        if not self.config:
            self.config = self.get_default_config()
        else:
            # Merge with defaults for missing keys
            default = self.get_default_config()
            for key in default:
                if key not in self.config:
                    self.config[key] = default[key]

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (v{self.version})"

    class Meta:
        db_table = 'agents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'deleted_at']),
            models.Index(fields=['created_at']),
        ]
```

**Create migration:**
```bash
python manage.py makemigrations agent
```

### Day 4-5: Create Analytics App Structure

```bash
cd server
python manage.py startapp analytics
```

**Create directory structure:**
```bash
mkdir -p analytics/models
mkdir -p analytics/evaluators
mkdir -p analytics/services
touch analytics/models/__init__.py
touch analytics/evaluators/__init__.py
touch analytics/services/__init__.py
```

**File:** `server/analytics/models/__init__.py`
```python
from .metrics import TurnMetric, SessionMetric, DailyMetric
from .evaluation import EvaluationJob

__all__ = [
    'TurnMetric',
    'SessionMetric',
    'DailyMetric',
    'EvaluationJob',
]
```

**File:** `server/analytics/models/metrics.py`
```python
from django.db import models
from django.contrib.postgres.indexes import BrinIndex
from agent.models import Conversation, Message, Agent


class TurnMetric(models.Model):
    """Turn-level metrics (per message)"""

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

    # Context
    agent_id = models.UUIDField()
    agent_version = models.IntegerField(default=1)
    model = models.CharField(max_length=100, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'analytics_turn_metrics'
        indexes = [
            models.Index(fields=['conversation', 'metric_name']),
            models.Index(fields=['metric_name', 'timestamp']),
            models.Index(fields=['agent_id', 'timestamp']),
            BrinIndex(fields=['timestamp']),
        ]


class SessionMetric(models.Model):
    """Session-level aggregated metrics"""

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='session_metrics',
        unique=False
    )

    metric_name = models.CharField(max_length=100, db_index=True)
    value = models.FloatField()
    count = models.IntegerField(default=1)

    # Context
    agent_id = models.UUIDField()
    agent_version = models.IntegerField(default=1)
    model = models.CharField(max_length=100, blank=True)

    timestamp = models.DateTimeField()

    class Meta:
        db_table = 'analytics_session_metrics'
        indexes = [
            models.Index(fields=['conversation', 'metric_name']),
            models.Index(fields=['agent_id', 'metric_name']),
            models.Index(fields=['timestamp']),
        ]


class DailyMetric(models.Model):
    """Daily aggregated metrics"""

    date = models.DateField(db_index=True)
    metric_name = models.CharField(max_length=100, db_index=True)

    value = models.FloatField()
    count = models.IntegerField()

    # Dimensions
    agent_id = models.UUIDField(null=True, blank=True)
    model = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_daily_metrics'
        unique_together = [('date', 'metric_name', 'agent_id', 'model')]
        indexes = [
            models.Index(fields=['date', 'metric_name']),
            models.Index(fields=['agent_id', 'date']),
        ]
```

**File:** `server/analytics/models/evaluation.py`
```python
import uuid
from django.db import models


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

    job_type = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    # Date range
    start_date = models.DateField()
    end_date = models.DateField()

    # Progress
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

**Add to `server/pecl/settings.py`:**
```python
INSTALLED_APPS = [
    # ... existing apps
    'analytics',
]

# Analytics settings
ANALYTICS_CONFIG = {
    'enable_local_models': True,  # Stage 2 evaluators
    'enable_llm_judges': True,    # Stage 3 evaluators
    'llm_sampling_rate': 0.1,     # 10% for cost control
    'async_evaluation': True,      # Don't block API responses
}
```

**Create migrations:**
```bash
python manage.py makemigrations analytics
python manage.py migrate
```

---

## Week 2: Agent Builder Backend

### Day 1-2: Enhanced Agent API

**File:** `server/agent/serializers.py` (Update or create)

```python
from rest_framework import serializers
from agent.models import Agent, Conversation, Message


class AgentConfigSerializer(serializers.Serializer):
    """Validate agent configuration"""
    model = serializers.DictField()
    system_prompt = serializers.CharField()
    retrieval = serializers.DictField(required=False)
    conversation_starters = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    constraints = serializers.DictField(required=False)


class AgentSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = Agent
        fields = [
            'id', 'name', 'description', 'avatar_url', 'config',
            'version', 'status', 'created_at', 'updated_at',
            'published_at', 'created_by', 'created_by_email',
            'total_conversations', 'avg_rating'
        ]
        read_only_fields = [
            'id', 'version', 'created_at', 'updated_at',
            'total_conversations', 'avg_rating'
        ]

    def validate_config(self, value):
        """Validate config structure"""
        serializer = AgentConfigSerializer(data=value)
        serializer.is_valid(raise_exception=True)
        return value


class AgentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list view"""

    class Meta:
        model = Agent
        fields = [
            'id', 'name', 'description', 'status',
            'created_at', 'total_conversations', 'avg_rating'
        ]


class ConversationSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source='agent.name', read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'agent', 'agent_name', 'user', 'created_at',
            'updated_at', 'message_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_message_count(self, obj):
        return obj.messages.count()


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'conversation', 'role', 'text', 'created_at', 'metadata']
        read_only_fields = ['id', 'created_at']
```

**File:** `server/agent/views.py` (Enhanced)

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from agent.models import Agent, Conversation, Message
from agent.serializers import (
    AgentSerializer,
    AgentListSerializer,
    ConversationSerializer,
    MessageSerializer
)
from agent.core.managers import ConversationManager


class AgentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return AgentListSerializer
        return AgentSerializer

    def get_queryset(self):
        return Agent.objects.filter(
            deleted_at__isnull=True
        ).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        # Soft delete
        instance.deleted_at = timezone.now()
        instance.status = Agent.STATUS_ARCHIVED
        instance.save()

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish agent (make active)"""
        agent = self.get_object()

        agent.status = Agent.STATUS_ACTIVE
        agent.published_at = timezone.now()
        agent.save()

        return Response({
            'status': 'published',
            'agent': AgentSerializer(agent).data
        })

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test agent with a message"""
        agent = self.get_object()
        message = request.data.get('message')

        if not message:
            return Response(
                {'error': 'Message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create test conversation
        conversation = Conversation.objects.create(
            agent=agent,
            user=request.user
        )

        # Add user message
        Message.objects.create(
            conversation=conversation,
            role='user',
            text=message
        )

        # Generate response
        manager = ConversationManager(conversation)
        response_message = manager.respond_to_user_message(message)

        return Response({
            'conversation_id': str(conversation.id),
            'response': MessageSerializer(response_message).data
        })

    @action(detail=True, methods=['get'])
    def conversations(self, request, pk=None):
        """Get recent conversations for agent"""
        agent = self.get_object()

        conversations = Conversation.objects.filter(
            agent=agent
        ).order_by('-created_at')[:20]

        return Response(
            ConversationSerializer(conversations, many=True).data
        )


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(
            user=self.request.user
        ).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message in conversation"""
        conversation = self.get_object()
        message = request.data.get('message')

        if not message:
            return Response(
                {'error': 'Message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Add user message
        user_message = Message.objects.create(
            conversation=conversation,
            role='user',
            text=message
        )

        # Generate response (async via Celery)
        from agent.tasks import respond_to_user_message_task
        task = respond_to_user_message_task.delay(
            str(conversation.id),
            message
        )

        return Response({
            'user_message': MessageSerializer(user_message).data,
            'task_id': task.id
        })

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get all messages in conversation"""
        conversation = self.get_object()
        messages = conversation.messages.order_by('created_at')

        return Response(
            MessageSerializer(messages, many=True).data
        )
```

**Update `server/agent/urls.py`:**
```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from agent.views import AgentViewSet, ConversationViewSet

router = DefaultRouter()
router.register(r'agents', AgentViewSet, basename='agent')
router.register(r'conversations', ConversationViewSet, basename='conversation')

urlpatterns = [
    path('', include(router.urls)),
]
```

### Day 3-5: Test Agent Endpoints

**Create `server/agent/tests/test_agent_api.py`:**
```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from agent.models import Agent

User = get_user_model()


class AgentAPITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_agent(self):
        """Test creating an agent"""
        response = self.client.post('/api/agents/', {
            'name': 'Test Agent',
            'description': 'A test agent',
            'config': Agent.get_default_config()
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'], 'Test Agent')
        self.assertEqual(response.data['status'], 'draft')

    def test_list_agents(self):
        """Test listing agents"""
        Agent.objects.create(
            name='Agent 1',
            created_by=self.user
        )
        Agent.objects.create(
            name='Agent 2',
            created_by=self.user
        )

        response = self.client.get('/api/agents/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_update_agent_config(self):
        """Test updating agent configuration"""
        agent = Agent.objects.create(
            name='Test Agent',
            created_by=self.user
        )

        new_config = agent.config.copy()
        new_config['system_prompt'] = 'Updated prompt'

        response = self.client.put(
            f'/api/agents/{agent.id}/',
            {'name': agent.name, 'config': new_config},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        agent.refresh_from_db()
        self.assertEqual(
            agent.config['system_prompt'],
            'Updated prompt'
        )

    def test_publish_agent(self):
        """Test publishing an agent"""
        agent = Agent.objects.create(
            name='Test Agent',
            created_by=self.user
        )

        response = self.client.post(f'/api/agents/{agent.id}/publish/')

        self.assertEqual(response.status_code, 200)
        agent.refresh_from_db()
        self.assertEqual(agent.status, 'active')
        self.assertIsNotNone(agent.published_at)
```

**Run tests:**
```bash
python manage.py test agent.tests.test_agent_api
```

---

## Week 3: Analytics Backend - Metrics Pipeline

### Day 1-2: Implement Evaluators

**File:** `server/analytics/evaluators/registry.py`
```python
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass


@dataclass
class MetricDefinition:
    """Definition of a metric"""
    name: str
    display_name: str
    description: str
    level: str  # 'turn', 'session', 'daily'
    stage: int  # 1=rule-based, 2=local-ml, 3=llm-judge

    compute_turn: Optional[Callable] = None
    reduce_session: Optional[Callable] = None
    rollup_daily: Optional[Callable] = None


class MetricsRegistry:
    """Central registry for all metrics"""

    def __init__(self):
        self._metrics: Dict[str, MetricDefinition] = {}

    def register(self, metric: MetricDefinition):
        """Register a metric"""
        self._metrics[metric.name] = metric

    def get(self, name: str) -> Optional[MetricDefinition]:
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


# Global registry
registry = MetricsRegistry()
```

**File:** `server/analytics/evaluators/rule_based.py`
```python
"""Stage 1: Rule-based evaluators (fast, no external dependencies)"""

import re
from typing import Dict, Any
from langdetect import detect, LangDetectException

from analytics.evaluators.registry import registry, MetricDefinition


def detect_pii(text: str) -> bool:
    """Detect Personally Identifiable Information"""
    patterns = [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
    ]

    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def compute_pii_flag(turn_data: Dict[str, Any]) -> float:
    """Compute PII flag for a turn"""
    assistant_text = turn_data.get('assistant_text', '')
    return 1.0 if detect_pii(assistant_text) else 0.0


def detect_language(text: str) -> str:
    """Detect language"""
    try:
        return detect(text)
    except LangDetectException:
        return 'unknown'


def compute_response_length(turn_data: Dict[str, Any]) -> float:
    """Compute response length in characters"""
    assistant_text = turn_data.get('assistant_text', '')
    return float(len(assistant_text))


# Register metrics
registry.register(MetricDefinition(
    name='pii_flag',
    display_name='PII Detected',
    description='Whether PII was detected in response',
    level='turn',
    stage=1,
    compute_turn=compute_pii_flag
))

registry.register(MetricDefinition(
    name='response_length',
    display_name='Response Length',
    description='Length of response in characters',
    level='turn',
    stage=1,
    compute_turn=compute_response_length
))
```

**File:** `server/analytics/evaluators/local_ml.py`
```python
"""Stage 2: Local ML models (toxicity, coherence)"""

from typing import Dict, Any
import numpy as np

from analytics.evaluators.registry import registry, MetricDefinition

# Lazy load models
_toxicity_model = None
_sentence_transformer = None


def get_toxicity_model():
    global _toxicity_model
    if _toxicity_model is None:
        from detoxify import Detoxify
        _toxicity_model = Detoxify('original')
    return _toxicity_model


def get_sentence_transformer():
    global _sentence_transformer
    if _sentence_transformer is None:
        from sentence_transformers import SentenceTransformer
        _sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
    return _sentence_transformer


def compute_toxicity(turn_data: Dict[str, Any]) -> float:
    """Compute toxicity score"""
    assistant_text = turn_data.get('assistant_text', '')

    if not assistant_text:
        return 0.0

    model = get_toxicity_model()
    results = model.predict(assistant_text)

    # Max toxicity across categories
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
    """Compute coherence using sentence embeddings"""
    user_text = turn_data.get('user_text', '')
    assistant_text = turn_data.get('assistant_text', '')

    if not user_text or not assistant_text:
        return 0.5

    model = get_sentence_transformer()
    embeddings = model.encode([user_text, assistant_text])

    # Cosine similarity
    similarity = np.dot(embeddings[0], embeddings[1]) / (
        np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
    )

    # Scale to 0-1
    return float((similarity + 1) / 2)


# Register metrics
registry.register(MetricDefinition(
    name='toxicity',
    display_name='Toxicity',
    description='Toxicity score using Detoxify',
    level='turn',
    stage=2,
    compute_turn=compute_toxicity
))

registry.register(MetricDefinition(
    name='coherence',
    display_name='Coherence',
    description='Response coherence to query',
    level='turn',
    stage=2,
    compute_turn=compute_coherence
))
```

**File:** `server/analytics/evaluators/llm_judges.py`
```python
"""Stage 3: LLM-as-judge evaluators"""

from typing import Dict, Any
import openai
from django.conf import settings
import json

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

Respond with ONLY a JSON object:
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
        print(f"Error in answer_relevance: {e}")
        return 0.5


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
{{"faithfulness": 0.9, "reasoning": "explanation"}}"""

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
        print(f"Error in faithfulness: {e}")
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

Due to length constraints, I'll create a second file to continue the implementation guide.

Let me continue with the rest of Week 3-6 in a separate document.
