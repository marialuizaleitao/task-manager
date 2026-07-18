import pytest
from django.urls import reverse
from rest_framework import status

from apps.categories.models import Category

LIST_URL = reverse("categories:category-list")


def detail_url(category_id: int) -> str:
    return reverse("categories:category-detail", args=[category_id])


@pytest.mark.django_db
def test_create_category(authenticated_client, user):
    payload = {"name": "Trabalho", "description": "Tarefas profissionais", "color": "#1A2B3C"}

    response = authenticated_client.post(LIST_URL, payload)

    assert response.status_code == status.HTTP_201_CREATED
    category = Category.objects.get(id=response.data["id"])
    assert category.owner == user
    assert category.name == "Trabalho"


@pytest.mark.django_db
def test_list_returns_only_own_categories(authenticated_client, user, another_user):
    Category.objects.create(owner=user, name="Trabalho", color="#111111")
    Category.objects.create(owner=another_user, name="Pessoal", color="#222222")

    response = authenticated_client.get(LIST_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == "Trabalho"


@pytest.mark.django_db
def test_retrieve_category(authenticated_client, user):
    category = Category.objects.create(owner=user, name="Trabalho", color="#111111")

    response = authenticated_client.get(detail_url(category.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["name"] == "Trabalho"


@pytest.mark.django_db
def test_update_category(authenticated_client, user):
    category = Category.objects.create(owner=user, name="Trabalho", color="#111111")

    response = authenticated_client.patch(detail_url(category.id), {"name": "Estudos"})

    assert response.status_code == status.HTTP_200_OK
    category.refresh_from_db()
    assert category.name == "Estudos"


@pytest.mark.django_db
def test_delete_category(authenticated_client, user):
    category = Category.objects.create(owner=user, name="Trabalho", color="#111111")

    response = authenticated_client.delete(detail_url(category.id))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Category.objects.filter(id=category.id).exists()
