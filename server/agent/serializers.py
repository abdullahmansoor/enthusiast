"""
Serializers for Agent Builder API.

Includes:
- AgentConfigSerializer: Validates agent configuration
- AgentSerializer: Full agent details
- AgentListSerializer: Lightweight for list views
- AgentTestSerializer: For testing agents
- ConversationSerializer: Conversation details
- MessageSerializer: Message details
"""

from rest_framework import serializers
from agent.models import Agent, Conversation, Message


class AgentConfigSerializer(serializers.Serializer):
    """
    Validate agent configuration structure.

    This ensures the config JSON has all required fields and valid values.
    """

    # Model configuration
    model = serializers.DictField(required=True)

    # System prompt
    system_prompt = serializers.CharField(
        required=True,
        max_length=10000,
        help_text="Instructions for the agent's behavior"
    )

    # Retrieval configuration
    retrieval = serializers.DictField(
        required=False,
        default={
            "enabled": True,
            "top_k": 5,
            "score_threshold": 0.7
        }
    )

    # Conversation starters
    conversation_starters = serializers.ListField(
        child=serializers.CharField(max_length=500),
        required=False,
        default=["How can I help you today?"],
        max_length=5,
        help_text="Pre-defined prompts shown to users"
    )

    # Constraints
    constraints = serializers.DictField(
        required=False,
        default={
            "max_conversation_length": 50,
            "max_response_tokens": 1000,
            "response_timeout_seconds": 30
        }
    )

    def validate_model(self, value):
        """Validate model configuration"""
        required_fields = ['provider', 'name']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(
                    f"Model config must include '{field}'"
                )

        # Validate temperature range
        if 'temperature' in value:
            temp = value['temperature']
            if not (0 <= temp <= 2):
                raise serializers.ValidationError(
                    "Temperature must be between 0 and 2"
                )

        return value

    def validate_retrieval(self, value):
        """Validate retrieval configuration"""
        if 'top_k' in value:
            if not (1 <= value['top_k'] <= 20):
                raise serializers.ValidationError(
                    "top_k must be between 1 and 20"
                )

        if 'score_threshold' in value:
            if not (0 <= value['score_threshold'] <= 1):
                raise serializers.ValidationError(
                    "score_threshold must be between 0 and 1"
                )

        return value


class AgentSerializer(serializers.ModelSerializer):
    """
    Full agent serializer with all fields and related data.
    """

    created_by_email = serializers.EmailField(
        source='created_by.email',
        read_only=True
    )

    # Validate config using nested serializer
    config = AgentConfigSerializer()

    class Meta:
        model = Agent
        fields = [
            'id', 'name', 'description', 'avatar_url',
            'agent_type', 'config', 'dataset',
            'created_by', 'created_by_email',
            'version', 'status',
            'created_at', 'updated_at', 'published_at', 'deleted_at',
            'total_conversations', 'avg_rating'
        ]
        read_only_fields = [
            'id', 'version', 'created_at', 'updated_at', 'deleted_at',
            'total_conversations', 'avg_rating', 'created_by'
        ]

    def validate_config(self, value):
        """
        Validate and normalize config.
        Merges with defaults to ensure all keys are present.
        """
        # Validate using nested serializer
        config_serializer = AgentConfigSerializer(data=value)
        config_serializer.is_valid(raise_exception=True)

        # Merge with defaults
        default = Agent.get_default_config()
        for key in default:
            if key not in value:
                value[key] = default[key]

        return value

    def create(self, validated_data):
        """Set created_by to current user"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class AgentListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views.
    Only includes essential fields for performance.
    """

    model_name = serializers.SerializerMethodField()
    is_published = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = [
            'id', 'name', 'description', 'avatar_url',
            'status', 'model_name', 'is_published',
            'created_at', 'published_at',
            'total_conversations', 'avg_rating'
        ]

    def get_model_name(self, obj):
        """Extract model name from config"""
        return obj.config.get('model', {}).get('name', 'unknown')

    def get_is_published(self, obj):
        """Check if agent is published"""
        return obj.status == Agent.STATUS_ACTIVE


class AgentTestRequestSerializer(serializers.Serializer):
    """Serializer for testing an agent"""

    message = serializers.CharField(
        required=True,
        max_length=5000,
        help_text="Test message to send to the agent"
    )


class AgentTestResponseSerializer(serializers.Serializer):
    """Serializer for agent test response"""

    conversation_id = serializers.UUIDField()
    user_message = serializers.CharField()
    assistant_response = serializers.CharField()
    metadata = serializers.DictField(required=False)


class ConversationSerializer(serializers.ModelSerializer):
    """Conversation with agent and message count"""

    agent_name = serializers.CharField(source='agent.name', read_only=True)
    agent_version = serializers.IntegerField(source='agent.version', read_only=True)
    message_count = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Conversation
        fields = [
            'id', 'agent', 'agent_name', 'agent_version',
            'user', 'user_email',
            'created_at', 'updated_at',
            'message_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_message_count(self, obj):
        """Count messages in conversation"""
        return obj.messages.count()


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Detailed conversation with all messages"""

    agent_name = serializers.CharField(source='agent.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    messages = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'agent', 'agent_name',
            'user', 'user_email',
            'created_at', 'updated_at',
            'messages'
        ]

    def get_messages(self, obj):
        """Get all messages in chronological order"""
        messages = obj.messages.order_by('created_at')
        return MessageSerializer(messages, many=True).data


class MessageSerializer(serializers.ModelSerializer):
    """Individual message in a conversation"""

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'role', 'text',
            'created_at', 'metadata'
        ]
        read_only_fields = ['id', 'created_at']

    def validate_role(self, value):
        """Ensure role is valid"""
        valid_roles = ['user', 'assistant', 'system']
        if value not in valid_roles:
            raise serializers.ValidationError(
                f"Role must be one of: {', '.join(valid_roles)}"
            )
        return value
