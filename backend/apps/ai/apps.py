from django.apps import AppConfig


class AIConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai"
    verbose_name = "AI能力"

    def ready(self):
        from .runtime_registry import bootstrap_runtime_registry

        bootstrap_runtime_registry()
