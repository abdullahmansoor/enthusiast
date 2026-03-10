"""
Management command to backfill analytics session and daily metrics.

Run on startup to ensure all conversations have session metrics and daily
rollups computed. Safe to run multiple times — compute_session_metrics
upserts, and rollup_daily_metrics uses update_or_create.

Usage:
    python manage.py backfill_analytics
    python manage.py backfill_analytics --days 90
    python manage.py backfill_analytics --force   # recompute even if metrics exist
"""

from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from agent.models import Conversation
from analytics.models import SessionMetric, DailyMetric
from analytics.services.metrics_service import MetricsService


class Command(BaseCommand):
    help = "Backfill analytics session and daily metrics for existing conversations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=365,
            help="Number of days back to backfill (default: 365)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Recompute metrics even for conversations that already have session metrics",
        )

    def handle(self, *args, **options):
        days = options["days"]
        force = options["force"]
        since = timezone.now() - timedelta(days=days)

        conversations = Conversation.objects.filter(started_at__gte=since)
        total = conversations.count()

        if total == 0:
            self.stdout.write("No conversations found.")
            return

        self.stdout.write(f"Backfilling metrics for {total} conversations (last {days} days)...")

        service = MetricsService()
        processed = 0
        skipped = 0

        for conv in conversations.iterator():
            has_metrics = SessionMetric.objects.filter(conversation=conv).exists()

            if has_metrics and not force:
                skipped += 1
                continue

            try:
                service.compute_session_metrics(conv)
                processed += 1
            except Exception as e:
                self.stderr.write(f"  Error on conversation {conv.id}: {e}")

        self.stdout.write(f"  Processed: {processed}, Skipped (already computed): {skipped}")

        # Rollup daily metrics for all affected dates
        self.stdout.write("Rolling up daily metrics...")
        today = date.today()
        start_date = (timezone.now() - timedelta(days=days)).date()
        current = start_date
        daily_count = 0

        while current <= today:
            metrics = service.rollup_daily_metrics(current)
            if metrics:
                daily_count += len(metrics)
            current += timedelta(days=1)

        self.stdout.write(f"  Daily metrics created/updated: {daily_count}")
        self.stdout.write(self.style.SUCCESS("Analytics backfill complete."))
