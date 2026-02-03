"""
Metrics models for storing analytics data at different levels:
- TurnMetric: Per-message metrics (e.g., toxicity of one response)
- SessionMetric: Per-conversation aggregated metrics
- DailyMetric: Daily rollups for trending and dashboards
"""

from django.db import models
from django.contrib.postgres.indexes import BrinIndex


class TurnMetric(models.Model):
    """
    Turn-level metrics stored per message.

    Examples:
    - answer_relevance: 0.85
    - toxicity: 0.02
    - coherence: 0.91
    """

    conversation = models.ForeignKey(
        'agent.Conversation',
        on_delete=models.CASCADE,
        related_name='turn_metrics'
    )
    message = models.ForeignKey(
        'agent.Message',
        on_delete=models.CASCADE,
        related_name='metrics'
    )

    # Metric data
    metric_name = models.CharField(max_length=100, db_index=True)
    value = models.FloatField()

    # Context for filtering
    agent_id = models.UUIDField()
    agent_version = models.IntegerField(default=1)
    model = models.CharField(max_length=100, blank=True)

    # Optional dimensions
    country = models.CharField(max_length=10, blank=True)
    channel = models.CharField(max_length=50, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'analytics_turn_metrics'
        indexes = [
            models.Index(fields=['conversation', 'metric_name']),
            models.Index(fields=['metric_name', 'timestamp']),
            models.Index(fields=['agent_id', 'timestamp']),
            BrinIndex(fields=['timestamp']),  # Efficient for time-series queries
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.metric_name}={self.value:.2f} (msg {self.message_id})"


class SessionMetric(models.Model):
    """
    Session-level aggregated metrics per conversation.

    These are either:
    1. Reduced from turn metrics (e.g., average toxicity)
    2. Computed directly from the full conversation (e.g., repetition)
    """

    conversation = models.ForeignKey(
        'agent.Conversation',
        on_delete=models.CASCADE,
        related_name='session_metrics',
    )

    # Metric data
    metric_name = models.CharField(max_length=100, db_index=True)
    value = models.FloatField()
    count = models.IntegerField(default=1)  # Number of samples (for averaging)

    # Context
    agent_id = models.UUIDField()
    agent_version = models.IntegerField(default=1)
    model = models.CharField(max_length=100, blank=True)

    # Optional dimensions
    country = models.CharField(max_length=10, blank=True)
    channel = models.CharField(max_length=50, blank=True)

    timestamp = models.DateTimeField()

    class Meta:
        db_table = 'analytics_session_metrics'
        indexes = [
            models.Index(fields=['conversation', 'metric_name']),
            models.Index(fields=['agent_id', 'metric_name']),
            models.Index(fields=['timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.metric_name}={self.value:.2f} (conv {self.conversation_id})"


class DailyMetric(models.Model):
    """
    Daily aggregated metrics for dashboards and trending.

    These are rolled up from SessionMetrics for efficient querying.
    """

    date = models.DateField(db_index=True)
    metric_name = models.CharField(max_length=100, db_index=True)

    # Aggregated values
    value = models.FloatField()  # Usually mean/average
    count = models.IntegerField()  # Sample size

    # Dimensions for filtering
    agent_id = models.UUIDField(null=True, blank=True)
    model = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=10, blank=True)
    channel = models.CharField(max_length=50, blank=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_daily_metrics'
        unique_together = [
            ('date', 'metric_name', 'agent_id', 'model', 'country', 'channel')
        ]
        indexes = [
            models.Index(fields=['date', 'metric_name']),
            models.Index(fields=['agent_id', 'date']),
            models.Index(fields=['date', 'agent_id', 'metric_name']),
        ]
        ordering = ['-date', 'metric_name']

    def __str__(self):
        agent_str = f" agent={self.agent_id}" if self.agent_id else ""
        return f"{self.date} {self.metric_name}={self.value:.2f}{agent_str}"
