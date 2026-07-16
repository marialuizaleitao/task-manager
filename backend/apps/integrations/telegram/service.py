"""Implementação de TaskNotificationProvider (apps.integrations.interfaces) para o Telegram.

TelegramService concentra: localizar o chat_id do usuário, validar se a
integração está configurada e habilitada, formatar e enviar mensagens, e
manter o estado da conexão (last_contact_at, desabilitação automática ao
detectar que o bot foi bloqueado). Registrado no registry por
TelegramConfig.ready() — apps.integrations.sync chama estes métodos apenas
através da interface, nunca importando esta classe diretamente.

DailySummaryService vive neste mesmo arquivo (não em um módulo próprio):
é outro consumidor de TelegramService, sem estado ou contrato de Protocol
próprio, então um novo arquivo só para ele não teria uma responsabilidade
distinta o bastante para justificar a divisão (ver CLAUDE.md, "antes de
criar um novo arquivo, verifique se a responsabilidade pode ser atendida
por um arquivo existente").
"""
from __future__ import annotations

import secrets

from django.conf import settings
from django.utils import timezone

from apps.integrations.exceptions import ProviderNotConfiguredError
from apps.tasks.models import Task

from .client import ChatUnreachableError, TelegramClient
from .models import TelegramConnection


class TelegramService:
    def is_connected(self, user) -> bool:
        if not settings.TELEGRAM_BOT_TOKEN:
            return False
        connection = self._get_connection(user)
        return connection is not None and connection.is_linked() and connection.enabled

    def notify_task_created(self, task: Task) -> None:
        if task.due_date is None:
            return
        self.send_text(task.owner, _format_task_created_message(task))

    def notify_task_completed(self, task: Task) -> None:
        self.send_text(task.owner, _format_task_completed_message(task))

    def notify_task_overdue(self, task: Task) -> None:
        self.send_text(task.owner, _format_task_overdue_message(task))

    def send_text(self, user, text: str) -> None:
        """Envia uma mensagem de texto livre ao usuário, se conectado.

        Público (diferente de notify_task_*, que só existem para satisfazer
        o Protocol TaskNotificationProvider) porque também é usado por
        DailySummaryService, que monta sua própria mensagem a partir de uma
        consulta que não é um evento de ciclo de vida de uma única tarefa.
        """
        connection = self._require_connection(user)
        with TelegramClient(settings.TELEGRAM_BOT_TOKEN) as client:
            try:
                client.send_message(connection.telegram_chat_id, text)
            except ChatUnreachableError:
                # O chat não aceita mais mensagens deste bot (bloqueado,
                # removido, conta desativada). Desabilitar em vez de apagar
                # preserva o histórico (username, chat_id) para quando o
                # usuário reconectar, sem exigir o fluxo de vinculação de
                # novo se ele apenas desbloquear o bot e reenviar /start.
                connection.enabled = False
                connection.save(update_fields=["enabled", "updated_at"])
                raise

        connection.last_contact_at = timezone.now()
        connection.save(update_fields=["last_contact_at", "updated_at"])

    # -- vinculação -----------------------------------------------------

    def start_linking(self, user) -> dict:
        """Gera um código de vinculação e o deep link para iniciar a conversa no bot.

        Um bot não pode iniciar contato com um usuário — só pode responder
        depois que o próprio usuário envia a primeira mensagem (restrição
        da própria Bot API, pensada contra spam). Por isso não existe um
        jeito de "informar seu @username e pronto": o backend gera um
        linking_code de uso único, o usuário abre o deep link
        (https://t.me/<bot>?start=<code>), o Telegram entrega isso como a
        mensagem "/start <code>" para o bot, e confirm_linking() localiza
        essa mensagem via getUpdates().
        """
        self._require_bot_token()

        connection, _ = TelegramConnection.objects.get_or_create(owner=user)
        connection.linking_code = secrets.token_urlsafe(9)
        connection.save(update_fields=["linking_code", "updated_at"])

        with TelegramClient(settings.TELEGRAM_BOT_TOKEN) as client:
            bot = client.get_me()

        bot_username = bot["username"]
        return {
            "deep_link": f"https://t.me/{bot_username}?start={connection.linking_code}",
            "bot_username": bot_username,
        }

    def confirm_linking(self, user) -> TelegramConnection:
        """Verifica se o usuário já enviou /start ao bot e finaliza a vinculação.

        Não usa offset persistente entre chamadas — é um débito técnico
        conhecido e documentado (ver README, "Limitações"): cada chamada
        busca as atualizações recentes (a Bot API mantém até 100 ou ~24h) e
        filtra pelo linking_code, único por vinculação pendente, então
        reprocessar atualizações antigas é seguro (idempotente), apenas
        um pouco menos eficiente do que confirmar o offset a cada chamada.
        """
        self._require_bot_token()

        connection = TelegramConnection.objects.filter(owner=user).first()
        if connection is None or not connection.linking_code:
            raise ProviderNotConfiguredError(
                "Nenhuma vinculação pendente. Inicie a conexão novamente."
            )

        with TelegramClient(settings.TELEGRAM_BOT_TOKEN) as client:
            updates = client.get_updates()

        expected_text = f"/start {connection.linking_code}"
        match = next(
            (
                update
                for update in updates
                if update.get("message", {}).get("text") == expected_text
            ),
            None,
        )
        if match is None:
            return connection

        chat = match["message"]["chat"]
        connection.telegram_chat_id = str(chat["id"])
        connection.telegram_username = chat.get("username", "")
        connection.linking_code = None
        connection.enabled = True
        connection.last_contact_at = timezone.now()
        connection.save()
        return connection

    def set_enabled(self, user, enabled: bool) -> TelegramConnection:
        connection = TelegramConnection.objects.filter(owner=user).first()
        if connection is None:
            raise ProviderNotConfiguredError("Usuário não conectou o Telegram.")
        connection.enabled = enabled
        connection.save(update_fields=["enabled", "updated_at"])
        return connection

    def disconnect(self, user) -> None:
        TelegramConnection.objects.filter(owner=user).delete()

    # -- internos ---------------------------------------------------------

    def _get_connection(self, user) -> TelegramConnection | None:
        return TelegramConnection.objects.filter(owner=user).first()

    def _require_connection(self, user) -> TelegramConnection:
        self._require_bot_token()
        connection = self._get_connection(user)
        if connection is None or not connection.is_linked() or not connection.enabled:
            raise ProviderNotConfiguredError("Usuário não conectou o Telegram.")
        return connection

    def _require_bot_token(self) -> None:
        if not settings.TELEGRAM_BOT_TOKEN:
            raise ProviderNotConfiguredError("TELEGRAM_BOT_TOKEN não configurado.")


