"""Registro de provedores de calendário disponíveis.

Um dict simples é suficiente: cada provedor se registra uma única vez, no
ready() do próprio AppConfig (ver google_calendar/apps.py), e apps.integrations
nunca precisa importar um provedor concreto para saber que ele existe.
"""
from .interfaces import CalendarEventProvider

_calendar_providers: dict[str, type[CalendarEventProvider]] = {}


def register_calendar_provider(key: str, provider_class: type[CalendarEventProvider]) -> None:
    _calendar_providers[key] = provider_class


def get_calendar_provider(key: str) -> CalendarEventProvider | None:
    provider_class = _calendar_providers.get(key)
    return provider_class() if provider_class else None


def registered_calendar_providers() -> list[str]:
    return list(_calendar_providers.keys())
