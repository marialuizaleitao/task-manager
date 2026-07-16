from apps.integrations import registry


class FakeProvider:
    def is_connected(self, user):
        return True


class FakeNotificationProvider:
    def is_connected(self, user):
        return True

    def notify_task_created(self, task):
        pass

    def notify_task_completed(self, task):
        pass

    def notify_task_overdue(self, task):
        pass


def test_register_and_get_calendar_provider(monkeypatch):
    monkeypatch.setattr(registry, "_calendar_providers", {})

    registry.register_calendar_provider("fake", FakeProvider)
    provider = registry.get_calendar_provider("fake")

    assert isinstance(provider, FakeProvider)


def test_get_unknown_provider_returns_none(monkeypatch):
    monkeypatch.setattr(registry, "_calendar_providers", {})

    assert registry.get_calendar_provider("unknown") is None


def test_registered_calendar_providers_lists_registered_keys(monkeypatch):
    monkeypatch.setattr(registry, "_calendar_providers", {})

    registry.register_calendar_provider("fake", FakeProvider)

    assert registry.registered_calendar_providers() == ["fake"]


def test_google_calendar_provider_is_registered_on_app_ready():
    # GoogleCalendarConfig.ready() já rodou na inicialização do Django de
    # teste — este teste garante que a app real está de fato registrada,
    # sem o qual sync_task nunca chamaria o provedor Google.
    assert "google_calendar" in registry.registered_calendar_providers()


def test_register_and_get_notification_provider(monkeypatch):
    monkeypatch.setattr(registry, "_notification_providers", {})

    registry.register_notification_provider("fake", FakeNotificationProvider)
    provider = registry.get_notification_provider("fake")

    assert isinstance(provider, FakeNotificationProvider)


def test_get_unknown_notification_provider_returns_none(monkeypatch):
    monkeypatch.setattr(registry, "_notification_providers", {})

    assert registry.get_notification_provider("unknown") is None


def test_registered_notification_providers_lists_registered_keys(monkeypatch):
    monkeypatch.setattr(registry, "_notification_providers", {})

    registry.register_notification_provider("fake", FakeNotificationProvider)

    assert registry.registered_notification_providers() == ["fake"]


def test_calendar_and_notification_registries_are_independent(monkeypatch):
    monkeypatch.setattr(registry, "_calendar_providers", {})
    monkeypatch.setattr(registry, "_notification_providers", {})

    registry.register_calendar_provider("fake", FakeProvider)

    assert registry.registered_calendar_providers() == ["fake"]
    assert registry.registered_notification_providers() == []


def test_telegram_provider_is_registered_on_app_ready():
    # TelegramConfig.ready() já rodou na inicialização do Django de teste —
    # este teste garante que a app real está de fato registrada, sem o qual
    # notify_task nunca chamaria o provedor Telegram.
    assert "telegram" in registry.registered_notification_providers()
