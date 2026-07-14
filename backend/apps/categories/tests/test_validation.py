import pytest
from django.urls import reverse
from rest_framework import status

from apps.categories.models import Category

LIST_URL = reverse("categories:category-list")


@pytest.mark.django_db
def test_name_is_required(authenticated_client):
    response = authenticated_client.post(LIST_URL, {"color": "#111111"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "name" in response.data


@pytest.mark.django_db
def test_color_must_be_valid_hex(authenticated_client):
    response = authenticated_client.post(LIST_URL, {"name": "Trabalho", "color": "azul"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "color" in response.data


@pytest.mark.django_db
def test_color_is_required(authenticated_client):
    response = authenticated_client.post(LIST_URL, {"name": "Trabalho"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "color" in response.data


@pytest.mark.django_db
def test_cannot_create_duplicate_category_name_for_same_user(authenticated_client, user):
    Category.objects.create(owner=user, name="Trabalho", color="#111111")

    response = authenticated_client.post(LIST_URL, {"name": "trabalho", "color": "#222222"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "name" in response.data


@pytest.mark.django_db
def test_different_users_can_have_categories_with_same_name(authenticated_client, another_user):
    Category.objects.create(owner=another_user, name="Trabalho", color="#111111")

    response = authenticated_client.post(LIST_URL, {"name": "Trabalho", "color": "#222222"})

    assert response.status_code == status.HTTP_201_CREATED
