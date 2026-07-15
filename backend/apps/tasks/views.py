from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from apps.sharing.models import TaskShare
from apps.sharing.permissions import TaskAccessPermission
from apps.sharing.serializers import TaskShareSerializer

from .models import Task
from .serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    """CRUD de tarefas, incluindo gestão de compartilhamento.

    Tarefas próprias têm acesso irrestrito ao dono. Tarefas compartilhadas
    ficam visíveis para ações de detalhe (não para a listagem principal, que
    continua restrita às tarefas do próprio usuário) e a permissão exata de
    cada ação é resolvida por TaskAccessPermission.
    """

    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, TaskAccessPermission]

    def get_queryset(self):
        # select_related evita uma query extra por tarefa ao ler o id da
        # categoria e do dono relacionados na serialização.
        base = Task.objects.select_related("category", "owner")

        if self.action == "list":
            queryset = base.filter(owner=self.request.user)
        else:
            # Ações de detalhe (retrieve/update/destroy/shares/remove_share)
            # também precisam enxergar tarefas compartilhadas com o usuário,
            # para que TaskAccessPermission possa decidir o que é permitido.
            # O JOIN com shares duplica a linha da tarefa quando ela possui
            # múltiplos compartilhamentos (mesmo quando o filtro que casa é
            # "owner"), por isso o distinct().
            queryset = base.filter(
                Q(owner=self.request.user) | Q(shares__shared_with=self.request.user)
            ).distinct()

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

    @action(detail=True, methods=["get", "post"], url_path="shares")
    def shares(self, request, pk=None):
        task = self.get_object()

        if request.method == "POST":
            serializer = TaskShareSerializer(
                data=request.data, context={"task": task, "request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        task_shares = task.shares.select_related("shared_with")
        serializer = TaskShareSerializer(task_shares, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["delete"], url_path=r"shares/(?P<share_id>\d+)")
    def remove_share(self, request, pk=None, share_id=None):
        task = self.get_object()
        share = get_object_or_404(TaskShare, pk=share_id, task=task)
        share.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
