"""Catálogo de mensagens do canal Telegram, por tipo de evento.

Centraliza toda formatação de texto em um único lugar, para que
TelegramService.notify() permaneça um simples "escolher o formatter certo e
enviar" — sem strings espalhadas nem condicionais repetidas por tipo de
evento. Um catálogo simples (dict de key -> função) é suficiente para o
volume de mensagens desta sprint; não há necessidade de um motor de
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
from apps.tasks.models import Task

_DATE_FORMAT = "%d/%m/%Y"


def _format_due_date(task: Task) -> str:
    return task.due_date.strftime(_DATE_FORMAT) if task.due_date else "Sem prazo"


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


_FORMATTERS = {
    "task.created": _task_created,
    "task.completed": _task_completed,
    "task.overdue": _task_overdue,
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
