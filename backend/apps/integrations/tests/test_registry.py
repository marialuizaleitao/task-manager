from apps.integrations import registry


class FakeProvider:
    def is_connected(self, user):
        return True


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
