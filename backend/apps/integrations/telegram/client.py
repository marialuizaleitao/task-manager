"""Cliente HTTP para a Telegram Bot API.

Cliente próprio via httpx, consumindo a API HTTP oficial diretamente — sem
SDK (ver README, "Comunicação"). Mesma justificativa arquitetural do
GoogleCalendarClient: o projeto já padronizou httpx como cliente HTTP em
todas as integrações, e a Bot API do Telegram é simples o bastante (JSON
puro, sem discovery de schema) para não precisar de um SDK.
"""
from __future__ import annotations

import httpx
from django.conf import settings

from apps.integrations.exceptions import AuthenticationExpiredError, ExternalServiceError

TELEGRAM_API_BASE_URL = "https://api.telegram.org"

# Descrições que o Telegram usa para indicar que uma mensagem não pode mais
# ser entregue a este chat_id — nem com um bot token válido. Checadas via
# substring porque a Bot API não expõe um código de erro estável para essa
# distinção (ambas costumam vir com error_code 403, mas "chat not found"
# também pode aparecer com 400).
_UNREACHABLE_MARKERS = ("blocked", "chat not found", "user is deactivated", "kicked")


class ChatUnreachableError(ExternalServiceError):
    """O chat_id não aceita mais mensagens deste bot (bloqueado, removido, inexistente).

    Distinto de ExternalServiceError genérico porque TelegramService reage
    de forma específica a este caso: desabilita a conexão automaticamente
    (ver service.py), em vez de apenas registrar uma falha passageira.
    """


class TelegramClient:
    """Cliente síncrono para os três métodos da Bot API usados nesta sprint.

    Responsável exclusivamente pela chamada HTTP e pela tradução de erros —
    nenhuma regra de negócio (localizar chat_id, decidir o que enviar) vive
    aqui; isso é responsabilidade de TelegramService.
    """

    def __init__(self, bot_token: str) -> None:
        self._client = httpx.Client(
            base_url=f"{TELEGRAM_API_BASE_URL}/bot{bot_token}",
            timeout=settings.TELEGRAM_API_TIMEOUT_SECONDS,
            transport=httpx.HTTPTransport(retries=settings.TELEGRAM_API_MAX_RETRIES),
        )

    def __enter__(self) -> "TelegramClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self._client.close()

    def get_me(self) -> dict:
        """Valida o token e retorna os dados do bot (usado para montar o deep link)."""
        return self._request("GET", "/getMe")

    def send_message(self, chat_id: str, text: str) -> dict:
        return self._request("POST", "/sendMessage", json={"chat_id": chat_id, "text": text})

    def get_updates(self, offset: int | None = None) -> list[dict]:
        """Busca atualizações pendentes (mensagens recebidas pelo bot).

        timeout=0 (long polling desligado) é essencial aqui: este método é
        chamado de forma síncrona dentro de uma requisição HTTP comum
        (POST /telegram/confirm/), nunca por um worker em segundo plano. Um
        long poll do Telegram (que pode ficar até ~50s aguardando) bloquearia
        a thread do servidor web pelo mesmo tempo — inaceitável no ciclo
        request/response. Ver README, "Performance", para a discussão
        completa de polling vs. webhook.
        """
        params: dict = {"timeout": 0}
        if offset is not None:
            params["offset"] = offset
        return self._request("GET", "/getUpdates", params=params)

    def _request(self, method: str, path: str, *, json: dict | None = None, params: dict | None = None):
        try:
            response = self._client.request(method, path, json=json, params=params)
        except httpx.TimeoutException as exc:
            raise ExternalServiceError(f"Timeout ao chamar a Telegram Bot API ({method} {path}).") from exc
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"Falha de rede ao chamar a Telegram Bot API ({method} {path}).") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise ExternalServiceError(
                "Telegram Bot API retornou uma resposta inválida (corpo não é JSON)."
            ) from exc

        if data.get("ok"):
            return data["result"]

        description = data.get("description", "")
        error_code = data.get("error_code", response.status_code)

        if error_code == 401:
            raise AuthenticationExpiredError(
                "Bot token rejeitado pela Telegram Bot API — verifique TELEGRAM_BOT_TOKEN."
            )

        if any(marker in description.lower() for marker in _UNREACHABLE_MARKERS):
            raise ChatUnreachableError(description or "Chat inalcançável.", status_code=error_code)

        raise ExternalServiceError(
            f"Telegram Bot API retornou erro em {method} {path}: {description}",
            status_code=error_code,
        )
