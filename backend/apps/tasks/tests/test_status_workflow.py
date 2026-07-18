import pytest
from django.urls import reverse
from rest_framework import status

from apps.tasks.models import Task


def detail_url(task_id: int) -> str:
    return reverse("tasks:task-detail", args=[task_id])


@pytest.mark.django_db
def test_mark_task_as_completed(authenticated_client, user):
    task = Task.objects.create(owner=user, title="Tarefa", completed=False)

    response = authenticated_client.patch(detail_url(task.id), {"completed": True})

    assert response.status_code == status.HTTP_200_OK
    task.refresh_from_db()
    assert task.completed is True


@pytest.mark.django_db
def test_mark_task_as_pending(authenticated_client, user):
    task = Task.objects.create(owner=user, title="Tarefa", completed=True)

    response = authenticated_client.patch(detail_url(task.id), {"completed": False})

    assert response.status_code == status.HTTP_200_OK
    task.refresh_from_db()
    assert task.completed is False
