from rest_framework import permissions

from .models import TaskShare


class TaskAccessPermission(permissions.BasePermission):
    """Autorização de acesso a uma tarefa, considerando dono e compartilhamentos.

    O dono da tarefa tem acesso irrestrito. Um usuário com compartilhamento
    pode visualizar a tarefa (READ ou EDIT) ou editá-la (apenas EDIT), mas
    nunca pode excluí-la ou gerenciar seus compartilhamentos — essas ações
    permanecem exclusivas do dono.
    """

    OWNER_ONLY_ACTIONS = {"destroy", "shares", "remove_share"}
    EDITABLE_ACTIONS = {"update", "partial_update"}

    def has_object_permission(self, request, view, obj) -> bool:
        if obj.owner_id == request.user.id:
            return True

        if view.action in self.OWNER_ONLY_ACTIONS:
            return False

        share = TaskShare.objects.filter(task=obj, shared_with=request.user).first()
        if share is None:
            return False

        if view.action in self.EDITABLE_ACTIONS:
            return share.permission == TaskShare.Permission.EDIT

        return True
