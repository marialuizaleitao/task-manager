from unittest.mock import MagicMock

import pytest

from apps.integrations import notifications, registry
from apps.integrations.interfaces import NotificationEvent


@pytest.fixture
def fake_provider(monkeypatch):
    provider = MagicMock()
    monkeypatch.setattr(registry, "_notification_providers", {"fake": lambda: provider})
    return provider


def _event(**overrides) -> NotificationEvent:
    defaults = {"key": "task.created", "user": object(), "subject": None, "context": {}}
    defaults.update(overrides)
    return NotificationEvent(**defaults)


def test_notify_skips_provider_not_connected(fake_provider):
    fake_provider.is_connected.return_value = False
    event = _event()

    notifications.notify(event)

    fake_provider.notify.assert_not_called()


def test_notify_dispatches_to_connected_provider(fake_provider):
    fake_provider.is_connected.return_value = True
    event = _event()

    notifications.notify(event)

    fake_provider.notify.assert_called_once_with(event)


def test_notify_never_raises_when_provider_fails(fake_provider):
    fake_provider.is_connected.return_value = True
    fake_provider.notify.side_effect = RuntimeError("provedor indisponível")

    notifications.notify(_event())  # não deve levantar


def test_notify_isolates_failure_of_one_provider_from_others(monkeypatch):
    failing_provider = MagicMock()
    failing_provider.is_connected.return_value = True
    failing_provider.notify.side_effect = RuntimeError("boom")

    healthy_provider = MagicMock()
    healthy_provider.is_connected.return_value = True

    monkeypatch.setattr(
        registry,
        "_notification_providers",
        {"failing": lambda: failing_provider, "healthy": lambda: healthy_provider},
    )
    event = _event()

    notifications.notify(event)

    healthy_provider.notify.assert_called_once_with(event)


def test_notify_with_no_registered_providers_is_noop(monkeypatch):
    monkeypatch.setattr(registry, "_notification_providers", {})

    notifications.notify(_event())  # não deve levantar nem fazer nada
