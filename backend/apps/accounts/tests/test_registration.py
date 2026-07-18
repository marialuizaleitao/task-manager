import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

User = get_user_model()

REGISTER_URL = reverse("accounts:register")


@pytest.mark.django_db
def test_register_creates_user_successfully(api_client):
    payload = {
        "email": "new.user@example.com",
        "password": "StrongPass123!",
        "password_confirm": "StrongPass123!",
        "first_name": "Nova",
        "last_name": "Usuária",
    }

    response = api_client.post(REGISTER_URL, payload)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["email"] == payload["email"]
    assert "password" not in response.data

    user = User.objects.get(email=payload["email"])
    assert user.check_password(payload["password"])


@pytest.mark.django_db
def test_register_fails_with_duplicate_email(api_client, user):
    payload = {
        "email": user.email,
        "password": "StrongPass123!",
        "password_confirm": "StrongPass123!",
    }

    response = api_client.post(REGISTER_URL, payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.data


@pytest.mark.django_db
def test_register_fails_when_passwords_dont_match(api_client):
    payload = {
        "email": "mismatch@example.com",
        "password": "StrongPass123!",
        "password_confirm": "SomethingElse456!",
    }

    response = api_client.post(REGISTER_URL, payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "password_confirm" in response.data


@pytest.mark.django_db
def test_register_fails_with_weak_password(api_client):
    payload = {
        "email": "weak@example.com",
        "password": "12345678",
        "password_confirm": "12345678",
    }

    response = api_client.post(REGISTER_URL, payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not User.objects.filter(email="weak@example.com").exists()
