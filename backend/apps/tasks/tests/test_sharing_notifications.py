"""Verifica que TaskViewSet aciona apps.integrations.sync.notify_task_shared /
notify_task_shared_updated nos pontos certos — sem importar telegram
diretamente. Adicionado na Sprint 7.1 (canal de comunicação generalizado):
compartilhar uma tarefa e alterar uma tarefa compartilhada passaram a gerar
eventos de notificação, assim como criar/concluir uma tarefa já geravam
desde a Sprint 7.
"""
from unittest.mock import MagicMock

import pytest
from django.urls import reverse
from rest_framework import status

from apps.sharing.models import TaskShare
from apps.tasks import views as tasks_views
from apps.tasks.models import Task


def shares_url(task_id: int) -> str:
    return reverse("tasks:task-shares", args=[task_id])


def detail_url(task_id: int) -> str:
    return reverse("tasks:task-detail", args=[task_id])


@pytest.fixture
def mock_notify_task_shared(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr(tasks_views.integrations_sync, "notify_task_shared", mock)
    monkeypatch.setattr(tasks_views.integrations_sync, "sync_task", MagicMock())
    monkeypatch.setattr(tasks_views.integrations_sync, "notify_task", MagicMock())
    return mock


@pytest.fixture
def mock_notify_task_shared_updated(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr(tasks_views.integrations_sync, "notify_task_shared_updated", mock)
    monkeypatch.setattr(tasks_views.integrations_sync, "sync_task", MagicMock())
    monkeypatch.setattr(tasks_views.integrations_sync, "notify_task", MagicMock())
    return mock


@pytest.mark.django_db
def test_sharing_task_triggers_shared_notification(
    authenticated_client, user, another_user, mock_notify_task_shared
):
    task = Task.objects.create(owner=user, title="Enviar documentação")

    response = authenticated_client.post(
        shares_url(task.id), {"email": another_user.email, "permission": "read"}
    )

    assert response.status_code == status.HTTP_201_CREATED
    share = TaskShare.objects.get(task=task, shared_with=another_user)
    mock_notify_task_shared.assert_called_once_with(share)


@pytest.mark.django_db
def test_updating_shared_task_as_owner_triggers_shared_updated_notification(
    authenticated_client, user, another_user, mock_notify_task_shared_updated
):
    task = Task.objects.create(owner=user, title="Tarefa")
    TaskShare.objects.create(task=task, shared_with=another_user, permission="edit")
    mock_notify_task_shared_updated.reset_mock()

    response = authenticated_client.patch(detail_url(task.id), {"title": "Tarefa atualizada"})

    assert response.status_code == status.HTTP_200_OK
    mock_notify_task_shared_updated.assert_called_once_with(task, actor=user)


@pytest.mark.django_db
def test_updating_shared_task_as_collaborator_triggers_shared_updated_notification(
    another_authenticated_client, user, another_user, mock_notify_task_shared_updated
):
    task = Task.objects.create(owner=user, title="Tarefa")
    TaskShare.objects.create(task=task, shared_with=another_user, permission="edit")
    mock_notify_task_shared_updated.reset_mock()

    response = another_authenticated_client.patch(
        detail_url(task.id), {"title": "Ajustado pelo colaborador"}
    )

    assert response.status_code == status.HTTP_200_OK
    mock_notify_task_shared_updated.assert_called_once_with(task, actor=another_user)


@pytest.mark.django_db
def test_updating_unshared_task_does_not_trigger_shared_updated_notification(
    authenticated_client, user, mock_notify_task_shared_updated
):
    task = Task.objects.create(owner=user, title="Tarefa")

    response = authenticated_client.patch(detail_url(task.id), {"title": "Tarefa atualizada"})

    assert response.status_code == status.HTTP_200_OK
    mock_notify_task_shared_updated.assert_not_called()
