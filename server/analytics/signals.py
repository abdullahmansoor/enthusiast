"""
Django signals for automatic metrics evaluation.

Automatically triggers evaluation when:
- A new message is created
- A conversation is updated
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from agent.models import Message, Conversation
from analytics.tasks import evaluate_message_task, evaluate_conversation_task


# Get analytics configuration
ANALYTICS_CONFIG = getattr(settings, 'ANALYTICS_CONFIG', {})
ASYNC_EVALUATION = ANALYTICS_CONFIG.get('async_evaluation', True)


@receiver(post_save, sender=Message)
def evaluate_message_on_create(sender, instance, created, **kwargs):
    """
    Automatically evaluate a message when it's created.

    Only evaluates assistant messages.
    Also triggers session + daily rollup after every assistant reply.
    """
    if not created:
        return

    if instance.role not in ('assistant', 'ai'):
        return

    conversation = instance.conversation

    if ASYNC_EVALUATION:
        from analytics.tasks import rollup_daily_metrics_task
        evaluate_message_task.delay(instance.id, stage=3)
        evaluate_conversation_task.apply_async(args=[conversation.id], countdown=2)
        rollup_daily_metrics_task.apply_async(countdown=10)
    else:
        from analytics.services import MetricsService
        from datetime import date
        service = MetricsService()
        service.compute_turn_metrics(instance, stage=3)
        service.compute_session_metrics(conversation)
        service.rollup_daily_metrics(date.today())


# Optional: Disconnect signals for testing
def disconnect_analytics_signals():
    """
    Disconnect analytics signals.

    Useful for testing when you don't want automatic evaluation.

    Usage:
        from analytics.signals import disconnect_analytics_signals
        disconnect_analytics_signals()
    """
    post_save.disconnect(evaluate_message_on_create, sender=Message)


def reconnect_analytics_signals():
    """
    Reconnect analytics signals after disconnecting.

    Usage:
        from analytics.signals import reconnect_analytics_signals
        reconnect_analytics_signals()
    """
    post_save.connect(evaluate_message_on_create, sender=Message)
