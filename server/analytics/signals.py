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
    Runs asynchronously via Celery if ASYNC_EVALUATION is True.

    Args:
        sender: Message model
        instance: Message instance
        created: True if this is a new message
    """
    if not created:
        # Only evaluate new messages, not updates
        return

    if instance.role not in ('assistant', 'ai'):
        # Only evaluate assistant responses
        return

    # Trigger evaluation
    if ASYNC_EVALUATION:
        # Run in background via Celery
        evaluate_message_task.delay(instance.id, stage=3)
    else:
        # Run synchronously (for testing or debugging)
        from analytics.services import MetricsService
        service = MetricsService()
        service.compute_turn_metrics(instance, stage=3)


@receiver(post_save, sender=Conversation)
def evaluate_conversation_on_update(sender, instance, created, **kwargs):
    """
    Trigger session-level evaluation periodically.

    We evaluate after every N messages to avoid computing too frequently.

    Args:
        sender: Conversation model
        instance: Conversation instance
        created: True if this is a new conversation
    """
    if created:
        # Don't evaluate empty conversations
        return

    # Get message count
    message_count = instance.messages.count()

    # Evaluate after every 2 messages (1 turn), or every 5 messages thereafter
    should_evaluate = (
        message_count >= 2 and
        (message_count % 2 == 0 or message_count % 5 == 0)
    )

    if should_evaluate:
        if ASYNC_EVALUATION:
            # Run in background
            evaluate_conversation_task.delay(instance.id)
            from analytics.tasks import rollup_daily_metrics_task
            rollup_daily_metrics_task.apply_async(countdown=5)
        else:
            # Run synchronously
            from analytics.services import MetricsService
            from datetime import date
            service = MetricsService()
            service.compute_session_metrics(instance)
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
    post_save.disconnect(evaluate_conversation_on_update, sender=Conversation)


def reconnect_analytics_signals():
    """
    Reconnect analytics signals after disconnecting.

    Usage:
        from analytics.signals import reconnect_analytics_signals
        reconnect_analytics_signals()
    """
    post_save.connect(evaluate_message_on_create, sender=Message)
    post_save.connect(evaluate_conversation_on_update, sender=Conversation)
