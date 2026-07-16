"""Cliente HTTP para os endpoints de eventos da Google Calendar API v3.

Cliente próprio via httpx, consumindo a REST API diretamente — não o SDK
oficial (google-api-python-client). Justificativa (ver README): o SDK usa
discovery dinâmico de schema em runtime e pouca tipagem, o que tornaria o
fluxo OAuth2 menos explícito; um cliente próprio mantém uma única
dependência HTTP no projeto (httpx, já usada em todo o backend) e reaproveita
o mesmo padrão de tratamento de erro das demais camadas.
"""
from __future__ import annotations

from datetime import timedelta

import httpx
from django.conf import settings

from apps.integrations.exceptions import AuthenticationExpiredError, ExternalServiceError
from apps.tasks.models import Task

CALENDAR_API_BASE_URL = "https://www.googleapis.com/calendar/v3"


def _task_to_event_body(task: Task) -> dict:
    """Converte a Task em um evento de dia inteiro.

    O Google trata o fim de eventos de dia inteiro como exclusivo: um evento
    de um único dia tem end.date = start.date + 1 dia.
    """
    end_date = task.due_date + timedelta(days=1)
    return {
        "summary": task.title,
        "description": task.description,
        "start": {"date": task.due_date.isoformat()},
        "end": {"date": end_date.isoformat()},
    }


class GoogleCalendarClient:
    """Cliente síncrono para criar/atualizar/remover eventos de um calendário.

    Recebe um access_token já válido — renovar o token é responsabilidade da
    camada de serviço, não deste cliente.
    """

    def __init__(self, access_token: str, calendar_id: str = "primary") -> None:
        self._calendar_id = calendar_id
        self._client = httpx.Client(
            base_url=CALENDAR_API_BASE_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=settings.GOOGLE_API_TIMEOUT_SECONDS,
            # Retries do transporte cobrem apenas falhas de conexão (DNS,
            # timeout de conexão) — não substituem o backoff de quota
            # documentado pelo Google para 429/5xx, que fica fora do escopo
            # desta sprint por exigir uma fila (ver README, "Limitações").
            transport=httpx.HTTPTransport(retries=settings.GOOGLE_API_MAX_RETRIES),
        )

    def __enter__(self) -> "GoogleCalendarClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self._client.close()

    def create_event(self, task: Task) -> str:
        data = self._request("POST", f"/calendars/{self._calendar_id}/events", json=_task_to_event_body(task))
        return data["id"]

    def update_event(self, task: Task, event_id: str) -> str:
        data = self._request(
            "PATCH",
            f"/calendars/{self._calendar_id}/events/{event_id}",
            json=_task_to_event_body(task),
        )
        return data["id"]

    def delete_event(self, event_id: str) -> None:
        self._request("DELETE", f"/calendars/{self._calendar_id}/events/{event_id}", expect_empty=True)

    def _request(self, method: str, path: str, *, json: dict | None = None, expect_empty: bool = False):
        try:
            response = self._client.request(method, path, json=json)
        except httpx.TimeoutException as exc:
            raise ExternalServiceError(f"Timeout ao chamar a Google Calendar API ({method} {path}).") from exc
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"Falha de rede ao chamar a Google Calendar API ({method} {path}).") from exc

        if response.status_code == 401:
            raise AuthenticationExpiredError("Access token rejeitado pela Google Calendar API (401).")

        if response.is_error:
            raise ExternalServiceError(
                f"Google Calendar API retornou {response.status_code} em {method} {path}.",
                status_code=response.status_code,
            )

        if expect_empty:
            return None

        try:
            return response.json()
        except ValueError as exc:
            raise ExternalServiceError(
                "Google Calendar API retornou uma resposta inválida (corpo não é JSON)."
            ) from exc
