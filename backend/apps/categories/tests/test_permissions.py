import pytest
from django.urls import reverse
from rest_framework import status

from apps.categories.models import Category

LIST_URL = reverse("categories:category-list")


def detail_url(category_id: int) -> str:
    return reverse("categories:category-detail", args=[category_id])


@pytest.mark.django_db
def test_list_requires_authentication(api_client):
    response = api_client.get(LIST_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_create_requires_authentication(api_client):
    response = api_client.post(LIST_URL, {"name": "Trabalho", "color": "#111111"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_cannot_retrieve_another_users_category(authenticated_client, another_user):
    category = Category.objects.create(owner=another_user, name="Pessoal", color="#222222")

    response = authenticated_client.get(detail_url(category.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_cannot_update_another_users_category(authenticated_client, another_user):
    category = Category.objects.create(owner=another_user, name="Pessoal", color="#222222")

    response = authenticated_client.patch(detail_url(category.id), {"name": "Hackeada"})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    category.refresh_from_db()
    assert category.name == "Pessoal"


@pytest.mark.django_db
def test_cannot_delete_another_users_category(authenticated_client, another_user):
    category = Category.objects.create(owner=another_user, name="Pessoal", color="#222222")

    response = authenticated_client.delete(detail_url(category.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert Category.objects.filter(id=category.id).exists()
