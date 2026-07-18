from django.conf import settings
from django.db import models

from apps.categories.models import Category


class Task(models.Model):
    """Tarefa de um usuário, opcionalmente associada a uma categoria."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # due_date_before/after e ordering=due_date são filtros suportados
            # pela API; sem este índice, filtrar ou ordenar por due_date força
            # um sort temporário (TEMP B-TREE) mesmo após reduzir por owner_id
            # via índice — confirmado empiricamente com QuerySet.explain().
            models.Index(fields=["owner", "due_date"], name="tasks_owner_due_date_idx"),
            # created_at é a ordenação padrão de toda listagem (Meta.ordering)
            # e também tem filtro de intervalo (created_before/after); mesmo
            # padrão de TEMP B-TREE observado sem este índice.
            models.Index(fields=["owner", "-created_at"], name="tasks_owner_created_idx"),
        ]

    def __str__(self) -> str:
        return self.title
