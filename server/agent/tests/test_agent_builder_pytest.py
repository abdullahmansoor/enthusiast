"""
Comprehensive pytest-style tests for the Agent Builder API.

Covers 10 action groups across these endpoints:
- GET    /api/agents-builder/
- POST   /api/agents-builder/
- GET    /api/agents-builder/{id}/
- PATCH  /api/agents-builder/{id}/
- DELETE /api/agents-builder/{id}/
- POST   /api/agents-builder/{id}/publish/
- POST   /api/agents-builder/{id}/duplicate/   (clone equivalent)
- POST   /api/agents-builder/{id}/test/
- GET    /api/agents-builder/{id}/conversations/
- GET    /api/agents-builder/{id}/stats/
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from django.utils import timezone
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from account.models import User
from agent.models import Conversation, Message
from agent.models.agent import Agent
from analytics.signals import disconnect_analytics_signals, reconnect_analytics_signals
from catalog.models import DataSet

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def disable_analytics_signals():
    """Prevent analytics signals from firing (avoids Celery tasks and signal errors)."""
    disconnect_analytics_signals()
    yield
    reconnect_analytics_signals()


@pytest.fixture
def user():
    return baker.make(User)


@pytest.fixture
def other_user():
    return baker.make(User)


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def other_api_client(other_user):
    client = APIClient()
    client.force_authenticate(user=other_user)
    return client


@pytest.fixture
def dataset(user):
    return baker.make(DataSet, users=[user])


@pytest.fixture
def agent_data(dataset):
    """Valid payload dict for creating an agent."""
    return {
        "name": "My Test Agent",
        "description": "A pytest-created agent",
        "dataset": dataset.id,
        "config": {
            "model": {
                "provider": "openai",
                "name": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2000,
            },
            "system_prompt": "You are a helpful AI assistant.",
            "retrieval": {"enabled": True, "top_k": 5},
            "conversation_starters": ["How can I help?"],
        },
    }


@pytest.fixture
def draft_agent(user, dataset):
    """An Agent in draft status owned by `user`."""
    return baker.make(
        Agent,
        created_by=user,
        dataset=dataset,
        status=Agent.STATUS_DRAFT,
        deleted_at=None,
        config={
            "model": {"provider": "openai", "name": "gpt-4", "temperature": 0.7},
            "system_prompt": "You are a helpful AI assistant.",
            "retrieval": {"enabled": True, "top_k": 5},
            "conversation_starters": ["How can I help?"],
        },
    )


@pytest.fixture
def other_agent(other_user, dataset):
    """An Agent owned by `other_user`."""
    return baker.make(
        Agent,
        created_by=other_user,
        dataset=dataset,
        status=Agent.STATUS_DRAFT,
        deleted_at=None,
    )


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

BASE_URL = "/api/agents-builder/"


def detail_url(agent_id):
    return f"{BASE_URL}{agent_id}/"


def action_url(agent_id, action_name):
    return f"{BASE_URL}{agent_id}/{action_name}/"


# ===========================================================================
# List endpoint
# ===========================================================================


class TestAgentBuilderList:
    def test_returns_only_own_agents(self, api_client, user, dataset, other_user):
        """Only agents created by the requesting user are returned."""
        baker.make(Agent, created_by=user, dataset=dataset, deleted_at=None)
        baker.make(Agent, created_by=other_user, dataset=dataset, deleted_at=None)

        response = api_client.get(BASE_URL)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) == 1
        assert results[0]["name"] == Agent.objects.filter(
            created_by=user, deleted_at__isnull=True
        ).first().name

    def test_excludes_soft_deleted_agents(self, api_client, user, dataset):
        """Soft-deleted agents are excluded from the list."""
        baker.make(Agent, created_by=user, dataset=dataset, deleted_at=None)
        baker.make(Agent, created_by=user, dataset=dataset, deleted_at=timezone.now())

        response = api_client.get(BASE_URL)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_excludes_other_users_agents(self, api_client, other_agent):
        """Other users' agents do not appear in the list."""
        response = api_client.get(BASE_URL)

        assert response.status_code == status.HTTP_200_OK
        returned_ids = [str(a["id"]) for a in response.data["results"]]
        assert str(other_agent.id) not in returned_ids

    def test_status_filter_returns_matching_agents(self, api_client, user, dataset):
        """?status=draft returns only draft agents."""
        baker.make(Agent, created_by=user, dataset=dataset, status=Agent.STATUS_DRAFT, deleted_at=None)
        baker.make(Agent, created_by=user, dataset=dataset, status=Agent.STATUS_ACTIVE, deleted_at=None)

        response = api_client.get(BASE_URL, {"status": "draft"})

        assert response.status_code == status.HTTP_200_OK
        for agent in response.data["results"]:
            assert agent["status"] == "draft"

    def test_empty_list_when_no_agents(self, api_client):
        """Returns empty list when user has no agents."""
        response = api_client.get(BASE_URL)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        response = APIClient().get(BASE_URL)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===========================================================================
