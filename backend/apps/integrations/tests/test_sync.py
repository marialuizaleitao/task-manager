from datetime import date
from unittest.mock import MagicMock

import pytest

from apps.integrations import registry, sync
from apps.integrations.interfaces import NotificationEvent


@pytest.fixture
def fake_provider(monkeypatch):
    provider = MagicMock()
    monkeypatch.setattr(registry, "_calendar_providers", {"fake": lambda: provider})
    return provider


@pytest.fixture
def fake_notification_provider(monkeypatch):
    provider = MagicMock()
    monkeypatch.setattr(registry, "_notification_providers", {"fake": lambda: provider})
    return provider


@pytest.mark.django_db
def test_sync_task_skips_provider_not_connected(fake_provider, task_factory):
    fake_provider.is_connected.return_value = False
    task = task_factory(due_date=date(2026, 8, 1))

    sync.sync_task(task, sync.CREATE)

    fake_provider.sync_create.assert_not_called()


@pytest.mark.django_db
def test_sync_task_routes_create_action(fake_provider, task_factory):
    fake_provider.is_connected.return_value = True
    task = task_factory(due_date=date(2026, 8, 1))

    sync.sync_task(task, sync.CREATE)

    fake_provider.sync_create.assert_called_once_with(task)


@pytest.mark.django_db
def test_sync_task_routes_update_action(fake_provider, task_factory):
    fake_provider.is_connected.return_value = True
    task = task_factory(due_date=date(2026, 8, 1))

    sync.sync_task(task, sync.UPDATE)

    fake_provider.sync_update.assert_called_once_with(task)


@pytest.mark.django_db
def test_sync_task_routes_delete_action(fake_provider, task_factory):
    fake_provider.is_connected.return_value = True
    task = task_factory(due_date=date(2026, 8, 1))

    sync.sync_task(task, sync.DELETE)

    fake_provider.sync_delete.assert_called_once_with(task)


@pytest.mark.django_db
def test_sync_task_never_raises_when_provider_fails(fake_provider, task_factory):
    fake_provider.is_connected.return_value = True
    fake_provider.sync_create.side_effect = RuntimeError("Google indisponível")
    task = task_factory(due_date=date(2026, 8, 1))

    sync.sync_task(task, sync.CREATE)  # não deve levantar


@pytest.mark.django_db
def test_sync_task_isolates_failure_of_one_provider_from_others(monkeypatch, task_factory):
    failing_provider = MagicMock()
    failing_provider.is_connected.return_value = True
    failing_provider.sync_create.side_effect = RuntimeError("boom")

    healthy_provider = MagicMock()
    healthy_provider.is_connected.return_value = True

    monkeypatch.setattr(
        registry,
        "_calendar_providers",
        {"failing": lambda: failing_provider, "healthy": lambda: healthy_provider},
    )
    task = task_factory(due_date=date(2026, 8, 1))

    sync.sync_task(task, sync.CREATE)

    healthy_provider.sync_create.assert_called_once_with(task)


@pytest.mark.django_db
def test_notify_task_skips_provider_not_connected(fake_notification_provider, task_factory):
    fake_notification_provider.is_connected.return_value = False
    task = task_factory(due_date=date(2026, 8, 1))

    sync.notify_task(task, sync.TaskEvent.CREATED)

    fake_notification_provider.notify.assert_not_called()


@pytest.mark.django_db
def test_notify_task_routes_created_event(fake_notification_provider, task_factory):
    fake_notification_provider.is_connected.return_value = True
    task = task_factory(due_date=date(2026, 8, 1))

    sync.notify_task(task, sync.TaskEvent.CREATED)

    fake_notification_provider.notify.assert_called_once_with(
        NotificationEvent(key="task.created", user=task.owner, subject=task)
    )


@pytest.mark.django_db
def test_notify_task_routes_completed_event(fake_notification_provider, task_factory):
    fake_notification_provider.is_connected.return_value = True
    task = task_factory(due_date=date(2026, 8, 1))

    sync.notify_task(task, sync.TaskEvent.COMPLETED)

    fake_notification_provider.notify.assert_called_once_with(
        NotificationEvent(key="task.completed", user=task.owner, subject=task)
    )


@pytest.mark.django_db
def test_notify_task_routes_overdue_event(fake_notification_provider, task_factory):
    fake_notification_provider.is_connected.return_value = True
    task = task_factory(due_date=date(2026, 8, 1))

    sync.notify_task(task, sync.TaskEvent.OVERDUE)

    fake_notification_provider.notify.assert_called_once_with(
        NotificationEvent(key="task.overdue", user=task.owner, subject=task)
    )


@pytest.mark.django_db
def test_notify_task_rejects_unknown_event(fake_notification_provider, task_factory):
    task = task_factory(due_date=date(2026, 8, 1))

    with pytest.raises(ValueError):
        sync.notify_task(task, "invalid-event")


@pytest.mark.django_db
def test_notify_task_never_raises_when_provider_fails(fake_notification_provider, task_factory):
    fake_notification_provider.is_connected.return_value = True
    fake_notification_provider.notify.side_effect = RuntimeError("Telegram indisponível")
    task = task_factory(due_date=date(2026, 8, 1))

    sync.notify_task(task, sync.TaskEvent.CREATED)  # não deve levantar


@pytest.mark.django_db
def test_notify_task_is_independent_from_sync_task(fake_provider, fake_notification_provider, task_factory):
    fake_provider.is_connected.return_value = True
    fake_notification_provider.is_connected.return_value = True
    task = task_factory(due_date=date(2026, 8, 1))

    sync.notify_task(task, sync.TaskEvent.CREATED)

    fake_provider.sync_create.assert_not_called()
    fake_notification_provider.notify.assert_called_once()
