from rest_framework import serializers

from apps.categories.models import Category

from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "completed",
            "category",
            "due_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None:
            # Restringe as categorias aceitas às do próprio usuário: uma categoria de
            # outro usuário simplesmente "não existe" para este serializer, sem
            # precisar de uma validação de posse separada.
            self.fields["category"].queryset = Category.objects.filter(owner=request.user)

    def validate_title(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("O título da tarefa não pode ser vazio.")
        return value
