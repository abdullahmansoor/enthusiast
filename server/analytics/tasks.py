"""
Celery tasks for analytics evaluation pipeline.

Tasks:
- evaluate_message_task: Compute metrics for a new message
- evaluate_conversation_task: Compute session metrics
- rollup_daily_metrics_task: Daily aggregation
- backfill_metrics_task: Backfill metrics for date range
"""

from celery import shared_task
from datetime import date, timedelta
from django.utils import timezone

from analytics.services import MetricsService
from analytics.models import EvaluationJob
from agent.models import Message, Conversation


@shared_task(name='analytics.evaluate_message')
def evaluate_message_task(message_id: int, stage: int = 3):
    """
    Evaluate a single message and compute turn-level metrics.

    Args:
        message_id: Message ID to evaluate
        stage: Max evaluation stage (1=rules, 2=ML, 3=LLM)

    Returns:
        Dict with number of metrics computed
    """
    try:
        message = Message.objects.get(id=message_id)

        # Only evaluate assistant messages
        if message.role not in ('assistant', 'ai'):
            return {'message': 'Skipped: not an assistant message', 'metrics_computed': 0}

        service = MetricsService()
        metrics = service.compute_turn_metrics(message, stage=stage)

        return {
            'message': 'Success',
            'message_id': message_id,
            'metrics_computed': len(metrics),
            'metric_names': [m.metric_name for m in metrics]
        }

    except Message.DoesNotExist:
        return {'error': f'Message {message_id} not found'}
    except Exception as e:
        return {'error': str(e)}


@shared_task(name='analytics.evaluate_conversation')
def evaluate_conversation_task(conversation_id: int):
    """
    Evaluate a conversation and compute session-level metrics.

    This should be called after a conversation is complete or after
    several messages have been exchanged.

    Args:
        conversation_id: Conversation ID to evaluate

    Returns:
        Dict with number of metrics computed
    """
    try:
        conversation = Conversation.objects.get(id=conversation_id)

        service = MetricsService()
        metrics = service.compute_session_metrics(conversation)

        return {
            'message': 'Success',
            'conversation_id': conversation_id,
            'metrics_computed': len(metrics),
            'metric_names': [m.metric_name for m in metrics]
        }

    except Conversation.DoesNotExist:
        return {'error': f'Conversation {conversation_id} not found'}
    except Exception as e:
        return {'error': str(e)}


@shared_task(name='analytics.rollup_daily_metrics')
def rollup_daily_metrics_task(target_date: str = None, agent_id: str = None):
    """
    Rollup session metrics to daily aggregates.

    Args:
        target_date: Date to rollup (ISO format YYYY-MM-DD). Defaults to yesterday.
        agent_id: Optional agent UUID filter

    Returns:
        Dict with number of daily metrics created
    """
    try:
        # Parse date
        if target_date:
            target_date_obj = date.fromisoformat(target_date)
        else:
            # Default to yesterday
            target_date_obj = (timezone.now() - timedelta(days=1)).date()

        # Create evaluation job
        job = EvaluationJob.objects.create(
            job_type='daily_rollup',
            start_date=target_date_obj,
            end_date=target_date_obj,
            config={'agent_id': agent_id} if agent_id else {}
        )

        job.mark_started()

        try:
            service = MetricsService()
            metrics = service.rollup_daily_metrics(target_date_obj, agent_id=agent_id)

            job.total_items = len(metrics)
            job.processed_items = len(metrics)
            job.mark_completed()

            return {
                'message': 'Success',
                'date': target_date_obj.isoformat(),
                'metrics_created': len(metrics),
                'job_id': str(job.id)
            }

        except Exception as e:
            job.mark_failed(str(e))
            raise

    except Exception as e:
        return {'error': str(e)}


