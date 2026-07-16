from django.apps import AppConfig


class GoogleCalendarConfig(AppConfig):
    """App própria (models e migrations independentes) para o provedor Google.

    Cada integração futura (Outlook, Slack) segue o mesmo padrão — uma app
    aninhada em apps.integrations, nunca compartilhando tabelas/migrations
    com outro provedor.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.integrations.google_calendar"
    label = "google_calendar"

    def ready(self) -> None:
        from apps.integrations.registry import register_calendar_provider

        from .service import GoogleCalendarService

        register_calendar_provider("google_calendar", GoogleCalendarService)
