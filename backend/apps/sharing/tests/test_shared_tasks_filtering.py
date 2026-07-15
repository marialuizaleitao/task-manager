import datetime

import pytest
from django.urls import reverse

from apps.sharing.models import TaskShare
from apps.tasks.models import Task

SHARED_TASKS_URL = reverse("sharing:shared-task-list")


@pytest.mark.django_db
def test_search_shared_tasks(another_authenticated_client, user, another_user):
    task = Task.objects.create(owner=user, title="Relatório financeiro")
    TaskShare.objects.create(task=task, shared_with=another_user, permission="read")
    other = Task.objects.create(owner=user, title="Outra tarefa")
    TaskShare.objects.create(task=other, shared_with=another_user, permission="read")

    response = another_authenticated_client.get(SHARED_TASKS_URL, {"search": "financeiro"})

    titles = [item["title"] for item in response.data["results"]]
    assert titles == ["Relatório financeiro"]


@pytest.mark.django_db
def test_filter_shared_tasks_by_completed(another_authenticated_client, user, another_user):
    done = Task.objects.create(owner=user, title="Feita", completed=True)
    TaskShare.objects.create(task=done, shared_with=another_user, permission="read")
    pending = Task.objects.create(owner=user, title="Pendente", completed=False)
    TaskShare.objects.create(task=pending, shared_with=another_user, permission="read")

    response = another_authenticated_client.get(SHARED_TASKS_URL, {"completed": "true"})

    titles = [item["title"] for item in response.data["results"]]
    assert titles == ["Feita"]


@pytest.mark.django_db
def test_ordering_shared_tasks_by_due_date(another_authenticated_client, user, another_user):
    later = Task.objects.create(owner=user, title="Depois", due_date=datetime.date(2026, 6, 1))
    TaskShare.objects.create(task=later, shared_with=another_user, permission="read")
    earlier = Task.objects.create(owner=user, title="Antes", due_date=datetime.date(2026, 1, 1))
    TaskShare.objects.create(task=earlier, shared_with=another_user, permission="read")

    response = another_authenticated_client.get(SHARED_TASKS_URL, {"ordering": "due_date"})

    titles = [item["title"] for item in response.data["results"]]
    assert titles == ["Antes", "Depois"]


@pytest.mark.django_db
def test_shared_tasks_search_does_not_leak_unshared_tasks(another_authenticated_client, user, another_user):
    Task.objects.create(owner=user, title="Relatório não compartilhado")
    shared = Task.objects.create(owner=user, title="Relatório compartilhado")
    TaskShare.objects.create(task=shared, shared_with=another_user, permission="read")

    response = another_authenticated_client.get(SHARED_TASKS_URL, {"search": "relatório"})

    titles = [item["title"] for item in response.data["results"]]
    assert titles == ["Relatório compartilhado"]
