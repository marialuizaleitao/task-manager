from django.conf import settings
from django.db import models

from apps.tasks.models import Task


class TaskShare(models.Model):
    """Compartilhamento de uma tarefa com outro usuário, com nível de acesso explícito."""

    class Permission(models.TextChoices):
        READ = "read", "Leitura"
        EDIT = "edit", "Edição"

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="shares")
    shared_with = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_shares",
    )
    permission = models.CharField(
        max_length=10,
        choices=Permission.choices,
        default=Permission.READ,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["task", "shared_with"],
                name="unique_task_share_per_user",
            )
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.task_id} compartilhada com {self.shared_with_id} ({self.permission})"
