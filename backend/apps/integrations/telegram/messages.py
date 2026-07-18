"""Catálogo de mensagens do canal Telegram, por tipo de evento.

Centraliza toda formatação de texto em um único lugar, para que
TelegramService.notify() permaneça um simples "escolher o formatter certo e
enviar" — sem strings espalhadas nem condicionais repetidas por tipo de
evento. Um catálogo simples (dict de key -> função) é suficiente para o
volume de mensagens do projeto; não há necessidade de um motor de
templates (ex.: Django templates, Jinja) para textos curtos e sem lógica de
apresentação além de formatação de data e pluralização trivial.

Escopo deliberadamente Telegram: cada provedor futuro (Slack, e-mail...)
teria seu próprio catálogo, já que o formato de mensagem ideal difere por
canal (texto simples aqui; blocks estruturados no Slack; HTML em e-mail).
Não há um `communication/templates.py` compartilhado entre provedores
porque hoje só existe um provedor — criar essa camada agora seria
generalizar sem um segundo caso de uso real para validar a abstração.
"""
from __future__ import annotations

from apps.integrations.interfaces import NotificationEvent
from apps.sharing.models import TaskShare
from apps.tasks.models import Task

_DATE_FORMAT = "%d/%m/%Y"


def _format_due_date(task: Task) -> str:
    return task.due_date.strftime(_DATE_FORMAT) if task.due_date else "Sem prazo"


def _display_name(user) -> str:
    return user.first_name or user.email


def _task_created(event: NotificationEvent) -> str:
    task = event.subject
    lines = ["🆕 Nova tarefa", "", "Título:", task.title, "", "Prazo:", _format_due_date(task)]
    if task.category:
        lines += ["", "Categoria:", task.category.name]
    return "\n".join(lines)


def _task_completed(event: NotificationEvent) -> str:
    return f"✅ Tarefa concluída\n\nTítulo:\n{event.subject.title}"


def _task_overdue(event: NotificationEvent) -> str:
    task = event.subject
    lines = ["⚠️ Tarefa vencida", "", "Título:", task.title, "", "Prazo:", _format_due_date(task)]
    return "\n".join(lines)


def _task_shared(event: NotificationEvent) -> str:
    task = event.subject
    permission_label = TaskShare.Permission(event.context["permission"]).label
    lines = [
        "🔗 Uma tarefa foi compartilhada com você.",
        "",
        "Título:",
        task.title,
        "",
        "Permissão:",
        permission_label,
    ]
    return "\n".join(lines)


def _task_shared_updated(event: NotificationEvent) -> str:
    task = event.subject
    actor = event.context["actor"]
    lines = [
        "🔄 Uma tarefa compartilhada foi atualizada.",
        "",
        "Alterado por:",
        _display_name(actor),
        "",
        "Novo prazo:",
        _format_due_date(task),
        "",
        "Status:",
        "Concluída" if task.completed else "Pendente",
    ]
    return "\n".join(lines)


def _calendar_sync_succeeded(event: NotificationEvent) -> str:
    task = event.subject
    lines = [
        "Google Calendar",
        "",
        "Sua tarefa foi sincronizada.",
        "Evento criado com sucesso.",
        "",
        "Título:",
        task.title,
    ]
    return "\n".join(lines)


def _calendar_sync_failed(event: NotificationEvent) -> str:
    task = event.subject
    lines = [
        "Google Calendar",
        "",
        "Não foi possível sincronizar sua tarefa.",
        "Sua tarefa continua salva normalmente.",
        "",
        "Título:",
        task.title,
    ]
    return "\n".join(lines)


_FORMATTERS = {
    "task.created": _task_created,
    "task.completed": _task_completed,
    "task.overdue": _task_overdue,
    "task.shared": _task_shared,
    "task.shared_updated": _task_shared_updated,
    "calendar.sync_succeeded": _calendar_sync_succeeded,
    "calendar.sync_failed": _calendar_sync_failed,
}


def format_message(event: NotificationEvent) -> str | None:
    """Formata o texto de um evento, ou None se não houver um evento conhecido.

    Retornar None (em vez de levantar exceção) para uma key desconhecida é
    proposital: um evento futuro sem formatter Telegram ainda registrado não
    deve derrubar o despacho best-effort em notifications.py — apenas essa
    notificação específica é silenciosamente ignorada.
    """
    formatter = _FORMATTERS.get(event.key)
    return formatter(event) if formatter else None
