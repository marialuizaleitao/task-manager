"""Fluxo OAuth2 Authorization Code ("Web Server Flow") do Google.

Endpoints e comportamento documentados em
https://developers.google.com/identity/protocols/oauth2/web-server.

access_type=offline + prompt=consent garantem que o Google emita um
refresh_token a cada autorização completa — sem prompt=consent, um usuário
que já autorizou o app antes pode receber apenas um novo access_token.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
from django.conf import settings
from django.core import signing
from django.utils import timezone

from apps.integrations.exceptions import AuthenticationExpiredError, ExternalServiceError

AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"

# Escopo mínimo necessário para criar/editar/remover eventos — não o acesso
# completo à conta de calendários (.../auth/calendar), seguindo o princípio
# do menor privilégio.
SCOPE = "https://www.googleapis.com/auth/calendar.events"

_STATE_SALT = "google_calendar_oauth_state"
_STATE_MAX_AGE_SECONDS = 600


@dataclass(frozen=True)
class TokenResponse:
    access_token: str
    refresh_token: str
    expires_at: datetime


def build_authorization_url(user_id: int) -> str:
    """Monta a URL de consentimento do Google, com o usuário identificado via `state`.

    O redirect de volta (callback) é uma navegação de navegador comum, sem
    Authorization: Bearer — por isso o usuário precisa ser identificado por
    um valor assinado (django.core.signing) embutido em `state`, em vez de
    um JWT ou de uma tabela de sessões de OAuth em andamento.
    """
    state = signing.dumps({"user_id": user_id}, salt=_STATE_SALT)
    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    query = httpx.QueryParams(params)
    return f"{AUTHORIZATION_ENDPOINT}?{query}"


def resolve_user_id_from_state(state: str) -> int:
    try:
        data = signing.loads(state, salt=_STATE_SALT, max_age=_STATE_MAX_AGE_SECONDS)
    except signing.BadSignature as exc:
        raise AuthenticationExpiredError("Parâmetro state inválido ou expirado.") from exc
    return data["user_id"]


def exchange_code_for_tokens(code: str) -> TokenResponse:
    payload = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
    }
    data = _post_token_request(payload)

    if "refresh_token" not in data:
        # Só ocorre se o Google decidir não reemitir o refresh_token (raro
        # com prompt=consent). Sem ele não há como renovar o access_token
        # depois, então tratamos como se a autorização não tivesse valor.
        raise AuthenticationExpiredError(
            "Google não retornou refresh_token; revogue o acesso na conta "
            "Google e conecte novamente."
        )

    return TokenResponse(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_at=timezone.now() + timedelta(seconds=data["expires_in"]),
    )


def refresh_access_token(refresh_token: str) -> TokenResponse:
    payload = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    data = _post_token_request(payload)
    return TokenResponse(
        access_token=data["access_token"],
        # A resposta de refresh normalmente não repete o refresh_token: o
        # mesmo token continua válido até ser revogado.
        refresh_token=data.get("refresh_token", refresh_token),
        expires_at=timezone.now() + timedelta(seconds=data["expires_in"]),
    )


def revoke_token(token: str) -> None:
    """Revoga um token junto ao Google. Best-effort: usado no fluxo de desconexão,
    onde a credencial local já será apagada independentemente do resultado.
    """
    try:
        httpx.post(REVOKE_ENDPOINT, params={"token": token}, timeout=settings.GOOGLE_API_TIMEOUT_SECONDS)
    except httpx.HTTPError:
        pass


def _post_token_request(payload: dict) -> dict:
    try:
        response = httpx.post(TOKEN_ENDPOINT, data=payload, timeout=settings.GOOGLE_API_TIMEOUT_SECONDS)
    except httpx.TimeoutException as exc:
        raise ExternalServiceError("Timeout ao comunicar com o Google (token endpoint).") from exc
    except httpx.HTTPError as exc:
        raise ExternalServiceError("Falha de rede ao comunicar com o Google (token endpoint).") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise ExternalServiceError(
            "Google retornou uma resposta inválida (corpo não é JSON).",
            status_code=response.status_code,
        ) from exc

    if response.status_code == 400 and data.get("error") == "invalid_grant":
        raise AuthenticationExpiredError("Google recusou as credenciais (invalid_grant).")

    if response.is_error:
        raise ExternalServiceError(
            f"Google retornou {response.status_code} ao comunicar com o token endpoint.",
            status_code=response.status_code,
        )

    return data
