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
