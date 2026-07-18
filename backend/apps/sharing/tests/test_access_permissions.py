import pytest
from django.urls import reverse
from rest_framework import status

from apps.sharing.models import TaskShare
from apps.tasks.models import Task


def detail_url(task_id: int) -> str:
    return reverse("tasks:task-detail", args=[task_id])


@pytest.fixture
def task(user) -> Task:
    return Task.objects.create(owner=user, title="Tarefa original")


@pytest.mark.django_db
def test_shared_user_with_read_can_view_task(another_authenticated_client, task, another_user):
    TaskShare.objects.create(task=task, shared_with=another_user, permission="read")

    response = another_authenticated_client.get(detail_url(task.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["title"] == "Tarefa original"


@pytest.mark.django_db
def test_shared_user_with_read_cannot_edit_task(another_authenticated_client, task, another_user):
    TaskShare.objects.create(task=task, shared_with=another_user, permission="read")

    response = another_authenticated_client.patch(detail_url(task.id), {"title": "Invadida"})

    assert response.status_code == status.HTTP_403_FORBIDDEN
    task.refresh_from_db()
    assert task.title == "Tarefa original"


@pytest.mark.django_db
def test_shared_user_with_edit_can_view_task(another_authenticated_client, task, another_user):
    TaskShare.objects.create(task=task, shared_with=another_user, permission="edit")

    response = another_authenticated_client.get(detail_url(task.id))

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_shared_user_with_edit_can_edit_task(another_authenticated_client, task, another_user):
    TaskShare.objects.create(task=task, shared_with=another_user, permission="edit")

    response = another_authenticated_client.patch(detail_url(task.id), {"title": "Atualizada"})

    assert response.status_code == status.HTTP_200_OK
    task.refresh_from_db()
    assert task.title == "Atualizada"


@pytest.mark.django_db
def test_shared_user_with_edit_can_mark_task_completed(another_authenticated_client, task, another_user):
    TaskShare.objects.create(task=task, shared_with=another_user, permission="edit")

    response = another_authenticated_client.patch(detail_url(task.id), {"completed": True})

    assert response.status_code == status.HTTP_200_OK
    task.refresh_from_db()
    assert task.completed is True


@pytest.mark.django_db
def test_shared_user_with_read_cannot_delete_task(another_authenticated_client, task, another_user):
    TaskShare.objects.create(task=task, shared_with=another_user, permission="read")

    response = another_authenticated_client.delete(detail_url(task.id))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert Task.objects.filter(id=task.id).exists()


@pytest.mark.django_db
def test_shared_user_with_edit_cannot_delete_task(another_authenticated_client, task, another_user):
    TaskShare.objects.create(task=task, shared_with=another_user, permission="edit")

    response = another_authenticated_client.delete(detail_url(task.id))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert Task.objects.filter(id=task.id).exists()


@pytest.mark.django_db
def test_unrelated_user_cannot_view_task(third_authenticated_client, task):
    response = third_authenticated_client.get(detail_url(task.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_owner_retains_full_access_to_shared_task(authenticated_client, task, another_user):
    TaskShare.objects.create(task=task, shared_with=another_user, permission="read")

    response = authenticated_client.patch(detail_url(task.id), {"title": "Editada pelo dono"})

    assert response.status_code == status.HTTP_200_OK
