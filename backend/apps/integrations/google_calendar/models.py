from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.integrations.crypto import EncryptedTextField


class GoogleCalendarCredential(models.Model):
    """Credenciais OAuth2 do usuário para a Google Calendar API.

    Um usuário tem no máximo uma credencial (OneToOne): reconectar
    sobrescreve a anterior em vez de acumular históricos, já que o Google
    sempre emite um novo par de tokens a cada consentimento completo.
    """

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="google_calendar_credential",
    )
    access_token = EncryptedTextField()
    refresh_token = EncryptedTextField()
    expires_at = models.DateTimeField()
    calendar_id = models.CharField(max_length=255, default="primary")
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_token_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def __str__(self) -> str:
        return f"Google Calendar de {self.owner_id}"


class SyncStatus(models.TextChoices):
    PENDING = "pending", "Pendente"
    SYNCED = "synced", "Sincronizado"
    FAILED = "failed", "Falhou"


class GoogleCalendarEventLink(models.Model):
    """Vínculo entre uma Task e o evento correspondente no Google Calendar."""

    task = models.OneToOneField(
        "tasks.Task",
        on_delete=models.CASCADE,
        related_name="google_calendar_link",
    )
    google_event_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=SyncStatus.choices, default=SyncStatus.PENDING)
    last_error = models.TextField(blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"task={self.task_id} event={self.google_event_id or '(nenhum)'}"
