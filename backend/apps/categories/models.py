from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

hex_color_validator = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Informe uma cor no formato hexadecimal, ex.: #1A2B3C.",
)


class Category(models.Model):
    """Categoria usada para organizar as tarefas de um usuário."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    color = models.CharField(max_length=7, validators=[hex_color_validator])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "name"], name="unique_category_name_per_owner"),
        ]

    def __str__(self) -> str:
        return self.name
