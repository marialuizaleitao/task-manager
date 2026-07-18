"""Ponto único de integração entre apps/tasks e provedores externos.

apps/tasks nunca importa google_calendar, telegram (ou qualquer outro
provedor) diretamente — chama apenas as funções deste módulo, que localizam
os provedores conectados via registry e delegam a cada um:

- sync_task(task, action): espelha o estado da tarefa em provedores de
  calendário (criar/atualizar/remover um evento correspondente).
- notify_task(task, event): avisa provedores de notificação sobre um evento
  do ciclo de vida da própria tarefa (criada, concluída, vencida).
- notify_task_shared(share) / notify_task_shared_updated(task, actor):
  avisam sobre eventos de compartilhamento — adicionados na Sprint 7.1.

Todas são atalhos que constroem um NotificationEvent e delegam a
apps.integrations.notifications.notify(), que faz o despacho best-effort de
fato (percorre os provedores conectados, isola a falha de cada um). Esses
atalhos existem porque apps/tasks e apps/sharing não deveriam precisar
conhecer a forma de um NotificationEvent para disparar um evento de tarefa —
só sync.py precisa saber que "task.created" é a key certa para uma tarefa
recém-criada. Um domínio futuro sem esse tipo de atalho (ex.: apps/accounts)
chamaria notifications.notify() diretamente.

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
    OVERDUE não tem um ponto de disparo automático ainda — não há
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


def notify_task_shared(share) -> None:
    """Notifica o usuário com quem uma tarefa acabou de ser compartilhada."""
    notifications.notify(
        NotificationEvent(
            key="task.shared",
            user=share.shared_with,
            subject=share.task,
            context={"permission": share.permission},
        )
    )


def notify_task_shared_updated(task, actor) -> None:
    """Notifica os usuários afetados por uma alteração em uma tarefa compartilhada.

    "Afetados" = dono da tarefa + todos com quem ela está compartilhada,
    exceto quem fez a própria alteração — evita notificar o autor sobre a
    própria ação, e o dict por id garante que cada afetado seja notificado
    uma única vez mesmo que apareça mais de uma vez na relação.
    """
    recipients = {task.owner_id: task.owner}
    for share in task.shares.select_related("shared_with"):
        recipients[share.shared_with_id] = share.shared_with
    recipients.pop(actor.id, None)

    for recipient in recipients.values():
        notifications.notify(
            NotificationEvent(
                key="task.shared_updated",
                user=recipient,
                subject=task,
                context={"actor": actor},
            )
        )
