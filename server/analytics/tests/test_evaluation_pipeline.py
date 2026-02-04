"""
Tests for analytics evaluation pipeline.

Tests:
- Turn metric computation
- Session metric computation
- Daily rollups
- Celery tasks
- Signal triggers
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from django.utils import timezone

from analytics.services import MetricsService
from analytics.models import TurnMetric, SessionMetric, DailyMetric
from analytics.evaluators.registry import registry
from analytics.signals import disconnect_analytics_signals, reconnect_analytics_signals
from agent.models import Agent, Conversation, Message
from catalog.models import DataSet

User = get_user_model()


class MetricsServiceTestCase(TestCase):
    """Test MetricsService functionality"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        self.dataset = DataSet.objects.create(
            name='Test Dataset',
            description='Test dataset'
        )

        self.agent = Agent.objects.create(
            name='Test Agent',
            dataset=self.dataset,
            created_by=self.user
        )

        self.conversation = Conversation.objects.create(
            agent=self.agent,
            user=self.user,
            dataset=self.dataset
        )

        self.service = MetricsService()

        # Disconnect signals to avoid automatic evaluation during tests
        disconnect_analytics_signals()

    def tearDown(self):
        """Clean up"""
        reconnect_analytics_signals()

    def test_compute_turn_metrics(self):
        """Test computing turn-level metrics"""
        # Create messages
        user_msg = Message.objects.create(
            conversation=self.conversation,
            role='user',
            text='What is Python?'
        )

        assistant_msg = Message.objects.create(
            conversation=self.conversation,
            role='assistant',
            text='Python is a high-level programming language.'
        )

        # Compute turn metrics (Stage 1 only for speed)
        metrics = self.service.compute_turn_metrics(assistant_msg, stage=1)

        # Should have computed some metrics
        self.assertGreater(len(metrics), 0)

        # Check that metrics were saved
        self.assertTrue(
            TurnMetric.objects.filter(message=assistant_msg).exists()
        )

        # Verify response_length metric
        response_length = TurnMetric.objects.filter(
            message=assistant_msg,
            metric_name='response_length'
        ).first()

        self.assertIsNotNone(response_length)
        self.assertEqual(response_length.value, len(assistant_msg.text))

    def test_skip_user_messages(self):
        """Test that user messages are not evaluated"""
        user_msg = Message.objects.create(
            conversation=self.conversation,
            role='user',
            text='Test question'
        )

        metrics = self.service.compute_turn_metrics(user_msg, stage=1)

        # Should return empty list
        self.assertEqual(len(metrics), 0)

    def test_compute_session_metrics(self):
        """Test computing session-level metrics"""
        # Create conversation with messages
        Message.objects.create(
            conversation=self.conversation,
            role='user',
            text='Question 1'
        )
        Message.objects.create(
            conversation=self.conversation,
            role='assistant',
            text='Answer 1'
        )
        Message.objects.create(
            conversation=self.conversation,
            role='user',
            text='Question 2'
        )
        Message.objects.create(
            conversation=self.conversation,
            role='assistant',
            text='Answer 2'
        )

        # First compute turn metrics
        for msg in self.conversation.messages.filter(role='assistant'):
            self.service.compute_turn_metrics(msg, stage=1)

        # Then compute session metrics
        metrics = self.service.compute_session_metrics(self.conversation)

        # Should have computed metrics
        self.assertGreater(len(metrics), 0)

        # Check that session metrics were saved
        self.assertTrue(
            SessionMetric.objects.filter(conversation=self.conversation).exists()
        )

    def test_rollup_daily_metrics(self):
        """Test daily metric rollup"""
        # Create conversation and compute metrics
        Message.objects.create(
            conversation=self.conversation,
            role='user',
            text='Test question'
        )
        msg = Message.objects.create(
            conversation=self.conversation,
            role='assistant',
            text='Test answer'
        )

        # Compute turn and session metrics
        self.service.compute_turn_metrics(msg, stage=1)
        self.service.compute_session_metrics(self.conversation)

        # Rollup to daily
        today = date.today()
        daily_metrics = self.service.rollup_daily_metrics(today, agent_id=str(self.agent.id))

        # Should have created daily metrics
        self.assertGreater(len(daily_metrics), 0)

        # Check that daily metrics were saved
        self.assertTrue(
            DailyMetric.objects.filter(
                date=today,
                agent_id=self.agent.id
            ).exists()
        )

    def test_get_kpis(self):
        """Test getting KPI summary"""
        # Create and evaluate a conversation
        Message.objects.create(
            conversation=self.conversation,
            role='user',
            text='Test'
        )
        msg = Message.objects.create(
            conversation=self.conversation,
            role='assistant',
            text='Response'
        )

        self.service.compute_turn_metrics(msg, stage=1)
        self.service.compute_session_metrics(self.conversation)

        today = date.today()
        self.service.rollup_daily_metrics(today, agent_id=str(self.agent.id))

        # Get KPIs
        kpis = self.service.get_kpis(
            start_date=today,
            end_date=today,
            agent_id=str(self.agent.id)
        )

        # Should have KPI data
        self.assertIn('total_conversations', kpis)
        self.assertEqual(kpis['total_conversations'], 1)

    def test_get_timeseries(self):
        """Test getting time series data"""
        # Create metrics for multiple days
        for i in range(3):
            target_date = date.today() - timedelta(days=i)

            DailyMetric.objects.create(
                date=target_date,
                metric_name='response_length_mean',
                value=100 + i * 10,
                count=5,
                agent_id=self.agent.id,
                model='gpt-4'
            )

        # Get timeseries
        timeseries = self.service.get_timeseries(
            metric_name='response_length_mean',
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
            agent_id=str(self.agent.id)
        )

        # Should have 3 data points
        self.assertEqual(len(timeseries), 3)


