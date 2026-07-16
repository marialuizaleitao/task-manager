"""Configurações específicas para execução da suíte de testes."""
from .base import *  # noqa: F401, F403

DEBUG = False
ALLOWED_HOSTS = ["*"]

# Hasher mais rápido para acelerar a criação de usuários nos testes.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Chave Fernet fixa para os testes (nunca usada fora deste ambiente) — sem
# ela, qualquer teste que salve GoogleCalendarCredential falharia ao cifrar
# os tokens.
GOOGLE_TOKEN_ENCRYPTION_KEY = "IS6Pk8SPwjgKvUaEM5hb0C0TAQx92R5AJqXI_u-tguE="
GOOGLE_OAUTH_CLIENT_ID = "test-client-id"
GOOGLE_OAUTH_CLIENT_SECRET = "test-client-secret"
GOOGLE_OAUTH_REDIRECT_URI = "http://localhost:8000/api/integrations/google-calendar/callback/"

# Token fixo para os testes (nunca usado fora deste ambiente) — sem ele,
# TelegramService.is_connected() sempre retornaria False e nenhum teste
# conseguiria exercitar o fluxo autenticado.
TELEGRAM_BOT_TOKEN = "test-telegram-bot-token"
