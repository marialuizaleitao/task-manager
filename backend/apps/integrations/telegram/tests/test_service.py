from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from apps.integrations.exceptions import ProviderNotConfiguredError
from apps.integrations.interfaces import NotificationEvent
from apps.integrations.telegram import service as service_module
from apps.integrations.telegram.client import ChatUnreachableError
from apps.integrations.telegram.models import TelegramConnection
from apps.integrations.telegram.service import DailySummaryService, TelegramService


@pytest.fixture
def fake_client(monkeypatch):
    """Substitui TelegramClient por um dublê controlável nos testes de service."""
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(service_module, "TelegramClient", MagicMock(return_value=client))
    return client


@pytest.fixture(autouse=True)
def bot_token(settings):
    settings.TELEGRAM_BOT_TOKEN = "fake-bot-token"


class TestIsConnected:
    def test_false_without_bot_token(self, user, telegram_connection, settings):
        settings.TELEGRAM_BOT_TOKEN = ""
        assert TelegramService().is_connected(user) is False

    def test_false_when_no_connection(self, user):
        assert TelegramService().is_connected(user) is False

    def test_false_when_pending(self, user, pending_telegram_connection):
        assert TelegramService().is_connected(user) is False

    def test_false_when_disabled(self, user, telegram_connection):
        telegram_connection.enabled = False
        telegram_connection.save()
        assert TelegramService().is_connected(user) is False

    def test_true_when_linked_and_enabled(self, user, telegram_connection):
        assert TelegramService().is_connected(user) is True


class TestNotify:
    """Cobre TelegramService.notify() para cada evento do catálogo (messages.py).

    A partir da Sprint 7.1, todo evento chega como um NotificationEvent —
    não há mais um método por tipo de evento (ver interfaces.NotificationProvider).
    """

    def test_task_created_skips_task_without_due_date(self, telegram_connection, task_factory, fake_client):
        task = task_factory(due_date=None)
        event = NotificationEvent(key="task.created", user=task.owner, subject=task)

        TelegramService().notify(event)

        fake_client.send_message.assert_not_called()

    def test_task_created_sends_formatted_message(self, telegram_connection, task_factory, fake_client):
        task = task_factory(title="Enviar documentação", due_date=date(2026, 7, 20))
        event = NotificationEvent(key="task.created", user=task.owner, subject=task)

        TelegramService().notify(event)

        fake_client.send_message.assert_called_once()
        chat_id, text = fake_client.send_message.call_args[0]
        assert chat_id == telegram_connection.telegram_chat_id
        assert "Enviar documentação" in text
        assert "20/07/2026" in text

    def test_task_created_includes_category_when_present(
        self, telegram_connection, task_factory, fake_client, category_factory
    ):
        category = category_factory(name="Trabalho")
        task = task_factory(due_date=date(2026, 7, 20), category=category)
        event = NotificationEvent(key="task.created", user=task.owner, subject=task)

        TelegramService().notify(event)

        _, text = fake_client.send_message.call_args[0]
        assert "Trabalho" in text

    def test_task_completed_sends_message(self, telegram_connection, task_factory, fake_client):
        task = task_factory(title="Revisar contrato")
        event = NotificationEvent(key="task.completed", user=task.owner, subject=task)

        TelegramService().notify(event)

        _, text = fake_client.send_message.call_args[0]
        assert "Revisar contrato" in text
        assert "concluída" in text.lower()

    def test_task_overdue_sends_message(self, telegram_connection, task_factory, fake_client):
        task = task_factory(title="Pagar fornecedor", due_date=date(2026, 7, 1))
        event = NotificationEvent(key="task.overdue", user=task.owner, subject=task)

        TelegramService().notify(event)

        _, text = fake_client.send_message.call_args[0]
        assert "Pagar fornecedor" in text
        assert "vencida" in text.lower()

    def test_unknown_event_key_is_ignored(self, telegram_connection, fake_client):
        event = NotificationEvent(key="unknown.event", user=telegram_connection.owner)

        TelegramService().notify(event)

        fake_client.send_message.assert_not_called()


class TestSendText:
    def test_send_text_raises_when_not_connected(self, user):
        with pytest.raises(ProviderNotConfiguredError):
            TelegramService().send_text(user, "oi")

    def test_send_text_updates_last_contact_at_on_success(self, telegram_connection, fake_client):
        TelegramService().send_text(telegram_connection.owner, "oi")

        telegram_connection.refresh_from_db()
        assert telegram_connection.last_contact_at is not None

    def test_send_text_disables_connection_when_chat_unreachable(self, telegram_connection, fake_client):
        fake_client.send_message.side_effect = ChatUnreachableError("bot was blocked by the user")

        with pytest.raises(ChatUnreachableError):
            TelegramService().send_text(telegram_connection.owner, "oi")

        telegram_connection.refresh_from_db()
        assert telegram_connection.enabled is False


