"""
Comprehensive pytest-style tests for the Analytics Dashboard API.

Covers all 7 endpoints:
- GET /api/analytics/overview/
- GET /api/analytics/timeseries/
- GET /api/analytics/distribution/
- GET /api/analytics/conversations/
- GET /api/analytics/conversations/{id}/detail/
- GET /api/analytics/metrics/
- GET /api/analytics/outliers/
"""

from datetime import date, timedelta

import pytest
from django.utils import timezone
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from account.models import User
from agent.models import Conversation, Message
from agent.models.agent import Agent
from analytics.models import DailyMetric, SessionMetric, TurnMetric
from analytics.signals import disconnect_analytics_signals, reconnect_analytics_signals
from catalog.models import DataSet

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def disable_analytics_signals():
    """Prevent analytics signals from firing during tests (avoids Celery tasks)."""
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
def dataset():
    return baker.make(DataSet)


@pytest.fixture
def agent(user, dataset):
    return baker.make(
        Agent,
        created_by=user,
        dataset=dataset,
        deleted_at=None,
        config={
            "model": {"provider": "openai", "name": "gpt-4", "temperature": 0.7},
            "system_prompt": "You are helpful.",
        },
    )


@pytest.fixture
def other_agent(other_user, dataset):
    return baker.make(
        Agent,
        created_by=other_user,
        dataset=dataset,
        deleted_at=None,
    )


@pytest.fixture
def conversation_with_metrics(user, agent, dataset):
    """
    Creates a Conversation with Messages, TurnMetrics, and SessionMetrics.
    Returns the Conversation instance.
    """
    conv = baker.make(Conversation, user=user, agent=agent, data_set=dataset)

    user_msg = baker.make(Message, conversation=conv, role="user", text="Hello?")
    asst_msg = baker.make(
        Message, conversation=conv, role="assistant", text="Hello! How can I help?"
    )

    # Turn metric for assistant message
    baker.make(
        TurnMetric,
        conversation=conv,
        message=asst_msg,
        metric_name="response_length",
        value=25.0,
        agent_id=agent.id,
        agent_version=1,
        model="gpt-4",
    )

    # Session metric tied to the conversation
    baker.make(
        SessionMetric,
        conversation=conv,
        metric_name="response_length_mean",
        value=25.0,
        count=1,
        agent_id=agent.id,
        agent_version=1,
        model="gpt-4",
        timestamp=timezone.now(),
    )

    return conv


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_daily_metric(agent, metric_name="response_length_mean", value=0.8, target_date=None):
    """Create a DailyMetric for the given agent."""
    if target_date is None:
        target_date = date.today()
    return baker.make(
        DailyMetric,
        date=target_date,
        metric_name=metric_name,
        value=value,
        count=1,
        agent_id=agent.id,
    )


# ===========================================================================
# Overview endpoint
# ===========================================================================