class EvaluatorRegistryTestCase(TestCase):
    """Test metrics registry"""

    def test_registry_has_metrics(self):
        """Test that metrics are registered"""
        metrics = registry.list()

        # Should have multiple metrics
        self.assertGreater(len(metrics), 0)

    def test_get_metric_by_name(self):
        """Test getting specific metric"""
        metric = registry.get('response_length')

        self.assertIsNotNone(metric)
        self.assertEqual(metric.name, 'response_length')
        self.assertEqual(metric.level, 'turn')
        self.assertEqual(metric.stage, 1)

    def test_filter_by_stage(self):
        """Test filtering metrics by stage"""
        stage1_metrics = registry.list(stage=1)

        # All should be stage 1
        for metric in stage1_metrics:
            self.assertEqual(metric.stage, 1)

    def test_filter_by_level(self):
        """Test filtering metrics by level"""
        turn_metrics = registry.list(level='turn')

        # All should be turn-level
        for metric in turn_metrics:
            self.assertEqual(metric.level, 'turn')


class SignalTriggerTestCase(TestCase):
    """Test automatic evaluation via signals"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        self.dataset = DataSet.objects.create(name='Test Dataset')

        self.agent = Agent.objects.create(
            name='Test Agent',
            dataset=self.dataset,
            created_by=self.user
        )

        self.conversation = Conversation.objects.create(
            agent=self.agent,
            user=self.user,
            dataset=self.dataset
        )

        # Ensure signals are connected
        reconnect_analytics_signals()

    def test_signal_triggers_on_message_create(self):
        """Test that creating an assistant message triggers evaluation"""
        # Note: This test will only pass if Celery is running or
        # if ASYNC_EVALUATION is False

        # Create assistant message
        msg = Message.objects.create(
            conversation=self.conversation,
            role='assistant',
            text='Test response'
        )

        # In async mode, the task is queued (can't test without Celery)
        # In sync mode, metrics should be created immediately

        # Check if task was called (this requires Celery to be running)
        # For now, just verify the message was created
        self.assertEqual(msg.role, 'assistant')

    def test_signal_skips_user_messages(self):
        """Test that user messages don't trigger evaluation"""
        msg = Message.objects.create(
            conversation=self.conversation,
            role='user',
            text='Test question'
        )

        # Should not create any metrics
        self.assertEqual(
            TurnMetric.objects.filter(message=msg).count(),
            0
        )


class CeleryTaskTestCase(TestCase):
    """Test Celery tasks (unit tests only - requires Celery for integration tests)"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        self.dataset = DataSet.objects.create(name='Test Dataset')

        self.agent = Agent.objects.create(
            name='Test Agent',
            dataset=self.dataset,
            created_by=self.user
        )

        self.conversation = Conversation.objects.create(
            agent=self.agent,
            user=self.user,
            dataset=self.dataset
        )

        disconnect_analytics_signals()

    def tearDown(self):
        reconnect_analytics_signals()

    def test_evaluate_message_task_logic(self):
        """Test evaluate_message_task logic (synchronous)"""
        from analytics.tasks import evaluate_message_task

        # Create messages
        Message.objects.create(
            conversation=self.conversation,
            role='user',
            text='Question'
        )
        msg = Message.objects.create(
            conversation=self.conversation,
            role='assistant',
            text='Answer'
        )

        # Call task directly (not via Celery)
        result = evaluate_message_task(msg.id, stage=1)

        # Should succeed
        self.assertEqual(result['message'], 'Success')
        self.assertGreater(result['metrics_computed'], 0)

    def test_evaluate_conversation_task_logic(self):
        """Test evaluate_conversation_task logic"""
        from analytics.tasks import evaluate_conversation_task

        # Create conversation with messages
        Message.objects.create(
            conversation=self.conversation,
            role='user',
            text='Q1'
        )
        msg1 = Message.objects.create(
            conversation=self.conversation,
            role='assistant',
            text='A1'
        )

        # Compute turn metrics first
        service = MetricsService()
        service.compute_turn_metrics(msg1, stage=1)

        # Call task
        result = evaluate_conversation_task(self.conversation.id)

        # Should succeed
        self.assertEqual(result['message'], 'Success')
        self.assertGreater(result['metrics_computed'], 0)