class DailySummaryService:
    """Monta e envia o resumo diário de tarefas de um usuário.

    Nesta sprint, send_summary() não é chamado por nenhum fluxo automático
    — não há scheduler (ver README, "Performance"). O serviço existe pronto
    para ser invocado por usuário a partir de uma tarefa periódica futura
    (Celery Beat). build_message() é mantido independente de send_summary()
    para ser testável sem mockar HTTP.
    """

    def __init__(self, telegram_service: TelegramService | None = None) -> None:
        self._telegram_service = telegram_service or TelegramService()

    def build_message(self, user) -> str:
        today = timezone.localdate()
        due_today = list(
            Task.objects.filter(owner=user, due_date=today, completed=False).order_by("title")
        )
        overdue_count = Task.objects.filter(
            owner=user, due_date__lt=today, completed=False
        ).count()

        if not due_today and not overdue_count:
            return "📋 Resumo do dia\n\nNenhuma tarefa pendente para hoje."

        lines = ["📋 Resumo do dia"]

        if due_today:
            lines.append("")
            lines.append(f"Tarefas de hoje ({len(due_today)}):")
            lines.extend(f"- {task.title}" for task in due_today)

        if overdue_count:
            lines.append("")
            lines.append(f"Tarefas vencidas: {overdue_count}")

        return "\n".join(lines)

    def send_summary(self, user) -> None:
        self._telegram_service.send_text(user, self.build_message(user))


def _format_task_created_message(task: Task) -> str:
    lines = ["🆕 Nova tarefa", "", "Título:", task.title]
    lines += ["", "Prazo:", task.due_date.strftime("%d/%m/%Y")]
    if task.category:
        lines += ["", "Categoria:", task.category.name]
    return "\n".join(lines)


def _format_task_completed_message(task: Task) -> str:
    return f"✅ Tarefa concluída\n\nTítulo:\n{task.title}"


def _format_task_overdue_message(task: Task) -> str:
    lines = ["⚠️ Tarefa vencida", "", "Título:", task.title, "", "Prazo:", task.due_date.strftime("%d/%m/%Y")]
    return "\n".join(lines)
