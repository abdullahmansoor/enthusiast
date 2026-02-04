from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics'
    verbose_name = 'Analytics & Metrics'

    def ready(self):
        """
        Import evaluators and signals when Django starts.

        This:
        1. Registers all metrics in the global registry
        2. Connects signals for automatic evaluation
        """
        try:
            # Import evaluators to register metrics
            from analytics.evaluators import rule_based  # noqa
            from analytics.evaluators import local_ml  # noqa
            from analytics.evaluators import llm_judges  # noqa

            # Import signals to connect them
            from analytics import signals  # noqa

        except ImportError:
            # During initial migrations, these modules may not be available yet
            pass
