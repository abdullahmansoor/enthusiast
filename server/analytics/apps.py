from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics'
    verbose_name = 'Analytics & Metrics'

    def ready(self):
        """
        Import evaluators when Django starts to register them.
        This ensures all metrics are registered in the global registry.
        """
        try:
            # Import evaluators to register metrics
            from analytics.evaluators import rule_based  # noqa
            from analytics.evaluators import local_ml  # noqa
            from analytics.evaluators import llm_judges  # noqa
        except ImportError:
            # During initial migrations, these modules may not be available yet
            pass
