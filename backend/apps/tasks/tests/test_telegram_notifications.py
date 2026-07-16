"""Verifica que TaskViewSet aciona apps.integrations.sync.notify_task nos
pontos certos — sem importar telegram diretamente. A decisão de quando um
provedor efetivamente envia uma mensagem (ex.: só notificar criação se
houver due_date) é responsabilidade do provedor, coberta em
apps.integrations.telegram.tests.test_service.
"""
from unittest.mock import MagicMock

import pytest
from django.urls import reverse
from rest_framework import status

from apps.tasks import views as tasks_views
from apps.tasks.models import Task

LIST_URL = reverse("tasks:task-list")


def detail_url(task_id: int) -> str:
    return reverse("tasks:task-detail", args=[task_id])


@pytest.fixture
def mock_notify_task(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr(tasks_views.integrations_sync, "notify_task", mock)
    monkeypatch.setattr(tasks_views.integrations_sync, "sync_task", MagicMock())
    return mock


@pytest.mark.django_db
def test_create_task_triggers_created_notification(authenticated_client, mock_notify_task):
    response = authenticated_client.post(LIST_URL, {"title": "Enviar documentação"})

    assert response.status_code == status.HTTP_201_CREATED
    task = Task.objects.get(id=response.data["id"])
    mock_notify_task.assert_called_once_with(task, tasks_views.integrations_sync.TaskEvent.CREATED)


@pytest.mark.django_db
def test_update_without_completing_does_not_trigger_completed_notification(
    authenticated_client, user, mock_notify_task
):
    task = Task.objects.create(owner=user, title="Tarefa")
    mock_notify_task.reset_mock()

    response = authenticated_client.patch(detail_url(task.id), {"title": "Tarefa atualizada"})

    assert response.status_code == status.HTTP_200_OK
    mock_notify_task.assert_not_called()


@pytest.mark.django_db
def test_marking_task_completed_triggers_completed_notification(authenticated_client, user, mock_notify_task):
    task = Task.objects.create(owner=user, title="Tarefa", completed=False)
    mock_notify_task.reset_mock()

    response = authenticated_client.patch(detail_url(task.id), {"completed": True})

    assert response.status_code == status.HTTP_200_OK
    mock_notify_task.assert_called_once_with(task, tasks_views.integrations_sync.TaskEvent.COMPLETED)


@pytest.mark.django_db
def test_updating_already_completed_task_does_not_retrigger_notification(
    authenticated_client, user, mock_notify_task
):
    task = Task.objects.create(owner=user, title="Tarefa", completed=True)
    mock_notify_task.reset_mock()

    response = authenticated_client.patch(detail_url(task.id), {"title": "Ajuste de título"})

    assert response.status_code == status.HTTP_200_OK
    mock_notify_task.assert_not_called()


@pytest.mark.django_db
def test_deleting_task_does_not_trigger_notification(authenticated_client, user, mock_notify_task):
    task = Task.objects.create(owner=user, title="Tarefa")
    mock_notify_task.reset_mock()

    response = authenticated_client.delete(detail_url(task.id))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_notify_task.assert_not_called()
