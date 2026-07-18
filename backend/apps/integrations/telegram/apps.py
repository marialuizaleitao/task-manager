from django.apps import AppConfig


class TelegramConfig(AppConfig):
    """App própria (models e migrations independentes) para o provedor Telegram.

    Segue exatamente o mesmo padrão de apps.integrations.google_calendar:
    uma app aninhada em apps.integrations, com seu próprio ciclo de vida de
    schema, registrada no registry por ready().
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.integrations.telegram"
    label = "telegram"

    def ready(self) -> None:
        from apps.integrations.registry import register_notification_provider

        from .service import TelegramService

        register_notification_provider("telegram", TelegramService)
