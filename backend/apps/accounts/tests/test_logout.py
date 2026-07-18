import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

LOGOUT_URL = reverse("accounts:logout")
LOGIN_REFRESH_URL = reverse("accounts:login-refresh")


@pytest.mark.django_db
def test_logout_blacklists_refresh_token(api_client, user):
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = api_client.post(LOGOUT_URL, {"refresh": str(refresh)})

    assert response.status_code == status.HTTP_205_RESET_CONTENT


@pytest.mark.django_db
def test_logout_requires_authentication(api_client, user):
    refresh = RefreshToken.for_user(user)

    response = api_client.post(LOGOUT_URL, {"refresh": str(refresh)})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_blacklisted_refresh_token_cannot_be_used_again(api_client, user):
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    api_client.post(LOGOUT_URL, {"refresh": str(refresh)})

    api_client.credentials()
    response = api_client.post(LOGIN_REFRESH_URL, {"refresh": str(refresh)})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
