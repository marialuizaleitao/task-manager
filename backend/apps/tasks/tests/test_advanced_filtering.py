import datetime

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.tasks.models import Task

LIST_URL = reverse("tasks:task-list")


@pytest.mark.django_db
def test_filter_by_due_date_after(authenticated_client, user):
    Task.objects.create(owner=user, title="Cedo", due_date=datetime.date(2026, 1, 1))
    Task.objects.create(owner=user, title="Tarde", due_date=datetime.date(2026, 6, 1))

    response = authenticated_client.get(LIST_URL, {"due_date_after": "2026-03-01"})

    titles = [item["title"] for item in response.data["results"]]
    assert titles == ["Tarde"]


@pytest.mark.django_db
def test_filter_by_due_date_before(authenticated_client, user):
    Task.objects.create(owner=user, title="Cedo", due_date=datetime.date(2026, 1, 1))
    Task.objects.create(owner=user, title="Tarde", due_date=datetime.date(2026, 6, 1))

    response = authenticated_client.get(LIST_URL, {"due_date_before": "2026-03-01"})

    titles = [item["title"] for item in response.data["results"]]
    assert titles == ["Cedo"]


@pytest.mark.django_db
def test_filter_by_due_date_range(authenticated_client, user):
    Task.objects.create(owner=user, title="Fora", due_date=datetime.date(2026, 1, 1))
    Task.objects.create(owner=user, title="Dentro", due_date=datetime.date(2026, 3, 15))
    Task.objects.create(owner=user, title="Depois", due_date=datetime.date(2026, 8, 1))

    response = authenticated_client.get(
        LIST_URL, {"due_date_after": "2026-03-01", "due_date_before": "2026-04-01"}
    )

    titles = [item["title"] for item in response.data["results"]]
    assert titles == ["Dentro"]


@pytest.mark.django_db
def test_filter_by_created_after(authenticated_client, user):
    old_task = Task.objects.create(owner=user, title="Antiga")
    Task.objects.filter(id=old_task.id).update(created_at=timezone.now() - datetime.timedelta(days=10))
    Task.objects.create(owner=user, title="Nova")

    boundary = (timezone.now() - datetime.timedelta(days=5)).date()
    response = authenticated_client.get(LIST_URL, {"created_after": boundary.isoformat()})

    titles = [item["title"] for item in response.data["results"]]
    assert titles == ["Nova"]


@pytest.mark.django_db
def test_filter_by_created_before(authenticated_client, user):
    old_task = Task.objects.create(owner=user, title="Antiga")
    Task.objects.filter(id=old_task.id).update(created_at=timezone.now() - datetime.timedelta(days=10))
    Task.objects.create(owner=user, title="Nova")

    boundary = (timezone.now() - datetime.timedelta(days=5)).date()
    response = authenticated_client.get(LIST_URL, {"created_before": boundary.isoformat()})

    titles = [item["title"] for item in response.data["results"]]
    assert titles == ["Antiga"]


@pytest.mark.django_db
def test_combining_category_completed_search_and_ordering(authenticated_client, user):
    from apps.categories.models import Category

    category = Category.objects.create(owner=user, name="Trabalho", color="#123456")
    Task.objects.create(
        owner=user, title="Relatório A", category=category, completed=True, due_date=datetime.date(2026, 5, 1)
    )
    Task.objects.create(
        owner=user, title="Relatório B", category=category, completed=True, due_date=datetime.date(2026, 2, 1)
    )
    Task.objects.create(owner=user, title="Relatório C", category=category, completed=False)

    response = authenticated_client.get(
        LIST_URL,
        {"category": category.id, "completed": "true", "search": "relatório", "ordering": "due_date"},
    )

    titles = [item["title"] for item in response.data["results"]]
    assert titles == ["Relatório B", "Relatório A"]


@pytest.mark.django_db
def test_invalid_category_returns_empty_result_not_error(authenticated_client, user):
    Task.objects.create(owner=user, title="Tarefa")

    response = authenticated_client.get(LIST_URL, {"category": "abc"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["results"] == []


@pytest.mark.django_db
def test_filters_never_leak_another_users_tasks(authenticated_client, user, another_user):
    from apps.categories.models import Category

    foreign_category = Category.objects.create(owner=another_user, name="Alheia", color="#000000")
    Task.objects.create(owner=another_user, title="Tarefa alheia", category=foreign_category)
    Task.objects.create(owner=user, title="Minha tarefa")

    response = authenticated_client.get(LIST_URL, {"search": "tarefa"})

    titles = [item["title"] for item in response.data["results"]]
    assert titles == ["Minha tarefa"]
