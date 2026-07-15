from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.tasks.models import Task
from apps.tasks.serializers import TaskSerializer

from .models import TaskShare

User = get_user_model()


class TaskShareSerializer(serializers.ModelSerializer):
    """Representa um compartilhamento de tarefa.

    A entrada identifica o destinatário por e-mail (não por id), por ser o
    identificador que o dono da tarefa realmente conhece do outro usuário.
    """

    shared_with = UserSerializer(read_only=True)
    email = serializers.EmailField(write_only=True)
    permission = serializers.ChoiceField(choices=TaskShare.Permission.choices)

    class Meta:
        model = TaskShare
        fields = ["id", "shared_with", "email", "permission", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_email(self, value: str) -> str:
        request = self.context["request"]
        task = self.context["task"]

        try:
            target_user = User.objects.get(email__iexact=value)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError(
                "Não existe usuário cadastrado com este e-mail."
            ) from exc

        if target_user.id == request.user.id:
            raise serializers.ValidationError(
                "Você não pode compartilhar uma tarefa com você mesmo."
            )

        if TaskShare.objects.filter(task=task, shared_with=target_user).exists():
            raise serializers.ValidationError(
                "Esta tarefa já está compartilhada com este usuário."
            )

        self._target_user = target_user
        return value

    def create(self, validated_data: dict) -> TaskShare:
        validated_data.pop("email")
        return TaskShare.objects.create(
            task=self.context["task"],
            shared_with=self._target_user,
            permission=validated_data["permission"],
        )


class SharedTaskSerializer(TaskSerializer):
    """Serializa uma tarefa sob a ótica de quem a recebeu por compartilhamento.

    Estende TaskSerializer com o dono da tarefa e o nível de permissão do
    usuário autenticado, para que o frontend saiba o que pode fazer com ela.
    """

    owner = UserSerializer(read_only=True)
    permission = serializers.SerializerMethodField()

    class Meta(TaskSerializer.Meta):
        model = Task
        fields = [*TaskSerializer.Meta.fields, "owner", "permission"]

    def get_permission(self, obj: Task) -> str:
        # my_shares é populado via Prefetch em SharedTaskListView.get_queryset,
        # já filtrado para o usuário autenticado — evita uma query por tarefa.
        my_shares = getattr(obj, "my_shares", None)
        if my_shares:
            return my_shares[0].permission
        return ""
