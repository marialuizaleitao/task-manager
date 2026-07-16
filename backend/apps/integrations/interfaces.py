"""Contratos que desacoplam apps/tasks (e outros domínios) dos provedores concretos."""
from dataclasses import dataclass, field
from typing import Any, Protocol

from apps.tasks.models import Task


class CalendarEventProvider(Protocol):
    """Todo provedor de sincronização de calendário implementa este Protocol.

    apps.integrations.sync depende apenas desta interface — nunca de uma
    implementação concreta como GoogleCalendarService — para que adicionar um
    novo provedor (ex.: Outlook Calendar) não exija alterar sync.py nem
    apps/tasks.

    Cada método recebe a Task e decide internamente o que fazer: criar,
    atualizar, remover ou ignorar (ex.: uma tarefa sem due_date não gera
    evento). O provedor também é responsável por seu próprio bookkeeping de
    vínculo tarefa/evento — sync.py não conhece esse detalhe.
    """

    def is_connected(self, user) -> bool:
        """Indica se o provedor está conectado e habilitado para este usuário."""
        ...

    def sync_create(self, task: Task) -> None: ...

    def sync_update(self, task: Task) -> None: ...

    def sync_delete(self, task: Task) -> None: ...


@dataclass
class NotificationEvent:
    """Evento de sistema despachado a um NotificationProvider.

    key identifica o tipo de evento por um namespace pontilhado (ex.:
    "task.created", "calendar.sync_failed") — a mesma convenção usada por
    todo evento desta sprint em diante, o que permite que domínios futuros
    (ex.: "auth.login", "sharing.revoked", "comments.created",
    "audit.suspicious_login") passem a notificar sem exigir qualquer mudança
    nesta classe ou no Protocol abaixo: só é preciso construir um
    NotificationEvent com a key certa e registrar um formatter no catálogo
    de mensagens do provedor (ex.: telegram/messages.py).

    user é sempre o destinatário direto da notificação — eventos com mais de
    um destinatário (ex.: "task.shared_updated", que avisa vários usuários
    afetados) são despachados como múltiplos NotificationEvent, um por
    destinatário, pelo chamador (ver apps.integrations.sync). Manter
    notify() de destinatário único evita que cada provedor precise
    implementar sua própria lógica de fan-out.

    subject carrega o objeto de domínio ao qual o evento se refere (hoje,
    sempre uma Task) — o provedor usa isso para formatar a mensagem, sem que
    NotificationProvider precise conhecer o domínio de cada evento.

    context carrega dados que não são derivados de subject sozinho (ex.:
    quem fez uma alteração, a permissão de um compartilhamento).
    """

    key: str
    user: Any
    subject: Any = None
    context: dict = field(default_factory=dict)


class NotificationProvider(Protocol):
    """Todo provedor de comunicação (Telegram, e futuramente Slack, e-mail,
    push...) implementa este Protocol.

    Um único método de despacho genérico (notify) em vez de um método por
    tipo de evento — a forma anterior, TaskNotificationProvider, com
    notify_task_created/notify_task_completed/notify_task_overdue. Aquela
    forma acoplava a interface ao domínio Task: cada novo tipo de evento
    (compartilhamento, sincronização de calendário, e no futuro autenticação,
    comentários, organizações, auditoria) exigiria um novo método no
    Protocol e em toda implementação, mesmo nas que não usam aquele evento.
    Um único notify(event) resolve isso: a interface pública nunca muda,
    apenas o catálogo de eventos que cada provedor sabe formatar.

    Deliberadamente separado de CalendarEventProvider pelos mesmos motivos
    de sempre: um provedor de calendário espelha o *estado* de uma tarefa em
    um sistema externo; um provedor de notificação informa um humano sobre
    um *evento* que já aconteceu em qualquer parte do sistema.
    """

    def is_connected(self, user) -> bool:
        """Indica se o provedor está conectado e habilitado para este usuário."""
        ...

    def notify(self, event: NotificationEvent) -> None: ...
