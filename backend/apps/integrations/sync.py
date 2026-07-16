"""Ponto único de integração entre apps/tasks e provedores externos.

apps/tasks nunca importa google_calendar, telegram (ou qualquer outro
provedor) diretamente — chama apenas as duas funções deste módulo, que
localizam os provedores conectados via registry e delegam a cada um:

- sync_task(task, action): espelha o estado da tarefa em provedores de
  calendário (criar/atualizar/remover um evento correspondente).
- notify_task(task, event): avisa provedores de notificação sobre um
  evento que já aconteceu com a tarefa (criada, concluída, vencida).

Ambas são best-effort: TaskViewSet já persistiu a tarefa antes de chamar
qualquer uma delas, então nenhuma falha aqui pode se propagar para o
cliente da API. Cada provedor registra seu próprio estado de entrega;
estas funções apenas garantem isolamento entre provedores (a falha de um
nunca impede os demais) e logam o que aconteceu, sem nunca lançar exceção.
"""
import logging

from .registry import (
    get_calendar_provider,
    get_notification_provider,
    registered_calendar_providers,
    registered_notification_providers,
)

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
    """Eventos de tarefa que podem disparar uma notificação.

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
    for provider_key in registered_notification_providers():
        provider = get_notification_provider(provider_key)
        try:
            if not provider.is_connected(task.owner):
                continue

            if event == TaskEvent.CREATED:
                provider.notify_task_created(task)
            elif event == TaskEvent.COMPLETED:
                provider.notify_task_completed(task)
            elif event == TaskEvent.OVERDUE:
                provider.notify_task_overdue(task)
            else:
                raise ValueError(f"Evento de notificação desconhecido: {event!r}")
        except Exception:
            # Mesmo contrato best-effort de sync_task: notificar (ou falhar
            # ao notificar) nunca pode comprometer a resposta da API.
            logger.exception(
                "Falha ao notificar tarefa %s via provedor %s (evento=%s)",
                task.id,
                provider_key,
                event,
            )
