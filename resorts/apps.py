from django.apps import AppConfig


class ResortsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'resorts'
    
    def ready(self):
        import resorts.signals  # Register signals when app loads
