import pytest
from django.urls import reverse
from rest_framework import status

from apps.tasks.models import Task

LIST_URL = reverse("tasks:task-list")


def detail_url(task_id: int) -> str:
    return reverse("tasks:task-detail", args=[task_id])


@pytest.mark.django_db
def test_list_requires_authentication(api_client):
    response = api_client.get(LIST_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_create_requires_authentication(api_client):
    response = api_client.post(LIST_URL, {"title": "Tarefa"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_cannot_retrieve_another_users_task(authenticated_client, another_user):
    task = Task.objects.create(owner=another_user, title="Tarefa alheia")

    response = authenticated_client.get(detail_url(task.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_cannot_update_another_users_task(authenticated_client, another_user):
    task = Task.objects.create(owner=another_user, title="Tarefa alheia")

    response = authenticated_client.patch(detail_url(task.id), {"title": "Invadida"})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    task.refresh_from_db()
    assert task.title == "Tarefa alheia"


@pytest.mark.django_db
def test_cannot_delete_another_users_task(authenticated_client, another_user):
    task = Task.objects.create(owner=another_user, title="Tarefa alheia")

    response = authenticated_client.delete(detail_url(task.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert Task.objects.filter(id=task.id).exists()
