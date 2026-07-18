"""Configurações específicas do ambiente de desenvolvimento."""
from .base import *  # noqa: F401, F403

DEBUG = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
