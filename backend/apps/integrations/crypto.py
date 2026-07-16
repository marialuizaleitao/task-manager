"""Infraestrutura reutilizável de criptografia para credenciais de integrações.

Qualquer provedor que precise armazenar um token de acesso em texto usa
EncryptedTextField em vez de TextField — a cifragem (Fernet) acontece na
borda do ORM, então o restante do código sempre lida com o valor em texto
plano, sem se preocupar com criptografia.
"""
from django.conf import settings
from django.db import models

from cryptography.fernet import Fernet, InvalidToken


def _fernet() -> Fernet:
    return Fernet(settings.GOOGLE_TOKEN_ENCRYPTION_KEY)


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ValueError(
            "Não foi possível decifrar o valor armazenado: chave de criptografia "
            "incorreta ou dado corrompido."
        ) from exc


class EncryptedTextField(models.TextField):
    """TextField que persiste o valor cifrado com Fernet no banco.

    A chave vem de GOOGLE_TOKEN_ENCRYPTION_KEY. O nome da variável é
    específico do Google apenas porque é a única integração desta sprint;
    nada neste campo é acoplado ao Google — um provedor futuro pode
    reutilizá-lo diretamente ou apontar para outra variável de ambiente.
    """

    def get_prep_value(self, value):
        if value in (None, ""):
            return value
        return encrypt(str(value))

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        return decrypt(value)
