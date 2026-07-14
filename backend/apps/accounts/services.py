"""Regras de negócio da app accounts, fora das views e dos serializers."""
from django.contrib.auth import get_user_model

User = get_user_model()


def register_user(data: dict) -> User:
    """Cria um novo usuário a partir de dados já validados pelo serializer."""
    return User.objects.create_user(
        email=data["email"],
        password=data["password"],
        first_name=data.get("first_name", ""),
        last_name=data.get("last_name", ""),
    )
