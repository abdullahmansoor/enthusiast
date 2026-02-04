from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from .views_agent_builder import AgentBuilderViewSet

# Create router for Agent Builder ViewSet
router = DefaultRouter()
router.register(r'agents-builder', AgentBuilderViewSet, basename='agent-builder')

urlpatterns = (
    # Existing conversation endpoints
    path("api/conversations/", views.ConversationListView.as_view(), name="conversation-list"),
    path("api/conversations/<int:conversation_id>/", views.ConversationView.as_view(), name="conversation-details"),
    path(
        "api/conversations/<int:conversation_id>/upload/",
        views.ConversationFileUploadView.as_view(),
        name="conversation-upload",
    ),
    path("api/messages/<int:id>/feedback/", views.MessageFeedbackView.as_view()),
    path("api/task_status/<str:task_id>/", views.GetTaskStatus.as_view()),

    # Legacy agent endpoints (keep for backward compatibility)
    path("api/agents/", views.AgentView.as_view(), name="agents"),
    path("api/agents/<int:pk>/", views.AgentDetailsView.as_view(), name="agent-details"),
    path("api/agents/types/", views.AgentTypesView.as_view(), name="agent-types"),

    # New Agent Builder API (ViewSet-based)
    # Routes:
    # GET    /api/agents-builder/              - List agents
    # POST   /api/agents-builder/              - Create agent
    # GET    /api/agents-builder/{id}/         - Get agent
    # PUT    /api/agents-builder/{id}/         - Update agent
    # DELETE /api/agents-builder/{id}/         - Delete agent (soft)
    # POST   /api/agents-builder/{id}/publish/ - Publish agent
    # POST   /api/agents-builder/{id}/test/    - Test agent
    # GET    /api/agents-builder/{id}/conversations/ - Get conversations
    # GET    /api/agents-builder/{id}/stats/   - Get stats
    # POST   /api/agents-builder/{id}/duplicate/ - Duplicate agent
    path("api/", include(router.urls)),
)
