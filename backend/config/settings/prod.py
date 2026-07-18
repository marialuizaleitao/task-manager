"""Configurações específicas do ambiente de produção."""
from .base import *  # noqa: F401, F403

DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# A aplicação roda atrás do Nginx, que termina TLS e encaminha o protocolo
# original via X-Forwarded-Proto (ver docker/nginx/nginx.conf.template).
# Sem isso, o Django trata toda requisição como HTTP puro — mesmo as que
# chegaram em HTTPS — quebrando SECURE_SSL_REDIRECT (loop de redirect) e os
# cookies "Secure".
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS: instrui o navegador a nunca mais tentar HTTP neste domínio pelo
# tempo configurado. Começa em 1 ano sem preload — entrar na lista de
# preload dos navegadores é difícil de reverter, e só faz sentido depois do
# certificado estar estável em produção por um tempo.
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False

# Redundante com os headers que o Nginx já envia (docker/nginx/nginx.conf.template):
# defesa em profundidade, a aplicação não depende só da config externa do proxy.
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
