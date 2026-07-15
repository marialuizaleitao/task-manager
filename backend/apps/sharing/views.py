from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions

from apps.tasks.filters import TASK_ORDERING_FIELDS, TASK_SEARCH_FIELDS, TaskFilterSet
from apps.tasks.models import Task

from .models import TaskShare
from .serializers import SharedTaskSerializer


class SharedTaskListView(generics.ListAPIView):
    """Lista as tarefas que outros usuários compartilharam com o usuário autenticado.

    Reaproveita o mesmo FilterSet, busca e ordenação de TaskViewSet, para que
    "minhas tarefas" e "compartilhadas comigo" se comportem de forma idêntica
    em vez de duplicar essa lógica em dois lugares.
    """

    serializer_class = SharedTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TaskFilterSet
    search_fields = TASK_SEARCH_FIELDS
    ordering_fields = TASK_ORDERING_FIELDS
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        return (
            Task.objects.filter(shares__shared_with=user)
            .select_related("category", "owner")
            .prefetch_related(
                Prefetch(
                    "shares",
                    queryset=TaskShare.objects.filter(shared_with=user),
                    to_attr="my_shares",
                )
            )
        )