@shared_task(name='analytics.backfill_metrics')
def backfill_metrics_task(
    start_date: str,
    end_date: str,
    agent_id: str = None,
    max_stage: int = 3
):
    """
    Backfill metrics for a date range.

    This is useful for:
    - Initial setup
    - Recomputing metrics after changes
    - Filling gaps

    Args:
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
        agent_id: Optional agent UUID filter
        max_stage: Max evaluation stage

    Returns:
        Dict with counts of evaluated items
    """
    try:
        start_date_obj = date.fromisoformat(start_date)
        end_date_obj = date.fromisoformat(end_date)

        # Create evaluation job
        job = EvaluationJob.objects.create(
            job_type='backfill',
            start_date=start_date_obj,
            end_date=end_date_obj,
            config={
                'agent_id': agent_id,
                'max_stage': max_stage
            } if agent_id else {'max_stage': max_stage}
        )

        job.mark_started()

        try:
            service = MetricsService()

            # Get conversations in date range
            conversations = Conversation.objects.filter(
                started_at__date__gte=start_date_obj,
                started_at__date__lte=end_date_obj
            )

            if agent_id:
                conversations = conversations.filter(agent_id=agent_id)

            job.total_items = conversations.count()
            job.save()

            processed = 0
            failed = 0

            for conversation in conversations:
                try:
                    # Evaluate all messages in conversation
                    for message in conversation.messages.filter(role__in=['assistant', 'ai']):
                        service.compute_turn_metrics(message, stage=max_stage)

                    # Compute session metrics
                    service.compute_session_metrics(conversation)

                    processed += 1
                    if processed % 10 == 0:
                        job.update_progress(processed, failed)

                except Exception as e:
                    print(f"Error processing conversation {conversation.id}: {e}")
                    failed += 1

            # Rollup to daily for each date in range
            current_date = start_date_obj
            while current_date <= end_date_obj:
                service.rollup_daily_metrics(current_date, agent_id=agent_id)
                current_date += timedelta(days=1)

            job.processed_items = processed
            job.failed_items = failed
            job.mark_completed()

            return {
                'message': 'Success',
                'conversations_processed': processed,
                'failures': failed,
                'job_id': str(job.id)
            }

        except Exception as e:
            job.mark_failed(str(e))
            raise

    except Exception as e:
        return {'error': str(e)}


@shared_task(name='analytics.daily_rollup_all_agents')
def daily_rollup_all_agents_task(target_date: str = None):
    """
    Rollup metrics for all agents for a given date.

    This should be scheduled to run daily via Celery Beat.

    Args:
        target_date: Date to rollup (ISO format). Defaults to yesterday.

    Returns:
        Dict with summary
    """
    try:
        if target_date:
            target_date_obj = date.fromisoformat(target_date)
        else:
            target_date_obj = (timezone.now() - timedelta(days=1)).date()

        from agent.models import Agent

        # Get all active agents
        agents = Agent.objects.filter(deleted_at__isnull=True, status='active')

        service = MetricsService()
        total_metrics = 0

        for agent in agents:
            metrics = service.rollup_daily_metrics(
                target_date_obj,
                agent_id=str(agent.id)
            )
            total_metrics += len(metrics)

        return {
            'message': 'Success',
            'date': target_date_obj.isoformat(),
            'agents_processed': agents.count(),
            'total_metrics': total_metrics
        }

    except Exception as e:
        return {'error': str(e)}


@shared_task(name='analytics.cleanup_old_turn_metrics')
def cleanup_old_turn_metrics_task(days_to_keep: int = 90):
    """
    Clean up old turn-level metrics to save space.

    Session and daily metrics are kept, but turn-level metrics
    are deleted after the specified retention period.

    Args:
        days_to_keep: Number of days to keep turn metrics (default 90)

    Returns:
        Dict with number of deleted metrics
    """
    try:
        from analytics.models import TurnMetric

        cutoff_date = timezone.now() - timedelta(days=days_to_keep)

        deleted_count, _ = TurnMetric.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()

        return {
            'message': 'Success',
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.date().isoformat()
        }

    except Exception as e:
        return {'error': str(e)}
