import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(email="user@example.com", password="StrongPass123!")


@pytest.fixture
def another_user(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(email="other@example.com", password="StrongPass123!")


@pytest.fixture
def third_user(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(email="third@example.com", password="StrongPass123!")


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def another_authenticated_client(another_user) -> APIClient:
    # Instância própria de APIClient: reaproveitar a fixture api_client aqui
    # faria authenticated_client e another_authenticated_client compartilharem
    # o mesmo client, e o segundo force_authenticate sobrescreveria o primeiro.
    client = APIClient()
    client.force_authenticate(user=another_user)
    return client


@pytest.fixture
def third_authenticated_client(third_user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=third_user)
    return client
