"""Registro de provedores de integração disponíveis.

Dois registros independentes — um por tipo de contrato (ver interfaces.py):
calendário e notificação. Um dict simples é suficiente para cada um: todo
provedor se registra uma única vez, no ready() do próprio AppConfig (ver
google_calendar/apps.py e telegram/apps.py), e apps.integrations nunca
precisa importar um provedor concreto para saber que ele existe.

Dois dicts em vez de um único registro genérico porque as chaves podem se
sobrepor sem conflito (um provedor pode, no futuro, aparecer nos dois papéis)
e porque get_calendar_provider/get_notification_provider retornam tipos
diferentes — misturá-los em uma estrutura genérica exigiria um parâmetro de
"tipo de provedor" em cada chamada, sem ganho real com apenas dois papéis.
"""
from .interfaces import CalendarEventProvider, NotificationProvider

_calendar_providers: dict[str, type[CalendarEventProvider]] = {}
_notification_providers: dict[str, type[NotificationProvider]] = {}


def register_calendar_provider(key: str, provider_class: type[CalendarEventProvider]) -> None:
    _calendar_providers[key] = provider_class


def get_calendar_provider(key: str) -> CalendarEventProvider | None:
    provider_class = _calendar_providers.get(key)
    return provider_class() if provider_class else None


def registered_calendar_providers() -> list[str]:
    return list(_calendar_providers.keys())


def register_notification_provider(key: str, provider_class: type[NotificationProvider]) -> None:
    _notification_providers[key] = provider_class


def get_notification_provider(key: str) -> NotificationProvider | None:
    provider_class = _notification_providers.get(key)
    return provider_class() if provider_class else None


def registered_notification_providers() -> list[str]:
    return list(_notification_providers.keys())
