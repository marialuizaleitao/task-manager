from datetime import date
from unittest.mock import MagicMock

import pytest

from apps.integrations import registry, sync


@pytest.fixture
def fake_provider(monkeypatch):
    provider = MagicMock()
    monkeypatch.setattr(registry, "_calendar_providers", {"fake": lambda: provider})
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
