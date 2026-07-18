import pytest
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse
from rest_framework import status

from apps.sharing.models import TaskShare
from apps.tasks.models import Task

SHARED_TASKS_URL = reverse("sharing:shared-task-list")


@pytest.mark.django_db
def test_shared_tasks_listing_requires_authentication(api_client):
    response = api_client.get(SHARED_TASKS_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_lists_only_tasks_shared_with_me(another_authenticated_client, user, another_user):
    shared_task = Task.objects.create(owner=user, title="Compartilhada comigo")
    TaskShare.objects.create(task=shared_task, shared_with=another_user, permission="edit")
    Task.objects.create(owner=user, title="Não compartilhada")
    Task.objects.create(owner=another_user, title="Minha própria tarefa")

    response = another_authenticated_client.get(SHARED_TASKS_URL)

    assert response.status_code == status.HTTP_200_OK
    titles = [item["title"] for item in response.data["results"]]
    assert titles == ["Compartilhada comigo"]


@pytest.mark.django_db
def test_shared_task_includes_owner_and_permission(another_authenticated_client, user, another_user):
    shared_task = Task.objects.create(owner=user, title="Compartilhada")
    TaskShare.objects.create(task=shared_task, shared_with=another_user, permission="edit")

    response = another_authenticated_client.get(SHARED_TASKS_URL)

    item = response.data["results"][0]
    assert item["owner"]["email"] == user.email
    assert item["permission"] == "edit"


@pytest.mark.django_db
def test_shared_tasks_listing_avoids_n_plus_one_queries(another_authenticated_client, user, another_user):
    for i in range(10):
        task = Task.objects.create(owner=user, title=f"Tarefa {i}")
        TaskShare.objects.create(task=task, shared_with=another_user, permission="read")

    with CaptureQueriesContext(connection) as context:
        response = another_authenticated_client.get(SHARED_TASKS_URL)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]) == 10
    # Uma query para as tarefas (com select_related de category/owner) e uma
    # segunda para o prefetch de shares — sem o Prefetch, cada item da lista
    # dispararia uma consulta própria para calcular "permission" (N+1).
    assert len(context.captured_queries) <= 4
