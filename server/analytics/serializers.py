"""
Serializers for Analytics Dashboard API.

Provides data structures for:
- KPI overview
- Time series data
- Distributions
- Conversation lists
- Session details
"""

from rest_framework import serializers
from analytics.models import TurnMetric, SessionMetric, DailyMetric


class KPISerializer(serializers.Serializer):
    """KPI summary for dashboard overview"""

    # Quality metrics (LLM-judged)
    answer_relevance = serializers.FloatField(allow_null=True)
    faithfulness = serializers.FloatField(allow_null=True)
    coherence = serializers.FloatField(allow_null=True)
    toxicity = serializers.FloatField(allow_null=True)
    composite_quality = serializers.FloatField(allow_null=True)
    resolution_quality = serializers.FloatField(allow_null=True, required=False)

    # Business / operational metrics
    answer_failure_rate = serializers.FloatField(allow_null=True, required=False)
    knowledge_gap_rate = serializers.FloatField(allow_null=True, required=False)
    user_satisfaction_score = serializers.FloatField(allow_null=True, required=False)
    user_abandonment_rate = serializers.FloatField(allow_null=True, required=False)
    avg_session_depth = serializers.FloatField(allow_null=True, required=False)
    avg_response_latency = serializers.FloatField(allow_null=True, required=False)
    product_surface_rate = serializers.FloatField(allow_null=True, required=False)

    # Volume metrics
    total_conversations = serializers.IntegerField()

    # Date range
    date_range = serializers.DictField()


class TimeSeriesDataPointSerializer(serializers.Serializer):
    """Single data point in time series"""

    date = serializers.DateField()
    value = serializers.FloatField()
    count = serializers.IntegerField()


class TimeSeriesSerializer(serializers.Serializer):
    """Time series response"""

    metric_name = serializers.CharField()
    data = TimeSeriesDataPointSerializer(many=True)
    date_range = serializers.DictField()


class DistributionStatsSerializer(serializers.Serializer):
    """Statistical summary of a metric"""

    mean = serializers.FloatField()
    median = serializers.FloatField()
    std = serializers.FloatField()
    min = serializers.FloatField()
    max = serializers.FloatField()
    p10 = serializers.FloatField()
    p25 = serializers.FloatField()
    p75 = serializers.FloatField()
    p90 = serializers.FloatField()
    count = serializers.IntegerField()


class DistributionSerializer(serializers.Serializer):
    """Distribution/histogram response"""

    metric_name = serializers.CharField()
    stats = DistributionStatsSerializer(required=False, allow_null=True)
    values = serializers.ListField(child=serializers.FloatField())


class ConversationMetricSerializer(serializers.Serializer):
    """Metrics for a single conversation"""

    # Metrics dict with metric_name -> value
    metrics = serializers.DictField()


class ConversationListItemSerializer(serializers.Serializer):
    """Conversation item in list view"""

    id = serializers.IntegerField()
    agent_id = serializers.IntegerField()
    agent_name = serializers.CharField()
    created_at = serializers.DateTimeField()
    message_count = serializers.IntegerField()
    metrics = serializers.DictField()


class ConversationListSerializer(serializers.Serializer):
    """Paginated conversation list response"""

    results = ConversationListItemSerializer(many=True)
    count = serializers.IntegerField()
    total = serializers.IntegerField()
    has_more = serializers.BooleanField()


class MessageDetailSerializer(serializers.Serializer):
    """Message with metrics for session replay"""

    id = serializers.IntegerField()
    role = serializers.CharField()
    text = serializers.CharField()
    created_at = serializers.DateTimeField()
    metrics = serializers.DictField()
    metadata = serializers.DictField(required=False)


class SessionDetailSerializer(serializers.Serializer):
    """Detailed session with all messages and metrics"""

    conversation_id = serializers.IntegerField()
    agent_id = serializers.IntegerField()
    agent_name = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    message_count = serializers.IntegerField()
    session_metrics = serializers.DictField()
    messages = MessageDetailSerializer(many=True)


class TurnMetricSerializer(serializers.ModelSerializer):
    """Turn metric for detailed analysis"""

    class Meta:
        model = TurnMetric
        fields = [
            'id', 'conversation', 'message', 'metric_name', 'value',
            'agent_id', 'agent_version', 'model', 'timestamp'
        ]


class SessionMetricSerializer(serializers.ModelSerializer):
    """Session metric for detailed analysis"""

    class Meta:
        model = SessionMetric
        fields = [
            'id', 'conversation', 'metric_name', 'value', 'count',
            'agent_id', 'agent_version', 'model', 'timestamp'
        ]


class DailyMetricSerializer(serializers.ModelSerializer):
    """Daily metric for trend analysis"""

    class Meta:
        model = DailyMetric
        fields = [
            'id', 'date', 'metric_name', 'value', 'count',
            'agent_id', 'model', 'created_at', 'updated_at'
        ]


class MetricDefinitionSerializer(serializers.Serializer):
    """Metric metadata for catalog"""

    name = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()
    level = serializers.CharField()
    stage = serializers.IntegerField()


class DateRangeFilterSerializer(serializers.Serializer):
    """Date range filter for queries"""

    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)
    agent_id = serializers.IntegerField(required=False, allow_null=True)


class MetricQuerySerializer(serializers.Serializer):
    """Query parameters for metric endpoints"""

    metric_name = serializers.CharField(required=True)
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)
    agent_id = serializers.IntegerField(required=False, allow_null=True)
    granularity = serializers.ChoiceField(
        choices=['daily', 'weekly'],
        default='daily',
        required=False
    )


class OutlierConversationSerializer(serializers.Serializer):
    """Conversation that's an outlier on some metric"""

    conversation_id = serializers.IntegerField()
    agent_id = serializers.IntegerField()
    agent_name = serializers.CharField()
    metric_name = serializers.CharField()
    value = serializers.FloatField()
    percentile = serializers.FloatField()
    created_at = serializers.DateTimeField()
    message_count = serializers.IntegerField()
