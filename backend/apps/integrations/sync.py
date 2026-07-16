"""Ponto único de integração entre apps/tasks e provedores externos.

apps/tasks nunca importa google_calendar, telegram (ou qualquer outro
provedor) diretamente — chama apenas as funções deste módulo, que localizam
os provedores conectados via registry e delegam a cada um:

- sync_task(task, action): espelha o estado da tarefa em provedores de
  calendário (criar/atualizar/remover um evento correspondente).
- notify_task(task, event): avisa provedores de notificação sobre um evento
  do ciclo de vida da própria tarefa (criada, concluída, vencida).

notify_task constrói um NotificationEvent e delega a
apps.integrations.notifications.notify(), que faz o despacho best-effort de
fato (percorre os provedores conectados, isola a falha de cada um). Esse
atalho existe porque apps/tasks não deveria precisar conhecer a forma de um
NotificationEvent para disparar um evento de tarefa — só sync.py precisa
saber que "task.created" é a key certa para uma tarefa recém-criada.

sync_task continua best-effort e isolado por provedor aqui mesmo (não em
notifications.py), porque calendário e notificação são registries e
contratos diferentes (ver registry.py) — não faria sentido um módulo
genérico de notificação também orquestrar sincronização de calendário.
"""
import logging

from . import notifications
from .interfaces import NotificationEvent
from .registry import get_calendar_provider, registered_calendar_providers

logger = logging.getLogger(__name__)

CREATE = "create"
UPDATE = "update"
DELETE = "delete"


def sync_task(task, action: str) -> None:
    for provider_key in registered_calendar_providers():
        provider = get_calendar_provider(provider_key)
        try:
            if not provider.is_connected(task.owner):
                continue

            if action == CREATE:
                provider.sync_create(task)
            elif action == UPDATE:
                provider.sync_update(task)
            elif action == DELETE:
                provider.sync_delete(task)
            else:
                raise ValueError(f"Ação de sincronização desconhecida: {action!r}")
        except Exception:
            # Best-effort por design: uma falha de sincronização nunca pode
            # comprometer a resposta da API de tarefas. O provedor já
            # registrou o próprio status/last_error antes de propagar aqui;
            # este log serve à observabilidade, não ao usuário.
            logger.exception(
                "Falha ao sincronizar tarefa %s com o provedor %s (ação=%s)",
                task.id,
                provider_key,
                action,
            )


class TaskEvent:
    """Eventos do ciclo de vida de uma tarefa que podem disparar uma notificação.

    CREATED e COMPLETED são disparados por apps/tasks a partir de uma
    transição real de estado (TaskViewSet.perform_create/perform_update).
    OVERDUE não tem um ponto de disparo automático nesta sprint — não há
    scheduler (ver README, "Performance") — mas o provedor e a função de
    despacho já suportam o evento, prontos para serem chamados por uma
    tarefa periódica futura (Celery Beat) sem qualquer mudança de código.
    """

    CREATED = "created"
    COMPLETED = "completed"
    OVERDUE = "overdue"


def notify_task(task, event: str) -> None:
    if event not in (TaskEvent.CREATED, TaskEvent.COMPLETED, TaskEvent.OVERDUE):
        raise ValueError(f"Evento de notificação desconhecido: {event!r}")

    notifications.notify(NotificationEvent(key=f"task.{event}", user=task.owner, subject=task))
