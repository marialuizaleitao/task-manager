from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from apps.integrations.exceptions import ExternalServiceError, ProviderNotConfiguredError
from apps.integrations.google_calendar import oauth
from apps.integrations.google_calendar import service as service_module
from apps.integrations.google_calendar.models import GoogleCalendarEventLink, SyncStatus
from apps.integrations.google_calendar.service import GoogleCalendarService


@pytest.fixture
def fake_client(monkeypatch):
    """Substitui GoogleCalendarClient por um dublê controlável nos testes de service."""
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(service_module, "GoogleCalendarClient", MagicMock(return_value=client))
    return client


@pytest.mark.django_db
def test_is_connected_false_when_no_credential(user):
    assert GoogleCalendarService().is_connected(user) is False


@pytest.mark.django_db
def test_is_connected_false_when_disabled(user, connected_credential):
    connected_credential.enabled = False
    connected_credential.save()

    assert GoogleCalendarService().is_connected(user) is False


@pytest.mark.django_db
def test_is_connected_true_when_enabled(user, connected_credential):
    assert GoogleCalendarService().is_connected(user) is True


@pytest.mark.django_db
def test_sync_create_skips_task_without_due_date(connected_credential, task_factory, fake_client):
    task = task_factory(due_date=None)

    GoogleCalendarService().sync_create(task)

    fake_client.create_event.assert_not_called()
    assert not GoogleCalendarEventLink.objects.filter(task=task).exists()


@pytest.mark.django_db
def test_sync_create_without_connection_raises_provider_not_configured(task_factory):
    task = task_factory(due_date=date(2026, 8, 1))

    with pytest.raises(ProviderNotConfiguredError):
        GoogleCalendarService().sync_create(task)


@pytest.mark.django_db
def test_sync_create_success_marks_link_synced(connected_credential, task_factory, fake_client):
    fake_client.create_event.return_value = "evt-1"
    task = task_factory(due_date=date(2026, 8, 1))

    GoogleCalendarService().sync_create(task)

    link = GoogleCalendarEventLink.objects.get(task=task)
    assert link.status == SyncStatus.SYNCED
    assert link.google_event_id == "evt-1"
    assert link.last_error == ""
    assert link.last_synced_at is not None


@pytest.mark.django_db
def test_sync_create_failure_marks_link_failed_and_reraises(connected_credential, task_factory, fake_client):
    fake_client.create_event.side_effect = ExternalServiceError("timeout ao criar evento")
    task = task_factory(due_date=date(2026, 8, 1))

    with pytest.raises(ExternalServiceError):
        GoogleCalendarService().sync_create(task)

    link = GoogleCalendarEventLink.objects.get(task=task)
    assert link.status == SyncStatus.FAILED
    assert "timeout" in link.last_error


@pytest.mark.django_db
def test_sync_update_creates_event_when_never_synced(connected_credential, task_factory, fake_client):
    fake_client.create_event.return_value = "evt-1"
    task = task_factory(due_date=date(2026, 8, 1))

    GoogleCalendarService().sync_update(task)

    fake_client.create_event.assert_called_once()
    fake_client.update_event.assert_not_called()


@pytest.mark.django_db
def test_sync_update_patches_existing_event(connected_credential, task_factory, fake_client):
    task = task_factory(due_date=date(2026, 8, 1))
    GoogleCalendarEventLink.objects.create(task=task, google_event_id="evt-1", status=SyncStatus.SYNCED)
    fake_client.update_event.return_value = "evt-1"

    GoogleCalendarService().sync_update(task)

    fake_client.update_event.assert_called_once_with(task, "evt-1")


@pytest.mark.django_db
def test_sync_update_deletes_event_when_due_date_removed(connected_credential, task_factory, fake_client):
    task = task_factory(due_date=None)
    GoogleCalendarEventLink.objects.create(task=task, google_event_id="evt-1", status=SyncStatus.SYNCED)

    GoogleCalendarService().sync_update(task)

    fake_client.delete_event.assert_called_once_with("evt-1")
    assert not GoogleCalendarEventLink.objects.filter(task=task).exists()


@pytest.mark.django_db
def test_sync_delete_removes_event_and_link(connected_credential, task_factory, fake_client):
    task = task_factory(due_date=date(2026, 8, 1))
    GoogleCalendarEventLink.objects.create(task=task, google_event_id="evt-1", status=SyncStatus.SYNCED)

    GoogleCalendarService().sync_delete(task)

    fake_client.delete_event.assert_called_once_with("evt-1")
    assert not GoogleCalendarEventLink.objects.filter(task=task).exists()


@pytest.mark.django_db
def test_sync_delete_is_noop_when_never_synced(connected_credential, task_factory, fake_client):
    task = task_factory(due_date=date(2026, 8, 1))

    GoogleCalendarService().sync_delete(task)

    fake_client.delete_event.assert_not_called()


@pytest.mark.django_db
def test_ensure_valid_token_refreshes_expired_credential(expired_credential, task_factory, fake_client, monkeypatch):
    refreshed = oauth.TokenResponse(
        access_token="refreshed-access-token",
        refresh_token="refreshed-refresh-token",
        expires_at=timezone.now() + timedelta(hours=1),
    )
    monkeypatch.setattr(oauth, "refresh_access_token", MagicMock(return_value=refreshed))
    fake_client.create_event.return_value = "evt-1"
    task = task_factory(due_date=date(2026, 8, 1))

    GoogleCalendarService().sync_create(task)

    expired_credential.refresh_from_db()
    assert expired_credential.access_token == "refreshed-access-token"
    assert expired_credential.refresh_token == "refreshed-refresh-token"


@pytest.mark.django_db
def test_ensure_valid_token_propagates_invalid_grant(expired_credential, task_factory, fake_client, monkeypatch):
    from apps.integrations.exceptions import AuthenticationExpiredError

    monkeypatch.setattr(
        oauth, "refresh_access_token", MagicMock(side_effect=AuthenticationExpiredError("invalid_grant"))
    )
    task = task_factory(due_date=date(2026, 8, 1))

    with pytest.raises(AuthenticationExpiredError):
        GoogleCalendarService().sync_create(task)

    link = GoogleCalendarEventLink.objects.get(task=task)
    assert link.status == SyncStatus.FAILED
