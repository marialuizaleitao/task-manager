"""Configurações específicas para execução da suíte de testes."""
from .base import *  # noqa: F401, F403

DEBUG = False
ALLOWED_HOSTS = ["*"]

# Hasher mais rápido para acelerar a criação de usuários nos testes.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
