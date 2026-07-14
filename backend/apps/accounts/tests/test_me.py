import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

ME_URL = reverse("accounts:me")


@pytest.mark.django_db
def test_me_returns_authenticated_user_data(api_client, user):
    token = RefreshToken.for_user(user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = api_client.get(ME_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["email"] == user.email


@pytest.mark.django_db
def test_me_requires_authentication(api_client):
    response = api_client.get(ME_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_me_rejects_invalid_token(api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token")

    response = api_client.get(ME_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
