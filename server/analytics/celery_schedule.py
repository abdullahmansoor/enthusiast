"""
Celery Beat schedule for analytics periodic tasks.

Add this to your celery.py configuration:

    from analytics.celery_schedule import ANALYTICS_BEAT_SCHEDULE
    app.conf.beat_schedule.update(ANALYTICS_BEAT_SCHEDULE)

Or merge with your existing beat_schedule in pecl/celery.py
"""

from celery.schedules import crontab


ANALYTICS_BEAT_SCHEDULE = {
    # Daily rollup - runs every day at 1 AM
    'analytics-daily-rollup': {
        'task': 'analytics.daily_rollup_all_agents',
        'schedule': crontab(hour=1, minute=0),
        'args': (),  # Will use yesterday by default
    },

    # Cleanup old turn metrics - runs weekly on Sunday at 2 AM
    'analytics-cleanup-old-metrics': {
        'task': 'analytics.cleanup_old_turn_metrics',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),  # Sunday
        'args': (90,),  # Keep 90 days of turn metrics
    },
}


# Alternative: More frequent rollups (every 6 hours)
ANALYTICS_BEAT_SCHEDULE_FREQUENT = {
    'analytics-frequent-rollup': {
        'task': 'analytics.daily_rollup_all_agents',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
        'args': (),
    },
    'analytics-cleanup-old-metrics': {
        'task': 'analytics.cleanup_old_turn_metrics',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),
        'args': (90,),
    },
}
