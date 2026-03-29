from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    """
    Configuration for the 'core' application.
    Ensures signal handlers are connected when Django starts.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = _("Core Application")

    def ready(self):
        """
        Import signal handlers so they are registered.
        """
        import core.signals  # noqa