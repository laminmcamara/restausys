# core/apps.py

from django.apps import AppConfig
import logging


class CoreConfig(AppConfig):
    """App configuration for the Core application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = "Core Application"

    def ready(self):
        """
        Import signal modules when Django app registry is fully loaded.
        This ensures models and channel layers are ready before signal binding.
        """
        try:
            import core.signals  # noqa: F401  # Import solely for side effects
            logging.getLogger(__name__).info("✅ core.signals module loaded successfully.")
        except Exception as e:
            logging.getLogger(__name__).exception(f"⚠️ Failed to import core.signals: {e}")