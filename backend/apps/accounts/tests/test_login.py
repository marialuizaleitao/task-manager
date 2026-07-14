import pytest
from django.urls import reverse
from rest_framework import status

LOGIN_URL = reverse("accounts:login")


@pytest.mark.django_db
def test_login_returns_tokens_for_valid_credentials(api_client, user):
    response = api_client.post(
        LOGIN_URL, {"email": user.email, "password": "StrongPass123!"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
def test_login_fails_with_wrong_password(api_client, user):
    response = api_client.post(
        LOGIN_URL, {"email": user.email, "password": "WrongPassword!"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_login_fails_for_nonexistent_user(api_client):
    response = api_client.post(
        LOGIN_URL, {"email": "ghost@example.com", "password": "StrongPass123!"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
