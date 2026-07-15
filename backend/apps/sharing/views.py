from django.db.models import Prefetch
from rest_framework import generics, permissions

from apps.tasks.models import Task

from .models import TaskShare
from .serializers import SharedTaskSerializer


class SharedTaskListView(generics.ListAPIView):
    """Lista as tarefas que outros usuários compartilharam com o usuário autenticado."""

    serializer_class = SharedTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

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
            .order_by("-created_at")
        )