class TestLinking:
    def test_start_linking_requires_bot_token(self, user, settings):
        settings.TELEGRAM_BOT_TOKEN = ""

        with pytest.raises(ProviderNotConfiguredError):
            TelegramService().start_linking(user)

    def test_start_linking_creates_pending_connection_and_deep_link(self, user, fake_client):
        fake_client.get_me.return_value = {"id": 1, "username": "task_manager_bot"}

        data = TelegramService().start_linking(user)

        connection = TelegramConnection.objects.get(owner=user)
        assert connection.linking_code is not None
        assert data["deep_link"] == f"https://t.me/task_manager_bot?start={connection.linking_code}"

    def test_confirm_linking_without_pending_code_raises(self, user):
        with pytest.raises(ProviderNotConfiguredError):
            TelegramService().confirm_linking(user)

    def test_confirm_linking_returns_unlinked_connection_when_no_match(
        self, user, pending_telegram_connection, fake_client
    ):
        fake_client.get_updates.return_value = []

        connection = TelegramService().confirm_linking(user)

        assert connection.is_linked() is False

    def test_confirm_linking_finalizes_connection_on_match(self, user, pending_telegram_connection, fake_client):
        fake_client.get_updates.return_value = [
            {
                "update_id": 1,
                "message": {
                    "text": f"/start {pending_telegram_connection.linking_code}",
                    "chat": {"id": 555, "username": "maria_dev"},
                },
            }
        ]

        connection = TelegramService().confirm_linking(user)

        assert connection.is_linked() is True
        assert connection.telegram_chat_id == "555"
        assert connection.telegram_username == "maria_dev"
        assert connection.linking_code is None
        assert connection.enabled is True

    def test_confirm_linking_ignores_unrelated_updates(self, user, pending_telegram_connection, fake_client):
        fake_client.get_updates.return_value = [
            {"update_id": 1, "message": {"text": "/start outro-codigo", "chat": {"id": 999}}}
        ]

        connection = TelegramService().confirm_linking(user)

        assert connection.is_linked() is False


class TestConnectionManagement:
    def test_set_enabled_updates_flag(self, telegram_connection):
        connection = TelegramService().set_enabled(telegram_connection.owner, False)
        assert connection.enabled is False

    def test_set_enabled_raises_when_not_connected(self, user):
        with pytest.raises(ProviderNotConfiguredError):
            TelegramService().set_enabled(user, False)

    def test_disconnect_removes_connection(self, telegram_connection):
        owner = telegram_connection.owner

        TelegramService().disconnect(owner)

        assert not TelegramConnection.objects.filter(owner=owner).exists()

    def test_disconnect_is_idempotent(self, user):
        TelegramService().disconnect(user)


class TestDailySummaryService:
    def test_build_message_without_pending_tasks(self, user):
        message = DailySummaryService().build_message(user)

        assert "não tem nenhuma tarefa pendente" in message.lower()

    def test_build_message_counts_pending_due_today_and_overdue(self, user, task_factory):
        today = timezone.localdate()
        task_factory(title="Revisar PR", due_date=today, completed=False)
        task_factory(title="Atrasada", due_date=today - timedelta(days=2), completed=False)
        task_factory(title="Sem prazo", due_date=None, completed=False)

        message = DailySummaryService().build_message(user)

        assert "3 tarefa(s) pendente(s)" in message
        assert "1 tarefa(s) vencendo hoje" in message
        assert "1 tarefa(s) atrasada(s)" in message

    def test_build_message_ignores_completed_tasks(self, user, task_factory):
        today = timezone.localdate()
        task_factory(title="Já feita", due_date=today, completed=True)

        message = DailySummaryService().build_message(user)

        assert "não tem nenhuma tarefa pendente" in message.lower()

    def test_send_summary_delegates_to_telegram_service(self, user):
        telegram_service = MagicMock()

        DailySummaryService(telegram_service=telegram_service).send_summary(user)

        telegram_service.send_text.assert_called_once()
        called_user, called_text = telegram_service.send_text.call_args[0]
        assert called_user == user
        assert isinstance(called_text, str)
