"""
Agent Builder API Views for MVP.

New endpoints for agent management:
- AgentBuilderViewSet: CRUD + publish + test + conversations
- Replaces/enhances existing agent management
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Count, Avg

from agent.models import Agent, Conversation, Message
from agent.serializers import (
    AgentSerializer,
    AgentListSerializer,
    AgentTestRequestSerializer,
    AgentTestResponseSerializer,
    ConversationSerializer,
    MessageSerializer,
)
from agent.conversation import ConversationManager


class AgentBuilderViewSet(viewsets.ModelViewSet):
    """
    Agent Builder API for creating and managing AI agents.

    Endpoints:
    - list: GET /api/agents/
    - create: POST /api/agents/
    - retrieve: GET /api/agents/{id}/
    - update: PUT/PATCH /api/agents/{id}/
    - destroy: DELETE /api/agents/{id}/ (soft delete)
    - publish: POST /api/agents/{id}/publish/
    - test: POST /api/agents/{id}/test/
    - conversations: GET /api/agents/{id}/conversations/
    """

    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'dataset']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'total_conversations', 'avg_rating']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Use lightweight serializer for list view"""
        if self.action == 'list':
            return AgentListSerializer
        return AgentSerializer

    def get_queryset(self):
        """
        Return agents for current user (created_by).
        Excludes soft-deleted agents.
        """
        return Agent.objects.filter(
            created_by=self.request.user,
            deleted_at__isnull=True
        ).select_related('dataset', 'created_by').order_by('-created_at')

    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        """Soft delete the agent"""
        instance.set_deleted_at()

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """
        Publish an agent (make it active).

        POST /api/agents/{id}/publish/

        Sets status to 'active' and records published_at timestamp.
        """
        agent = self.get_object()

        # Validate agent has required configuration
        if not agent.config.get('system_prompt'):
            return Response(
                {'error': 'Cannot publish agent without system prompt'},
                status=status.HTTP_400_BAD_REQUEST
            )

        agent.publish()

        return Response({
            'message': 'Agent published successfully',
            'agent': AgentSerializer(agent).data
        })

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """
        Archive an agent.

        POST /api/agents/{id}/archive/

        Sets status to 'archived'.
        """
        agent = self.get_object()
        agent.archive()

        return Response({
            'message': 'Agent archived successfully',
            'agent': AgentListSerializer(agent).data
        })

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """
        Test an agent with a sample message.

        POST /api/agents/{id}/test/
        Body: {"message": "Test question"}

        Creates a test conversation and returns the response.
        """
        agent = self.get_object()

        # Validate request
        request_serializer = AgentTestRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        message_text = request_serializer.validated_data['message']

        try:
            # Create test conversation
            conversation = Conversation.objects.create(
                agent=agent,
                user=request.user,
                data_set=agent.dataset
            )

            # Add user message
            user_message = Message.objects.create(
                conversation=conversation,
                role='user',
                text=message_text
            )

            # Generate response using ConversationManager
            manager = ConversationManager(conversation)
            response_text, metadata = manager.respond_to_user_message(message_text)

            # Create assistant message
            assistant_message = Message.objects.create(
                conversation=conversation,
                role='assistant',
                text=response_text,
            )

            # Prepare response
            response_serializer = AgentTestResponseSerializer({
                'conversation_id': conversation.id,
                'user_message': user_message.text,
                'assistant_response': assistant_message.text,
                'metadata': metadata or {}
            })

            return Response(response_serializer.data)

        except Exception as e:
            return Response(
                {'error': f'Error testing agent: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def conversations(self, request, pk=None):
        """
        Get recent conversations for an agent.

        GET /api/agents/{id}/conversations/
        Query params:
        - limit: Number of conversations to return (default: 20, max: 100)
        - offset: Pagination offset

        Returns list of conversations with message counts.
        """
        agent = self.get_object()

        # Get pagination params
        limit = min(int(request.query_params.get('limit', 20)), 100)
        offset = int(request.query_params.get('offset', 0))

        # Get conversations
        conversations = Conversation.objects.filter(
            agent=agent
        ).select_related('user').annotate(
            message_count=Count('messages')
        ).order_by('-started_at')[offset:offset + limit]

        serializer = ConversationSerializer(conversations, many=True)

        return Response({
            'count': conversations.count(),
            'results': serializer.data
        })

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        Get statistics for an agent.

        GET /api/agents/{id}/stats/

        Returns:
        - Total conversations
        - Average rating
        - Total messages
        - Active status
        """
        agent = self.get_object()

        # Get conversation stats
        conversation_stats = Conversation.objects.filter(
            agent=agent
        ).aggregate(
            total=Count('id', distinct=True),
            total_messages=Count('messages')
        )

        # Get rating stats
        rating_stats = Message.objects.filter(
            conversation__agent=agent,
            role='assistant'
        ).aggregate(
            avg_rating=Avg('rating')
        )

        return Response({
            'agent_id': str(agent.id),
            'status': agent.status,
            'version': agent.version,
            'total_conversations': conversation_stats['total'],
            'total_messages': conversation_stats['total_messages'],
            'avg_rating': rating_stats['avg_rating'],
            'created_at': agent.created_at,
            'published_at': agent.published_at,
        })

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Duplicate an agent.

        POST /api/agents/{id}/duplicate/
        Body: {"name": "New Agent Name"} (optional)

        Creates a copy of the agent with a new ID.
        """
        agent = self.get_object()

        # Get new name from request or generate one
        new_name = request.data.get('name', f"{agent.name} (Copy)")

        # Create duplicate
        duplicate = Agent.objects.create(
            name=new_name,
            description=agent.description,
            avatar_url=agent.avatar_url,
            agent_type=agent.agent_type,
            config=agent.config.copy(),  # Deep copy the config
            dataset=agent.dataset,
            created_by=request.user,
            status=Agent.STATUS_DRAFT,
            version=1
        )

        return Response({
            'message': 'Agent duplicated successfully',
            'agent': AgentSerializer(duplicate).data
        }, status=status.HTTP_201_CREATED)
