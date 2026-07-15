import pytest
from django.urls import reverse
from rest_framework import status

from apps.categories.models import Category
from apps.tasks.models import Task

LIST_URL = reverse("tasks:task-list")


def detail_url(task_id: int) -> str:
    return reverse("tasks:task-detail", args=[task_id])


@pytest.mark.django_db
def test_create_task_without_category(authenticated_client, user):
    payload = {"title": "Comprar leite"}

    response = authenticated_client.post(LIST_URL, payload)

    assert response.status_code == status.HTTP_201_CREATED
    task = Task.objects.get(id=response.data["id"])
    assert task.owner == user
    assert task.category is None
    assert task.completed is False


@pytest.mark.django_db
def test_create_task_with_own_category(authenticated_client, user):
    category = Category.objects.create(owner=user, name="Trabalho", color="#111111")

    response = authenticated_client.post(LIST_URL, {"title": "Reunião", "category": category.id})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["category"] == category.id


@pytest.mark.django_db
def test_list_returns_only_own_tasks(authenticated_client, user, another_user):
    Task.objects.create(owner=user, title="Minha tarefa")
    Task.objects.create(owner=another_user, title="Tarefa alheia")

    response = authenticated_client.get(LIST_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["title"] == "Minha tarefa"


@pytest.mark.django_db
def test_retrieve_task(authenticated_client, user):
    task = Task.objects.create(owner=user, title="Estudar Django")

    response = authenticated_client.get(detail_url(task.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["title"] == "Estudar Django"


@pytest.mark.django_db
def test_update_task(authenticated_client, user):
    task = Task.objects.create(owner=user, title="Rascunho")

    response = authenticated_client.patch(detail_url(task.id), {"title": "Título final"})

    assert response.status_code == status.HTTP_200_OK
    task.refresh_from_db()
    assert task.title == "Título final"


@pytest.mark.django_db
def test_delete_task(authenticated_client, user):
    task = Task.objects.create(owner=user, title="Descartável")

    response = authenticated_client.delete(detail_url(task.id))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Task.objects.filter(id=task.id).exists()
