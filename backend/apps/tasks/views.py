from rest_framework import permissions, viewsets

from .models import Task
from .serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    """CRUD de tarefas, restrito às tarefas do usuário autenticado."""

    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # select_related evita uma query extra por tarefa ao ler o id da
        # categoria relacionada (sem isso, cada tarefa com categoria geraria
        # uma consulta adicional só para resolver task.category.pk).
        queryset = Task.objects.filter(owner=self.request.user).select_related("category")

        category_param = self.request.query_params.get("category")
        if category_param == "none":
            queryset = queryset.filter(category__isnull=True)
        elif category_param:
            queryset = queryset.filter(category_id=category_param)

        completed_param = self.request.query_params.get("completed")
        if completed_param is not None:
            queryset = queryset.filter(completed=completed_param.lower() in ("true", "1"))

        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
