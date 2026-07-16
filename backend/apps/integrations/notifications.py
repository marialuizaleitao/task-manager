"""Despacho genérico de eventos de notificação a provedores registrados.

Ponto de entrada para qualquer domínio do sistema que precise avisar um
usuário através de um canal de comunicação externo — não apenas apps/tasks.
apps/tasks continua usando os atalhos de sync.py (notify_task,
notify_task_shared, notify_task_shared_updated), que constroem o
NotificationEvent certo e delegam para notify() aqui; um futuro domínio
(ex.: apps/accounts avisando sobre um novo login) chamaria notify()
diretamente, sem precisar de nada específico de Task.

Mesmo contrato best-effort do restante do módulo de integrações: nunca
lança exceção, isola a falha de um provedor dos demais. NotificationEvent
já persistiu o que precisava antes de chegar aqui (ex.: a Task já foi
salva), então nenhuma falha de notificação pode se propagar para quem
disparou o evento.
"""
import logging

from .interfaces import NotificationEvent
from .registry import get_notification_provider, registered_notification_providers

logger = logging.getLogger(__name__)


def notify(event: NotificationEvent) -> None:
    for provider_key in registered_notification_providers():
        provider = get_notification_provider(provider_key)
        try:
            if not provider.is_connected(event.user):
                continue
            provider.notify(event)
        except Exception:
            logger.exception(
                "Falha ao despachar evento %s para o provedor %s (subject_id=%s)",
                event.key,
                provider_key,
                getattr(event.subject, "id", None),
            )