# Create endpoint
# ===========================================================================


class TestAgentBuilderCreate:
    def test_creates_agent_with_valid_data(self, api_client, agent_data):
        """POST with valid data returns 201 and creates the agent."""
        response = api_client.post(BASE_URL, agent_data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == agent_data["name"]

    def test_created_agent_status_defaults_to_draft(self, api_client, agent_data):
        """Newly created agent defaults to draft status."""
        response = api_client.post(BASE_URL, agent_data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "draft"

    def test_created_by_set_to_requesting_user(self, api_client, user, agent_data):
        """created_by is set to the authenticated user."""
        response = api_client.post(BASE_URL, agent_data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        agent = Agent.objects.get(pk=response.data["id"])
        assert agent.created_by == user

    def test_name_is_required_returns_400(self, api_client, agent_data):
        """Missing name returns 400."""
        agent_data.pop("name")
        response = api_client.post(BASE_URL, agent_data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_temperature_above_2_returns_400(self, api_client, agent_data):
        """Temperature > 2 is invalid and returns 400."""
        agent_data["config"]["model"]["temperature"] = 3.0
        response = api_client.post(BASE_URL, agent_data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_temperature_below_0_returns_400(self, api_client, agent_data):
        """Negative temperature is invalid and returns 400."""
        agent_data["config"]["model"]["temperature"] = -0.1
        response = api_client.post(BASE_URL, agent_data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_config_merged_with_defaults(self, api_client, dataset):
        """Partial config is merged with defaults on save."""
        data = {
            "name": "Minimal Agent",
            "dataset": dataset.id,
            "config": {
                "model": {"provider": "openai", "name": "gpt-3.5-turbo"},
                "system_prompt": "Helpful assistant",
            },
        }
        response = api_client.post(BASE_URL, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        agent = Agent.objects.get(pk=response.data["id"])
        assert "retrieval" in agent.config
        assert "constraints" in agent.config

    def test_unauthenticated_returns_401(self, agent_data):
        """Unauthenticated request returns 401."""
        response = APIClient().post(BASE_URL, agent_data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===========================================================================
# Retrieve endpoint
# ===========================================================================


class TestAgentBuilderRetrieve:
    def test_own_agent_returns_200_with_config(self, api_client, draft_agent):
        """Retrieving own agent returns 200 with config included."""
        response = api_client.get(detail_url(draft_agent.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == draft_agent.name
        assert "config" in response.data

    def test_other_users_agent_returns_404(self, api_client, other_agent):
        """Retrieving another user's agent returns 404."""
        response = api_client.get(detail_url(other_agent.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_soft_deleted_agent_returns_404(self, api_client, user, dataset):
        """Soft-deleted agent returns 404."""
        deleted = baker.make(
            Agent, created_by=user, dataset=dataset, deleted_at=timezone.now()
        )
        response = api_client.get(detail_url(deleted.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_nonexistent_uuid_returns_404(self, api_client):
        """Non-existent UUID returns 404."""
        response = api_client.get(detail_url(uuid4()))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_401(self, draft_agent):
        """Unauthenticated request returns 401."""
        response = APIClient().get(detail_url(draft_agent.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===========================================================================
# Update (PATCH) endpoint
# ===========================================================================


class TestAgentBuilderPatch:
    def test_patch_name(self, api_client, draft_agent):
        """PATCH name updates the agent name."""
        response = api_client.patch(
            detail_url(draft_agent.id), {"name": "Updated Name"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        draft_agent.refresh_from_db()
        assert draft_agent.name == "Updated Name"

    def test_patch_description(self, api_client, draft_agent):
        """PATCH description updates the agent description."""
        response = api_client.patch(
            detail_url(draft_agent.id),
            {"description": "New description"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        draft_agent.refresh_from_db()
        assert draft_agent.description == "New description"

    def test_patch_system_prompt_inside_config(self, api_client, draft_agent):
        """PATCH config with updated system_prompt persists correctly."""
        new_config = dict(draft_agent.config)
        new_config["system_prompt"] = "Updated system prompt"

        response = api_client.patch(
            detail_url(draft_agent.id), {"config": new_config}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        draft_agent.refresh_from_db()
        assert draft_agent.config["system_prompt"] == "Updated system prompt"

    def test_patch_temperature_in_config(self, api_client, draft_agent):
        """PATCH config with new valid temperature persists correctly."""
        new_config = dict(draft_agent.config)
        new_config["model"] = dict(new_config.get("model", {}))
        new_config["model"]["temperature"] = 1.0

        response = api_client.patch(
            detail_url(draft_agent.id), {"config": new_config}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        draft_agent.refresh_from_db()
        assert draft_agent.config["model"]["temperature"] == 1.0

    def test_patch_other_users_agent_returns_404(self, api_client, other_agent):
        """PATCH on another user's agent returns 404."""
        response = api_client.patch(
            detail_url(other_agent.id), {"name": "Hacked"}, format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_401(self, draft_agent):
        """Unauthenticated PATCH returns 401."""
        response = APIClient().patch(
            detail_url(draft_agent.id), {"name": "x"}, format="json"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===========================================================================
# Delete endpoint (soft delete)
# ===========================================================================


class TestAgentBuilderDelete:
    def test_soft_delete_sets_deleted_at(self, api_client, draft_agent):
        """DELETE sets deleted_at on the agent, not a hard delete."""
        response = api_client.delete(detail_url(draft_agent.id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        # Use all_objects to bypass the soft-delete manager
        agent_in_db = Agent.all_objects.get(pk=draft_agent.id)
        assert agent_in_db.deleted_at is not None

    def test_soft_delete_agent_still_exists_in_db(self, api_client, draft_agent):
        """After DELETE the record still exists in the database."""
        api_client.delete(detail_url(draft_agent.id))

        assert Agent.all_objects.filter(pk=draft_agent.id).exists()

    def test_delete_other_users_agent_returns_404(self, api_client, other_agent):
        """DELETE on another user's agent returns 404."""
        response = api_client.delete(detail_url(other_agent.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_already_deleted_agent_returns_404(self, api_client, user, dataset):
        """DELETE on already-deleted agent returns 404."""
        already_deleted = baker.make(
            Agent, created_by=user, dataset=dataset, deleted_at=timezone.now()
        )
        response = api_client.delete(detail_url(already_deleted.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_401(self, draft_agent):
        """Unauthenticated DELETE returns 401."""
        response = APIClient().delete(detail_url(draft_agent.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===========================================================================
# Publish endpoint
# ===========================================================================


class TestAgentBuilderPublish:
    def test_draft_agent_can_be_published(self, api_client, draft_agent):
        """Publishing a draft agent returns 200 and sets status to active."""
        response = api_client.post(action_url(draft_agent.id, "publish"))

        assert response.status_code == status.HTTP_200_OK
        draft_agent.refresh_from_db()
        assert draft_agent.status == Agent.STATUS_ACTIVE

    def test_publish_sets_published_at(self, api_client, draft_agent):
        """Publishing sets the published_at timestamp."""
        response = api_client.post(action_url(draft_agent.id, "publish"))

        assert response.status_code == status.HTTP_200_OK
        draft_agent.refresh_from_db()
        assert draft_agent.published_at is not None

    def test_publish_without_system_prompt_returns_400(self, api_client, user, dataset):
        """Publishing an agent with empty system_prompt returns 400."""
        agent = baker.make(
            Agent,
            created_by=user,
            dataset=dataset,
            deleted_at=None,
            status=Agent.STATUS_DRAFT,
        )
        # Clear system_prompt after creation to bypass the model's merge-with-defaults logic
        Agent.all_objects.filter(pk=agent.pk).update(
            config={**agent.config, "system_prompt": ""}
        )
        agent.refresh_from_db()

        response = api_client.post(action_url(agent.id, "publish"))

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_publish_other_users_agent_returns_404(self, api_client, other_agent):
        """Publishing another user's agent returns 404."""
        response = api_client.post(action_url(other_agent.id, "publish"))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_response_includes_agent_data(self, api_client, draft_agent):
        """Publish response contains agent key with agent data."""
        response = api_client.post(action_url(draft_agent.id, "publish"))

        assert response.status_code == status.HTTP_200_OK
        assert "agent" in response.data

    def test_unauthenticated_returns_401(self, draft_agent):
        """Unauthenticated publish returns 401."""
        response = APIClient().post(action_url(draft_agent.id, "publish"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===========================================================================
# Clone / Duplicate endpoint
# ===========================================================================


class TestAgentBuilderDuplicate:
    def test_duplicate_creates_new_agent(self, api_client, draft_agent):
        """Duplicating an agent creates a new agent record."""
        initial_count = Agent.objects.filter(created_by=draft_agent.created_by).count()

        response = api_client.post(action_url(draft_agent.id, "duplicate"), {}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert Agent.objects.filter(created_by=draft_agent.created_by).count() == initial_count + 1

    def test_duplicate_name_has_copy_suffix_by_default(self, api_client, draft_agent):
        """Duplicated agent name has '(Copy)' appended when no name given."""
        response = api_client.post(action_url(draft_agent.id, "duplicate"), {}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "(Copy)" in response.data["agent"]["name"]

    def test_duplicate_custom_name(self, api_client, draft_agent):
        """Specifying a name in the request uses that name for the duplicate."""
        response = api_client.post(
            action_url(draft_agent.id, "duplicate"),
            {"name": "Custom Clone Name"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["agent"]["name"] == "Custom Clone Name"

    def test_duplicate_is_in_draft_status(self, api_client, draft_agent):
        """Duplicated agent starts as a draft."""
        response = api_client.post(action_url(draft_agent.id, "duplicate"), {}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["agent"]["status"] == Agent.STATUS_DRAFT

    def test_duplicate_has_version_1(self, api_client, draft_agent):
        """Duplicated agent starts at version 1."""
        response = api_client.post(action_url(draft_agent.id, "duplicate"), {}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["agent"]["version"] == 1

    def test_original_agent_unchanged_after_duplicate(self, api_client, draft_agent):
        """Duplicating does not change the original agent."""
        original_name = draft_agent.name
        original_status = draft_agent.status

        api_client.post(action_url(draft_agent.id, "duplicate"), {}, format="json")

        draft_agent.refresh_from_db()
        assert draft_agent.name == original_name
        assert draft_agent.status == original_status

    def test_duplicate_other_users_agent_returns_404(self, api_client, other_agent):
        """Duplicating another user's agent returns 404."""
        response = api_client.post(action_url(other_agent.id, "duplicate"), {}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_401(self, draft_agent):
        """Unauthenticated duplicate returns 401."""
        response = APIClient().post(action_url(draft_agent.id, "duplicate"), {}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===========================================================================
# Test endpoint
# ===========================================================================


class TestAgentBuilderTestEndpoint:
    def _mock_conversation_manager(self, response_text="Mocked response"):
        """Return a MagicMock that simulates ConversationManager.respond_to_user_message."""
        mock_manager = MagicMock()
        mock_manager.respond_to_user_message.return_value = (response_text, {"source": "mock"})
        return mock_manager

    def test_test_endpoint_returns_response_and_conversation_id(
        self, api_client, draft_agent
    ):
        """POST /test/ returns 200 with assistant_response and conversation_id."""
        mock_manager = self._mock_conversation_manager()
        with patch(
            "agent.views_agent_builder.ConversationManager",
            return_value=mock_manager,
        ):
            response = api_client.post(
                action_url(draft_agent.id, "test"),
                {"message": "Hello, agent!"},
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK
        assert "conversation_id" in response.data
        assert "assistant_response" in response.data

    def test_test_endpoint_returns_user_message_echoed(
        self, api_client, draft_agent
    ):
        """Response contains the original user_message."""
        mock_manager = self._mock_conversation_manager()
        with patch(
            "agent.views_agent_builder.ConversationManager",
            return_value=mock_manager,
        ):
            response = api_client.post(
                action_url(draft_agent.id, "test"),
                {"message": "Ping!"},
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["user_message"] == "Ping!"

    def test_test_endpoint_creates_conversation_record(
        self, api_client, draft_agent
    ):
        """A Conversation record is created in the database."""
        initial_count = Conversation.objects.filter(agent=draft_agent).count()
        mock_manager = self._mock_conversation_manager()
        with patch(
            "agent.views_agent_builder.ConversationManager",
            return_value=mock_manager,
        ):
            api_client.post(
                action_url(draft_agent.id, "test"),
                {"message": "Test message"},
                format="json",
            )

        assert Conversation.objects.filter(agent=draft_agent).count() == initial_count + 1

    def test_test_endpoint_missing_message_returns_400(self, api_client, draft_agent):
        """Missing 'message' field in request body returns 400."""
        response = api_client.post(
            action_url(draft_agent.id, "test"), {}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_test_other_users_agent_returns_404(self, api_client, other_agent):
        """Testing another user's agent returns 404."""
        response = api_client.post(
            action_url(other_agent.id, "test"),
            {"message": "Hello"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_401(self, draft_agent):
        """Unauthenticated test request returns 401."""
        response = APIClient().post(
            action_url(draft_agent.id, "test"),
            {"message": "Hello"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_llm_exception_returns_500(self, api_client, draft_agent):
        """When the LLM call raises an exception, the endpoint returns 500."""
        mock_manager = MagicMock()
        mock_manager.respond_to_user_message.side_effect = RuntimeError("LLM unreachable")
        with patch(
            "agent.views_agent_builder.ConversationManager",
            return_value=mock_manager,
        ):
            response = api_client.post(
                action_url(draft_agent.id, "test"),
                {"message": "Will this fail?"},
                format="json",
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ===========================================================================
# Conversations endpoint
# ===========================================================================


class TestAgentBuilderConversations:
    def test_returns_conversations_for_agent(
        self, api_client, draft_agent, user, dataset
    ):
        """GET /conversations/ returns conversations belonging to the agent."""
        for _ in range(3):
            baker.make(Conversation, agent=draft_agent, user=user, data_set=dataset)

        response = api_client.get(action_url(draft_agent.id, "conversations"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3

    def test_returns_zero_when_no_conversations(self, api_client, draft_agent):
        """Returns count of 0 when agent has no conversations."""
        response = api_client.get(action_url(draft_agent.id, "conversations"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_other_users_agent_returns_404(self, api_client, other_agent):
        """Accessing conversations for another user's agent returns 404."""
        response = api_client.get(action_url(other_agent.id, "conversations"))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_401(self, draft_agent):
        """Unauthenticated request returns 401."""
        response = APIClient().get(action_url(draft_agent.id, "conversations"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===========================================================================
# Stats endpoint
# ===========================================================================


class TestAgentBuilderStats:
    def test_returns_stats_with_required_fields(self, api_client, draft_agent):
        """GET /stats/ returns 200 with expected fields."""
        response = api_client.get(action_url(draft_agent.id, "stats"))

        assert response.status_code == status.HTTP_200_OK
        for key in ("agent_id", "status", "version", "total_conversations", "total_messages"):
            assert key in response.data

    def test_stats_total_conversations_matches_db(
        self, api_client, draft_agent, user, dataset
    ):
        """total_conversations count matches the actual number in the database."""
        for _ in range(4):
            baker.make(Conversation, agent=draft_agent, user=user, data_set=dataset)

        response = api_client.get(action_url(draft_agent.id, "stats"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_conversations"] == 4

    def test_stats_total_messages_counts_all_roles(
        self, api_client, draft_agent, user, dataset
    ):
        """total_messages includes both user and assistant messages."""
        conv = baker.make(Conversation, agent=draft_agent, user=user, data_set=dataset)
        baker.make(Message, conversation=conv, role="user", text="Q")
        baker.make(Message, conversation=conv, role="assistant", text="A")

        response = api_client.get(action_url(draft_agent.id, "stats"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_messages"] == 2

    def test_other_users_agent_returns_404(self, api_client, other_agent):
        """Accessing stats for another user's agent returns 404."""
        response = api_client.get(action_url(other_agent.id, "stats"))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_401(self, draft_agent):
        """Unauthenticated request returns 401."""
        response = APIClient().get(action_url(draft_agent.id, "stats"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===========================================================================
# Authentication guard – all builder endpoints
# ===========================================================================


class TestAgentBuilderAuthenticationRequired:
    """All Agent Builder endpoints must return 401 for unauthenticated requests."""

    def test_list_requires_auth(self):
        assert APIClient().get(BASE_URL).status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_requires_auth(self):
        assert APIClient().post(BASE_URL, {}, format="json").status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_requires_auth(self):
        fake_id = uuid4()
        assert APIClient().get(detail_url(fake_id)).status_code == status.HTTP_401_UNAUTHORIZED

    def test_patch_requires_auth(self):
        fake_id = uuid4()
        assert APIClient().patch(detail_url(fake_id), {}).status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_requires_auth(self):
        fake_id = uuid4()
        assert APIClient().delete(detail_url(fake_id)).status_code == status.HTTP_401_UNAUTHORIZED

    def test_publish_requires_auth(self):
        fake_id = uuid4()
        assert APIClient().post(action_url(fake_id, "publish")).status_code == status.HTTP_401_UNAUTHORIZED

    def test_duplicate_requires_auth(self):
        fake_id = uuid4()
        assert APIClient().post(action_url(fake_id, "duplicate")).status_code == status.HTTP_401_UNAUTHORIZED

    def test_test_requires_auth(self):
        fake_id = uuid4()
        assert APIClient().post(action_url(fake_id, "test"), {"message": "hi"}).status_code == status.HTTP_401_UNAUTHORIZED

    def test_conversations_requires_auth(self):
        fake_id = uuid4()
        assert APIClient().get(action_url(fake_id, "conversations")).status_code == status.HTTP_401_UNAUTHORIZED

    def test_stats_requires_auth(self):
        fake_id = uuid4()
        assert APIClient().get(action_url(fake_id, "stats")).status_code == status.HTTP_401_UNAUTHORIZED