class TestOverviewEndpoint:
    URL = "/api/analytics/overview/"

    def test_happy_path_returns_200(self, api_client, agent):
        """Overview with no filters returns 200 and expected keys."""
        response = api_client.get(self.URL)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_conversations" in data
        assert "date_range" in data

    def test_returns_expected_kpi_keys(self, api_client, agent):
        """Overview response includes all KPI keys."""
        response = api_client.get(self.URL)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        expected_keys = {
            "answer_relevance",
            "faithfulness",
            "coherence",
            "toxicity",
            "composite_quality",
            "total_conversations",
            "date_range",
        }
        assert expected_keys.issubset(set(data.keys()))

    def test_custom_date_range_reflected_in_response(self, api_client, agent):
        """Custom start_date/end_date are reflected in the response date_range."""
        today = date.today()
        start = today - timedelta(days=7)

        response = api_client.get(
            self.URL, {"start_date": str(start), "end_date": str(today)}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["date_range"]["start"] == str(start)
        assert data["date_range"]["end"] == str(today)

    def test_agent_id_filter_own_agent_returns_200(self, api_client, agent):
        """Filtering by own agent returns 200."""
        response = api_client.get(self.URL, {"agent_id": str(agent.id)})

        assert response.status_code == status.HTTP_200_OK

    def test_agent_id_filter_other_users_agent_returns_404(
        self, api_client, other_agent
    ):
        """Filtering by another user's agent returns 404."""
        response = api_client.get(self.URL, {"agent_id": str(other_agent.id)})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_nonexistent_agent_id_returns_404(self, api_client):
        """Filtering by an integer ID that does not exist returns 404."""
        response = api_client.get(self.URL, {"agent_id": 999999})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        response = APIClient().get(self.URL)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===========================================================================
# Timeseries endpoint
# ===========================================================================


class TestTimeseriesEndpoint:
    URL = "/api/analytics/timeseries/"

    def _params(self, metric_name="response_length_mean", days_back=7, **extra):
        today = date.today()
        start = today - timedelta(days=days_back)
        return {"metric_name": metric_name, "start_date": str(start), "end_date": str(today), **extra}

    def test_happy_path_returns_200_with_correct_structure(self, api_client, agent):
        """Valid request returns 200 with metric_name and data list."""
        _make_daily_metric(agent)

        response = api_client.get(self.URL, self._params())

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "metric_name" in data
        assert "data" in data
        assert isinstance(data["data"], list)
        assert data["metric_name"] == "response_length_mean"

    def test_missing_metric_name_returns_400(self, api_client):
        """Omitting metric_name returns 400."""
        today = date.today()
        response = api_client.get(
            self.URL, {"start_date": str(today), "end_date": str(today)}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_start_date_returns_400(self, api_client):
        """Omitting start_date returns 400."""
        response = api_client.get(
            self.URL, {"metric_name": "response_length_mean", "end_date": str(date.today())}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_end_date_returns_400(self, api_client):
        """Omitting end_date returns 400."""
        response = api_client.get(
            self.URL,
            {"metric_name": "response_length_mean", "start_date": str(date.today())},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_agent_id_filter_own_agent_returns_200(self, api_client, agent):
        """Filtering by own agent_id succeeds."""
        _make_daily_metric(agent)

        response = api_client.get(self.URL, self._params(agent_id=str(agent.id)))

        assert response.status_code == status.HTTP_200_OK

    def test_agent_id_filter_other_users_agent_returns_404(
        self, api_client, other_agent
    ):
        """Filtering by another user's agent returns 404."""
        response = api_client.get(self.URL, self._params(agent_id=str(other_agent.id)))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_empty_date_range_returns_empty_data_list(self, api_client, agent):
        """Date range with no data returns empty data list."""
        far_past = date.today() - timedelta(days=365)
        far_past_end = far_past + timedelta(days=1)

        response = api_client.get(
            self.URL,
            {
                "metric_name": "response_length_mean",
                "start_date": str(far_past),
                "end_date": str(far_past_end),
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"] == []

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        response = APIClient().get(self.URL, {"metric_name": "x", "start_date": "2024-01-01", "end_date": "2024-01-31"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===========================================================================
# Distribution endpoint
# ===========================================================================


class TestDistributionEndpoint:
    URL = "/api/analytics/distribution/"

    def _params(self, metric_name="response_length_mean", **extra):
        today = date.today()
        start = today - timedelta(days=7)
        return {
            "metric_name": metric_name,
            "start_date": str(start),
            "end_date": str(today),
            **extra,
        }

    def test_happy_path_returns_200_with_correct_structure(
        self, api_client, agent, dataset
    ):
        """Valid request with data returns correct stats shape."""
        conv = baker.make(Conversation, user=baker.make(User), agent=agent, data_set=dataset)
        baker.make(
            SessionMetric,
            conversation=conv,
            metric_name="response_length_mean",
            value=42.0,
            agent_id=agent.id,
            timestamp=timezone.now(),
        )

        response = api_client.get(self.URL, self._params())

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "metric_name" in data
        assert "stats" in data
        assert "values" in data

    def test_stats_contain_required_fields(self, api_client, agent, dataset):
        """Stats dict contains all required statistical fields."""
        conv = baker.make(Conversation, user=baker.make(User), agent=agent, data_set=dataset)
        for v in [10.0, 20.0, 30.0]:
            baker.make(
                SessionMetric,
                conversation=conv,
                metric_name="response_length_mean",
                value=v,
                agent_id=agent.id,
                timestamp=timezone.now(),
            )

        response = api_client.get(self.URL, self._params())

        assert response.status_code == status.HTTP_200_OK
        stats = response.json()["stats"]
        for key in ("mean", "median", "std", "min", "max", "p10", "p25", "p75", "p90", "count"):
            assert key in stats, f"Missing key: {key}"

    def test_missing_metric_name_returns_400(self, api_client):
        """Omitting metric_name returns 400."""
        today = date.today()
        response = api_client.get(
            self.URL, {"start_date": str(today), "end_date": str(today)}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        response = APIClient().get(
            self.URL,
            {"metric_name": "x", "start_date": "2024-01-01", "end_date": "2024-01-31"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===========================================================================
# Conversations list endpoint
# ===========================================================================


class TestConversationsListEndpoint:
    URL = "/api/analytics/conversations/"

    def test_returns_only_own_conversations(
        self, api_client, user, agent, other_agent, dataset
    ):
        """Only conversations belonging to the requesting user's agents are returned."""
        baker.make(Conversation, user=user, agent=agent, data_set=dataset)
        other_user_obj = other_agent.created_by
        baker.make(Conversation, user=other_user_obj, agent=other_agent, data_set=dataset)

        response = api_client.get(self.URL)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["results"][0]["agent_id"] == agent.id

    def test_response_structure_contains_required_keys(
        self, api_client, user, agent, dataset
    ):
        """Response contains results, count, total, has_more."""
        baker.make(Conversation, user=user, agent=agent, data_set=dataset)

        response = api_client.get(self.URL)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for key in ("results", "count", "total", "has_more"):
            assert key in data

    def test_each_result_has_required_fields(self, api_client, user, agent, dataset):
        """Each conversation result has required fields."""
        baker.make(Conversation, user=user, agent=agent, data_set=dataset)

        response = api_client.get(self.URL)

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["results"][0]
        for key in ("id", "agent_id", "agent_name", "created_at", "message_count", "metrics"):
            assert key in result

    def test_pagination_page_and_page_size(self, api_client, user, agent, dataset):
        """Pagination with page=1, page_size=2 returns 2 of 5 total."""
        for _ in range(5):
            baker.make(Conversation, user=user, agent=agent, data_set=dataset)

        response = api_client.get(self.URL, {"page": 1, "page_size": 2})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] == 2
        assert data["total"] == 5
        assert data["has_more"] is True

    def test_pagination_second_page(self, api_client, user, agent, dataset):
        """Second page with page_size=2 returns next 2."""
        for _ in range(5):
            baker.make(Conversation, user=user, agent=agent, data_set=dataset)

        response = api_client.get(self.URL, {"page": 2, "page_size": 2})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] == 2
        assert data["total"] == 5

    def test_agent_id_filter_restricts_results(
        self, api_client, user, agent, dataset
    ):
        """agent_id query param filters results to matching conversations."""
        other_dataset = baker.make(DataSet)
        second_agent = baker.make(
            Agent, created_by=user, dataset=other_dataset, deleted_at=None
        )
        baker.make(Conversation, user=user, agent=agent, data_set=dataset)
        baker.make(Conversation, user=user, agent=second_agent, data_set=other_dataset)

        response = api_client.get(self.URL, {"agent_id": str(agent.id)})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["results"][0]["agent_id"] == agent.id

    def test_date_filter_start_date(self, api_client, user, agent, dataset):
        """start_date filter excludes earlier conversations."""
        baker.make(Conversation, user=user, agent=agent, data_set=dataset)

        future = date.today() + timedelta(days=10)
        response = api_client.get(self.URL, {"start_date": str(future)})

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total"] == 0

    def test_sorted_by_created_at_desc_by_default(
        self, api_client, user, agent, dataset
    ):
        """Conversations are returned newest-first by default."""
        for _ in range(3):
            baker.make(Conversation, user=user, agent=agent, data_set=dataset)

        response = api_client.get(self.URL)

        assert response.status_code == status.HTTP_200_OK
        results = response.json()["results"]
        timestamps = [r["created_at"] for r in results]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        response = APIClient().get(self.URL)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===========================================================================
# Conversation detail endpoint
# ===========================================================================


class TestConversationDetailEndpoint:
    def _url(self, conv_id):
        return f"/api/analytics/{conv_id}/detail/"

    def test_returns_200_with_correct_structure(
        self, api_client, conversation_with_metrics
    ):
        """Own conversation detail returns 200 with expected top-level keys."""
        conv = conversation_with_metrics
        response = api_client.get(self._url(conv.id))

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for key in (
            "conversation_id",
            "agent_id",
            "agent_name",
            "messages",
            "session_metrics",
        ):
            assert key in data

    def test_conversation_id_matches(
        self, api_client, conversation_with_metrics
    ):
        """conversation_id in response matches requested conversation."""
        conv = conversation_with_metrics
        response = api_client.get(self._url(conv.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["conversation_id"] == conv.id

    def test_messages_are_present_and_ordered(
        self, api_client, conversation_with_metrics
    ):
        """Messages array is non-empty and ordered chronologically."""
        conv = conversation_with_metrics
        response = api_client.get(self._url(conv.id))

        assert response.status_code == status.HTTP_200_OK
        messages = response.json()["messages"]
        assert len(messages) >= 2
        timestamps = [m["created_at"] for m in messages]
        assert timestamps == sorted(timestamps)

    def test_message_has_required_fields(
        self, api_client, conversation_with_metrics
    ):
        """Each message object has id, role, text, created_at, metrics."""
        conv = conversation_with_metrics
        response = api_client.get(self._url(conv.id))

        assert response.status_code == status.HTTP_200_OK
        msg = response.json()["messages"][0]
        for key in ("id", "role", "text", "created_at", "metrics"):
            assert key in msg

    def test_session_metrics_attached(
        self, api_client, conversation_with_metrics
    ):
        """session_metrics is a dict (may contain metrics we created)."""
        conv = conversation_with_metrics
        response = api_client.get(self._url(conv.id))

        assert response.status_code == status.HTTP_200_OK
        session_metrics = response.json()["session_metrics"]
        assert isinstance(session_metrics, dict)
        assert "response_length_mean" in session_metrics

    def test_other_users_conversation_returns_403(
        self, api_client, other_user, other_agent, dataset
    ):
        """Accessing another user's conversation returns 403."""
        other_conv = baker.make(
            Conversation, user=other_user, agent=other_agent, data_set=dataset
        )
        response = api_client.get(self._url(other_conv.id))

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_nonexistent_conversation_returns_404(self, api_client):
        """Non-existent conversation ID returns 404."""
        response = api_client.get(self._url(999999))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_turn_metrics_attached_to_assistant_messages(
        self, api_client, conversation_with_metrics
    ):
        """Assistant message has turn metrics attached."""
        conv = conversation_with_metrics
        response = api_client.get(self._url(conv.id))

        assert response.status_code == status.HTTP_200_OK
        messages = response.json()["messages"]
        assistant_msgs = [m for m in messages if m["role"] == "assistant"]
        assert len(assistant_msgs) >= 1
        assert "response_length" in assistant_msgs[0]["metrics"]

    def test_unauthenticated_returns_401(self, conversation_with_metrics):
        """Unauthenticated request returns 401."""
        conv = conversation_with_metrics
        response = APIClient().get(self._url(conv.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===========================================================================
# Metrics catalog endpoint
# ===========================================================================


class TestMetricsCatalogEndpoint:
    URL = "/api/analytics/metrics/"

    def test_returns_200_with_list(self, api_client):
        """Metrics catalog returns 200 with a list."""
        response = api_client.get(self.URL)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_each_metric_has_required_fields(self, api_client):
        """Each metric definition has required fields."""
        response = api_client.get(self.URL)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) > 0
        for metric in data:
            for key in ("name", "display_name", "description", "level", "stage"):
                assert key in metric

    def test_filter_by_level_turn(self, api_client):
        """level=turn filter returns only turn-level metrics."""
        response = api_client.get(self.URL, {"level": "turn"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        for metric in data:
            assert metric["level"] == "turn"

    def test_filter_by_stage_1(self, api_client):
        """stage=1 filter returns only stage-1 metrics."""
        response = api_client.get(self.URL, {"stage": 1})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        for metric in data:
            assert metric["stage"] == 1

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        response = APIClient().get(self.URL)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===========================================================================
# Outliers endpoint
# ===========================================================================


class TestOutliersEndpoint:
    URL = "/api/analytics/outliers/"

    def _params(self, metric_name="test_metric", **extra):
        today = date.today()
        return {
            "metric_name": metric_name,
            "start_date": str(today),
            "end_date": str(today),
            **extra,
        }

    def test_missing_metric_name_returns_400(self, api_client):
        """Omitting metric_name returns 400."""
        today = date.today()
        response = api_client.get(
            self.URL, {"start_date": str(today), "end_date": str(today)}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_returns_list(self, api_client, agent, dataset):
        """Valid request returns a list (possibly empty)."""
        response = api_client.get(self.URL, self._params())

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_outlier_structure_when_data_exists(self, api_client, user, agent, dataset):
        """When there is data, each outlier has expected fields."""
        # Create 5 conversations with varying session metric values
        for i in range(5):
            conv = baker.make(Conversation, user=user, agent=agent, data_set=dataset)
            baker.make(
                SessionMetric,
                conversation=conv,
                metric_name="test_metric",
                value=float(i * 10),
                count=1,
                agent_id=agent.id,
                agent_version=1,
                model="gpt-4",
                timestamp=timezone.now(),
            )

        response = api_client.get(self.URL, self._params())

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        if data:
            outlier = data[0]
            for key in (
                "conversation_id",
                "agent_name",
                "metric_name",
                "value",
                "percentile",
                "created_at",
                "message_count",
            ):
                assert key in outlier

    def test_filters_to_users_own_agents(
        self, api_client, user, agent, other_user, other_agent, dataset
    ):
        """Outliers returned only belong to the requesting user's agents."""
        # Create session metric for other user's agent
        other_conv = baker.make(
            Conversation, user=other_user, agent=other_agent, data_set=dataset
        )
        baker.make(
            SessionMetric,
            conversation=other_conv,
            metric_name="test_metric",
            value=99.0,
            count=1,
            agent_id=other_agent.id,
            agent_version=1,
            model="gpt-4",
            timestamp=timezone.now(),
        )

        # Create metric for the requesting user's agent too
        my_conv = baker.make(Conversation, user=user, agent=agent, data_set=dataset)
        baker.make(
            SessionMetric,
            conversation=my_conv,
            metric_name="test_metric",
            value=50.0,
            count=1,
            agent_id=agent.id,
            agent_version=1,
            model="gpt-4",
            timestamp=timezone.now(),
        )

        response = api_client.get(self.URL, self._params())

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        returned_agent_ids = {o["agent_id"] for o in data}
        assert other_agent.id not in returned_agent_ids

    def test_agent_id_filter_other_users_agent_returns_404(
        self, api_client, other_agent
    ):
        """Filtering by another user's agent_id returns 404."""
        response = api_client.get(
            self.URL, self._params(agent_id=str(other_agent.id))
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_missing_dates_returns_400(self, api_client):
        """Omitting both dates returns 400."""
        response = api_client.get(self.URL, {"metric_name": "test_metric"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        today = date.today()
        response = APIClient().get(
            self.URL,
            {"metric_name": "test_metric", "start_date": str(today), "end_date": str(today)},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===========================================================================
# Authentication guard – all endpoints
# ===========================================================================


class TestAuthenticationRequired:
    """All analytics endpoints must return 401 for unauthenticated requests."""

    ENDPOINTS = [
        "/api/analytics/overview/",
        "/api/analytics/timeseries/",
        "/api/analytics/distribution/",
        "/api/analytics/conversations/",
        "/api/analytics/metrics/",
        "/api/analytics/outliers/",
    ]

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_endpoint_requires_auth(self, endpoint):
        response = APIClient().get(endpoint)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
            f"Expected 401 for {endpoint}, got {response.status_code}"
        )
