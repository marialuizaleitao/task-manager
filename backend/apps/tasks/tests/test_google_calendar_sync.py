"""Verifica que TaskViewSet aciona apps.integrations.sync.sync_task nos
pontos certos — sem importar google_calendar diretamente. O comportamento
best-effort do próprio sync_task (nunca propagar falha do provedor) é
responsabilidade de apps.integrations.tests.test_sync, não deste módulo.
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
def mock_sync_task(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr(tasks_views.integrations_sync, "sync_task", mock)
    # notify_task é uma preocupação separada (ver test_telegram_notifications.py) —
    # isolada aqui para que estes testes verifiquem apenas o roteamento de sync_task.
    monkeypatch.setattr(tasks_views.integrations_sync, "notify_task", MagicMock())
    return mock


@pytest.mark.django_db
def test_create_task_triggers_sync_create(authenticated_client, mock_sync_task):
    response = authenticated_client.post(LIST_URL, {"title": "Revisar contrato"})

    assert response.status_code == status.HTTP_201_CREATED
    task = Task.objects.get(id=response.data["id"])
    mock_sync_task.assert_called_once_with(task, tasks_views.integrations_sync.CREATE)


@pytest.mark.django_db
def test_update_task_triggers_sync_update(authenticated_client, user, mock_sync_task):
    task = Task.objects.create(owner=user, title="Tarefa")
    mock_sync_task.reset_mock()

    response = authenticated_client.patch(detail_url(task.id), {"title": "Tarefa atualizada"})

    assert response.status_code == status.HTTP_200_OK
    mock_sync_task.assert_called_once_with(task, tasks_views.integrations_sync.UPDATE)


@pytest.mark.django_db
def test_delete_task_triggers_sync_delete_before_removal(authenticated_client, user, mock_sync_task):
    task = Task.objects.create(owner=user, title="Tarefa")
    task_id = task.id
    # Django zera instance.pk após instance.delete() — capturamos o id
    # dentro do side_effect, no momento exato da chamada, para provar que
    # sync_task recebeu a tarefa ainda com pk válido (ou seja, antes do
    # delete efetivo).
    captured = {}

    def _capture(synced_task, action):
        captured["id"] = synced_task.id
        captured["action"] = action

    mock_sync_task.side_effect = _capture

    response = authenticated_client.delete(detail_url(task_id))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert captured["id"] == task_id
    assert captured["action"] == tasks_views.integrations_sync.DELETE
    assert not Task.objects.filter(id=task_id).exists()
