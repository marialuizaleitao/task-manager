from unittest.mock import MagicMock

import pytest
from django.urls import reverse
from rest_framework import status

from apps.integrations.exceptions import ExternalServiceError
from apps.integrations.telegram import service as service_module
from apps.integrations.telegram.models import TelegramConnection


@pytest.fixture
def fake_client(monkeypatch):
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(service_module, "TelegramClient", MagicMock(return_value=client))
    return client


@pytest.mark.django_db
def test_connect_returns_deep_link(authenticated_client, fake_client):
    fake_client.get_me.return_value = {"id": 1, "username": "task_manager_bot"}

    response = authenticated_client.get(reverse("telegram:connect"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["deep_link"].startswith("https://t.me/task_manager_bot?start=")


@pytest.mark.django_db
def test_connect_requires_authentication(api_client):
    response = api_client.get(reverse("telegram:connect"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_connect_returns_503_without_bot_token(authenticated_client, settings):
    settings.TELEGRAM_BOT_TOKEN = ""

    response = authenticated_client.get(reverse("telegram:connect"))

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.django_db
def test_connect_returns_502_when_telegram_unreachable(authenticated_client, fake_client):
    fake_client.get_me.side_effect = ExternalServiceError("timeout")

    response = authenticated_client.get(reverse("telegram:connect"))

    assert response.status_code == status.HTTP_502_BAD_GATEWAY


@pytest.mark.django_db
def test_confirm_without_pending_linking_returns_503(authenticated_client):
    response = authenticated_client.post(reverse("telegram:confirm"))

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.django_db
def test_confirm_returns_not_connected_when_no_match(authenticated_client, pending_telegram_connection, fake_client):
    fake_client.get_updates.return_value = []

    response = authenticated_client.post(reverse("telegram:confirm"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["connected"] is False


@pytest.mark.django_db
def test_confirm_finalizes_connection_on_match(authenticated_client, pending_telegram_connection, fake_client):
    fake_client.get_updates.return_value = [
        {
            "message": {
                "text": f"/start {pending_telegram_connection.linking_code}",
                "chat": {"id": 777, "username": "maria_dev"},
            }
        }
    ]

    response = authenticated_client.post(reverse("telegram:confirm"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["connected"] is True
    assert response.data["telegram_username"] == "maria_dev"


@pytest.mark.django_db
def test_status_when_not_connected(authenticated_client):
    response = authenticated_client.get(reverse("telegram:status"))

    assert response.data == {"connected": False, "enabled": False}


@pytest.mark.django_db
def test_status_when_connected(authenticated_client, telegram_connection):
    response = authenticated_client.get(reverse("telegram:status"))

    assert response.data["connected"] is True
    assert response.data["telegram_username"] == telegram_connection.telegram_username


@pytest.mark.django_db
def test_status_when_pending_reports_not_connected(authenticated_client, pending_telegram_connection):
    response = authenticated_client.get(reverse("telegram:status"))

    assert response.data["connected"] is False


@pytest.mark.django_db
def test_toggle_updates_enabled_flag(authenticated_client, telegram_connection):
    response = authenticated_client.post(reverse("telegram:toggle"), {"enabled": False}, format="json")

    assert response.status_code == status.HTTP_200_OK
    telegram_connection.refresh_from_db()
    assert telegram_connection.enabled is False


@pytest.mark.django_db
def test_toggle_returns_404_when_not_connected(authenticated_client):
    response = authenticated_client.post(reverse("telegram:toggle"), {"enabled": False}, format="json")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_disconnect_removes_connection(authenticated_client, telegram_connection):
    owner = telegram_connection.owner

    response = authenticated_client.delete(reverse("telegram:disconnect"))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not TelegramConnection.objects.filter(owner=owner).exists()


@pytest.mark.django_db
def test_disconnect_is_idempotent_when_not_connected(authenticated_client):
    response = authenticated_client.delete(reverse("telegram:disconnect"))

    assert response.status_code == status.HTTP_204_NO_CONTENT
