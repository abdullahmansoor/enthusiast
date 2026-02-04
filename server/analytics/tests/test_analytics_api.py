"""
Tests for Analytics Dashboard API.

Tests all API endpoints:
- GET /api/analytics/overview/
- GET /api/analytics/timeseries/
- GET /api/analytics/distribution/
- GET /api/analytics/conversations/
- GET /api/analytics/conversations/{id}/detail/
- GET /api/analytics/metrics/
- GET /api/analytics/outliers/
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta
from django.utils import timezone

from analytics.services import MetricsService
from analytics.models import TurnMetric, SessionMetric, DailyMetric
from analytics.signals import disconnect_analytics_signals, reconnect_analytics_signals
from agent.models import Agent, Conversation, Message
from catalog.models import DataSet

User = get_user_model()


class AnalyticsAPITestCase(TestCase):
    """Test Analytics Dashboard API endpoints"""

    def setUp(self):
        """Set up test data"""
        # Create users
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )

        # Create client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create dataset
        self.dataset = DataSet.objects.create(
            name='Test Dataset',
            description='Test dataset'
        )

        # Create agent
        self.agent = Agent.objects.create(
            name='Test Agent',
            dataset=self.dataset,
            created_by=self.user
        )

        # Create other user's agent
        self.other_agent = Agent.objects.create(
            name='Other Agent',
            dataset=self.dataset,
            created_by=self.other_user
        )

        # Disconnect signals
        disconnect_analytics_signals()

        self.service = MetricsService()

    def tearDown(self):
        """Clean up"""
        reconnect_analytics_signals()

    def _create_conversation_with_metrics(self, agent, num_messages=2):
        """Helper to create conversation with messages and metrics"""
        conversation = Conversation.objects.create(
            agent=agent,
            user=self.user,
            dataset=self.dataset
        )

        for i in range(num_messages):
            # User message
            Message.objects.create(
                conversation=conversation,
                role='user',
                text=f'Question {i+1}'
            )

            # Assistant message
            msg = Message.objects.create(
                conversation=conversation,
                role='assistant',
                text=f'Answer {i+1}'
            )

            # Compute metrics
            self.service.compute_turn_metrics(msg, stage=1)

        # Compute session metrics
        self.service.compute_session_metrics(conversation)

        # Rollup to daily
        today = date.today()
        self.service.rollup_daily_metrics(today, agent_id=str(agent.id))

        return conversation

    def test_overview_endpoint(self):
        """Test GET /api/analytics/overview/"""
        # Create test data
        self._create_conversation_with_metrics(self.agent)

        # Make request
        response = self.client.get('/api/analytics/overview/')

        # Should succeed
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check response structure
        data = response.json()
        self.assertIn('total_conversations', data)
        self.assertIn('date_range', data)
        self.assertEqual(data['total_conversations'], 1)

    def test_overview_with_date_range(self):
        """Test overview with custom date range"""
        self._create_conversation_with_metrics(self.agent)

        today = date.today()
        start_date = today - timedelta(days=7)

        response = self.client.get(
            f'/api/analytics/overview/?start_date={start_date}&end_date={today}'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['date_range']['start'], start_date.isoformat())
        self.assertEqual(data['date_range']['end'], today.isoformat())

    def test_overview_with_agent_filter(self):
        """Test overview filtered by agent"""
        self._create_conversation_with_metrics(self.agent)

        response = self.client.get(
            f'/api/analytics/overview/?agent_id={self.agent.id}'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['total_conversations'], 1)

    def test_overview_denies_other_user_agent(self):
        """Test that overview denies access to other user's agents"""
        response = self.client.get(
            f'/api/analytics/overview/?agent_id={self.other_agent.id}'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_timeseries_endpoint(self):
        """Test GET /api/analytics/timeseries/"""
        self._create_conversation_with_metrics(self.agent)

        today = date.today()
        start_date = today - timedelta(days=7)

        response = self.client.get(
            f'/api/analytics/timeseries/?metric_name=response_length_mean'
            f'&start_date={start_date}&end_date={today}'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('metric_name', data)
        self.assertIn('data', data)
        self.assertEqual(data['metric_name'], 'response_length_mean')
        self.assertIsInstance(data['data'], list)

    def test_timeseries_requires_metric_name(self):
        """Test that timeseries requires metric_name"""
        today = date.today()
        response = self.client.get(
            f'/api/analytics/timeseries/?start_date={today}&end_date={today}'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_timeseries_requires_dates(self):
        """Test that timeseries requires start_date and end_date"""
        response = self.client.get(
            '/api/analytics/timeseries/?metric_name=response_length'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_distribution_endpoint(self):
        """Test GET /api/analytics/distribution/"""
        self._create_conversation_with_metrics(self.agent)

        today = date.today()

        response = self.client.get(
            f'/api/analytics/distribution/?metric_name=response_length_mean'
            f'&start_date={today}&end_date={today}'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('metric_name', data)
        self.assertIn('stats', data)
        self.assertIn('values', data)

        # Check stats structure
        stats = data['stats']
        self.assertIn('mean', stats)
        self.assertIn('median', stats)
        self.assertIn('count', stats)

    def test_conversations_list_endpoint(self):
        """Test GET /api/analytics/conversations/"""
        self._create_conversation_with_metrics(self.agent)
        self._create_conversation_with_metrics(self.agent)

        response = self.client.get('/api/analytics/conversations/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('results', data)
        self.assertIn('count', data)
        self.assertIn('total', data)
        self.assertIn('has_more', data)

        # Should have 2 conversations
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['total'], 2)
        self.assertFalse(data['has_more'])

        # Check result structure
        result = data['results'][0]
        self.assertIn('id', result)
        self.assertIn('agent_id', result)
        self.assertIn('agent_name', result)
        self.assertIn('created_at', result)
        self.assertIn('message_count', result)
        self.assertIn('metrics', result)

    def test_conversations_list_pagination(self):
        """Test conversation list pagination"""
        # Create 5 conversations
        for _ in range(5):
            self._create_conversation_with_metrics(self.agent, num_messages=1)

        # Request page 1 with page_size=2
        response = self.client.get(
            '/api/analytics/conversations/?page=1&page_size=2'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['total'], 5)
        self.assertTrue(data['has_more'])

    def test_conversations_list_filters_by_agent(self):
        """Test conversation list filtered by agent"""
        self._create_conversation_with_metrics(self.agent)

        # Other user's conversation should not appear
        other_conv = self._create_conversation_with_metrics(self.other_agent)

        response = self.client.get(
            f'/api/analytics/conversations/?agent_id={self.agent.id}'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        # Should only show user's conversations
        self.assertEqual(data['count'], 1)

    def test_conversation_detail_endpoint(self):
        """Test GET /api/analytics/conversations/{id}/detail/"""
        conversation = self._create_conversation_with_metrics(self.agent)

        response = self.client.get(
            f'/api/analytics/conversations/{conversation.id}/detail/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['conversation_id'], str(conversation.id))
        self.assertEqual(data['agent_id'], str(self.agent.id))
        self.assertIn('messages', data)
        self.assertIn('session_metrics', data)

        # Check messages structure
        self.assertGreater(len(data['messages']), 0)
        message = data['messages'][0]
        self.assertIn('id', message)
        self.assertIn('role', message)
        self.assertIn('text', message)
        self.assertIn('metrics', message)

    def test_conversation_detail_denies_other_user(self):
        """Test that conversation detail denies access to other user's conversations"""
        # Create conversation for other user
        other_conv = Conversation.objects.create(
            agent=self.other_agent,
            user=self.other_user,
            dataset=self.dataset
        )

        response = self.client.get(
            f'/api/analytics/conversations/{other_conv.id}/detail/'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_conversation_detail_not_found(self):
        """Test conversation detail with non-existent ID"""
        from uuid import uuid4
        fake_id = uuid4()

        response = self.client.get(
            f'/api/analytics/conversations/{fake_id}/detail/'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_metrics_catalog_endpoint(self):
        """Test GET /api/analytics/metrics/"""
        response = self.client.get('/api/analytics/metrics/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIsInstance(data, list)

        # Should have multiple metrics
        self.assertGreater(len(data), 0)

        # Check metric structure
        metric = data[0]
        self.assertIn('name', metric)
        self.assertIn('display_name', metric)
        self.assertIn('description', metric)
        self.assertIn('level', metric)
        self.assertIn('stage', metric)

    def test_metrics_catalog_filter_by_level(self):
        """Test metrics catalog filtered by level"""
        response = self.client.get('/api/analytics/metrics/?level=turn')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        # All should be turn-level
        for metric in data:
            self.assertEqual(metric['level'], 'turn')

    def test_metrics_catalog_filter_by_stage(self):
        """Test metrics catalog filtered by stage"""
        response = self.client.get('/api/analytics/metrics/?stage=1')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        # All should be stage 1
        for metric in data:
            self.assertEqual(metric['stage'], 1)

    def test_outliers_endpoint(self):
        """Test GET /api/analytics/outliers/"""
        # Create multiple conversations with varying metrics
        for i in range(5):
            conv = self._create_conversation_with_metrics(self.agent, num_messages=1)

            # Manually create a session metric with varying values
            SessionMetric.objects.create(
                conversation=conv,
                metric_name='test_metric',
                value=float(i * 10),
                count=1,
                agent_id=self.agent.id,
                agent_version=1,
                model='gpt-4',
                timestamp=timezone.now()
            )

        today = date.today()

        response = self.client.get(
            f'/api/analytics/outliers/?metric_name=test_metric'
            f'&start_date={today}&end_date={today}'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIsInstance(data, list)

        # Check outlier structure if any
        if len(data) > 0:
            outlier = data[0]
            self.assertIn('conversation_id', outlier)
            self.assertIn('agent_name', outlier)
            self.assertIn('metric_name', outlier)
            self.assertIn('value', outlier)
            self.assertIn('percentile', outlier)

    def test_outliers_requires_metric_name(self):
        """Test that outliers requires metric_name"""
        today = date.today()
        response = self.client.get(
            f'/api/analytics/outliers/?start_date={today}&end_date={today}'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_api_requires_authentication(self):
        """Test that API endpoints require authentication"""
        # Create unauthenticated client
        unauth_client = APIClient()

        endpoints = [
            '/api/analytics/overview/',
            '/api/analytics/timeseries/',
            '/api/analytics/distribution/',
            '/api/analytics/conversations/',
            '/api/analytics/metrics/',
        ]

        for endpoint in endpoints:
            response = unauth_client.get(endpoint)
            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"Endpoint {endpoint} should require authentication"
            )

    def test_caching_works(self):
        """Test that caching works for overview endpoint"""
        from django.core.cache import cache

        self._create_conversation_with_metrics(self.agent)

        # First request - should miss cache
        response1 = self.client.get('/api/analytics/overview/')
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Create another conversation
        self._create_conversation_with_metrics(self.agent)

        # Second request - should hit cache and return same data
        response2 = self.client.get('/api/analytics/overview/')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        # Data should be the same (cached)
        self.assertEqual(
            response1.json()['total_conversations'],
            response2.json()['total_conversations']
        )

        # Clear cache
        cache.clear()

        # Third request - should see new data
        response3 = self.client.get('/api/analytics/overview/')
        self.assertEqual(response3.status_code, status.HTTP_200_OK)

        # Now it should show 2 conversations
        self.assertEqual(response3.json()['total_conversations'], 2)
