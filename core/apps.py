from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """
        Import signals when the app is ready.
        This is the recommended way to register signals to avoid side-effects.
        """
        import core.signals