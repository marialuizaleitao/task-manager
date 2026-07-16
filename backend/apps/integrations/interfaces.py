"""Contratos que desacoplam apps/tasks dos provedores concretos de calendário."""
from typing import Protocol

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


class TaskNotificationProvider(Protocol):
    """Todo provedor de notificação de eventos de tarefa implementa este Protocol.

    Deliberadamente separado de CalendarEventProvider: um provedor de
    calendário espelha o *estado* de uma tarefa em um sistema externo
    (criar/atualizar/remover um evento correspondente); um provedor de
    notificação apenas informa um humano sobre um *evento* que já aconteceu
    (criação, conclusão, atraso). São contratos com formas diferentes — por
    exemplo, "tarefa vencida" não é uma ação de CRUD, então não faria sentido
    forçá-la em sync_update. Unificar as duas interfaces em uma só exigiria
    métodos vazios/irrelevantes em provedores que só cobrem um dos dois
    papéis (o Google Calendar não precisa notificar; o Telegram não precisa
    espelhar um evento de calendário).

    Assim como em CalendarEventProvider, cada provedor decide internamente
    se a notificação deve ou não ser enviada (ex.: sem due_date, sem
    conexão habilitada) e mantém seu próprio estado de entrega.
    """

    def is_connected(self, user) -> bool:
        """Indica se o provedor está conectado e habilitado para este usuário."""
        ...

    def notify_task_created(self, task: Task) -> None: ...

    def notify_task_completed(self, task: Task) -> None: ...

    def notify_task_overdue(self, task: Task) -> None: ...
