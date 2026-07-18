from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from django.core import signing
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.integrations.google_calendar import oauth
from apps.integrations.google_calendar.models import GoogleCalendarCredential


@pytest.mark.django_db
def test_connect_returns_authorization_url(authenticated_client):
    response = authenticated_client.get(reverse("google_calendar:connect"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["authorization_url"].startswith(oauth.AUTHORIZATION_ENDPOINT)


@pytest.mark.django_db
def test_connect_requires_authentication(api_client):
    response = api_client.get(reverse("google_calendar:connect"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_callback_creates_credential_and_redirects_to_success(api_client, user, monkeypatch):
    state = signing.dumps({"user_id": user.id}, salt=oauth._STATE_SALT)
    tokens = oauth.TokenResponse(
        access_token="at", refresh_token="rt", expires_at=timezone.now() + timedelta(hours=1)
    )
    monkeypatch.setattr(oauth, "exchange_code_for_tokens", MagicMock(return_value=tokens))

    response = api_client.get(reverse("google_calendar:callback"), {"code": "auth-code", "state": state})

    assert response.status_code == status.HTTP_302_FOUND
    assert "google_calendar=connected" in response.url
    credential = GoogleCalendarCredential.objects.get(owner=user)
    assert credential.access_token == "at"
    assert credential.enabled is True


@pytest.mark.django_db
def test_callback_redirects_with_error_when_google_denies_consent(api_client):
    response = api_client.get(reverse("google_calendar:callback"), {"error": "access_denied"})

    assert response.status_code == status.HTTP_302_FOUND
    assert "google_calendar=error" in response.url


@pytest.mark.django_db
def test_callback_redirects_with_error_on_invalid_state(api_client):
    response = api_client.get(reverse("google_calendar:callback"), {"code": "auth-code", "state": "invalid"})

    assert response.status_code == status.HTTP_302_FOUND
    assert "google_calendar=error" in response.url


@pytest.mark.django_db
def test_callback_redirects_with_error_when_token_exchange_fails(api_client, user, monkeypatch):
    from apps.integrations.exceptions import ExternalServiceError

    state = signing.dumps({"user_id": user.id}, salt=oauth._STATE_SALT)
    monkeypatch.setattr(
        oauth, "exchange_code_for_tokens", MagicMock(side_effect=ExternalServiceError("timeout"))
    )

    response = api_client.get(reverse("google_calendar:callback"), {"code": "auth-code", "state": state})

    assert response.status_code == status.HTTP_302_FOUND
    assert "google_calendar=error" in response.url
    assert not GoogleCalendarCredential.objects.filter(owner=user).exists()


@pytest.mark.django_db
def test_status_when_not_connected(authenticated_client):
    response = authenticated_client.get(reverse("google_calendar:status"))

    assert response.data == {"connected": False, "enabled": False}


@pytest.mark.django_db
def test_status_when_connected(authenticated_client, connected_credential):
    response = authenticated_client.get(reverse("google_calendar:status"))

    assert response.data["connected"] is True
    assert response.data["enabled"] is True


@pytest.mark.django_db
def test_toggle_updates_enabled_flag(authenticated_client, connected_credential):
    response = authenticated_client.post(reverse("google_calendar:toggle"), {"enabled": False}, format="json")

    assert response.status_code == status.HTTP_200_OK
    connected_credential.refresh_from_db()
    assert connected_credential.enabled is False


@pytest.mark.django_db
def test_toggle_returns_404_when_not_connected(authenticated_client):
    response = authenticated_client.post(reverse("google_calendar:toggle"), {"enabled": False}, format="json")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_disconnect_removes_credential(authenticated_client, connected_credential, monkeypatch):
    monkeypatch.setattr(oauth, "revoke_token", MagicMock())
    owner = connected_credential.owner

    response = authenticated_client.delete(reverse("google_calendar:disconnect"))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not GoogleCalendarCredential.objects.filter(owner=owner).exists()


@pytest.mark.django_db
def test_disconnect_is_idempotent_when_not_connected(authenticated_client):
    response = authenticated_client.delete(reverse("google_calendar:disconnect"))

    assert response.status_code == status.HTTP_204_NO_CONTENT
