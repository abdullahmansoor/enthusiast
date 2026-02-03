"""
Evaluation job tracking model for background metric computation.
"""

import uuid
from django.db import models


class EvaluationJob(models.Model):
    """
    Track evaluation pipeline jobs for monitoring and debugging.

    Used for:
    - Turn-level evaluation (computing metrics for new messages)
    - Session rollup (aggregating turns to sessions)
    - Daily rollup (aggregating sessions to daily metrics)
    """

    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Job metadata
    job_type = models.CharField(max_length=50)  # 'turn_evaluation', 'session_rollup', 'daily_rollup'
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )

    # Date range being processed
    start_date = models.DateField()
    end_date = models.DateField()

    # Progress tracking
    total_items = models.IntegerField(default=0)
    processed_items = models.IntegerField(default=0)
    failed_items = models.IntegerField(default=0)

    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Error tracking
    error_message = models.TextField(blank=True)

    # Configuration (JSON)
    config = models.JSONField(default=dict, blank=True)
    # Example config:
    # {
    #     "max_stage": 3,  # Max evaluation stage to run
    #     "sampling_rate": 0.1,  # For LLM judges
    #     "agent_ids": ["uuid1", "uuid2"],  # Filter specific agents
    # }

    class Meta:
        db_table = 'analytics_evaluation_jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['job_type', 'status']),
        ]

    def __str__(self):
        return f"{self.job_type} {self.status} ({self.start_date} to {self.end_date})"

    def mark_started(self):
        """Mark job as started"""
        from django.utils import timezone
        self.status = self.STATUS_RUNNING
        self.started_at = timezone.now()
        self.save()

    def mark_completed(self):
        """Mark job as completed"""
        from django.utils import timezone
        self.status = self.STATUS_COMPLETED
        self.completed_at = timezone.now()
        self.save()

    def mark_failed(self, error_message):
        """Mark job as failed with error message"""
        from django.utils import timezone
        self.status = self.STATUS_FAILED
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save()

    def update_progress(self, processed, failed=0):
        """Update progress counters"""
        self.processed_items = processed
        self.failed_items = failed
        self.save(update_fields=['processed_items', 'failed_items'])

    @property
    def progress_percentage(self):
        """Calculate progress percentage"""
        if self.total_items == 0:
            return 0
        return (self.processed_items / self.total_items) * 100

    @property
    def duration_seconds(self):
        """Calculate job duration in seconds"""
        if not self.started_at:
            return None
        end_time = self.completed_at or self.created_at
        return (end_time - self.started_at).total_seconds()
