import pytest
from django.urls import reverse
from rest_framework import status

from apps.categories.models import Category
from apps.tasks.models import Task

LIST_URL = reverse("tasks:task-list")


@pytest.mark.django_db
def test_list_is_paginated(authenticated_client, user):
    for index in range(15):
        Task.objects.create(owner=user, title=f"Tarefa {index:02d}")

    response = authenticated_client.get(LIST_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 15
    assert len(response.data["results"]) == 10
    assert response.data["next"] is not None


@pytest.mark.django_db
def test_filter_by_category(authenticated_client, user):
    work = Category.objects.create(owner=user, name="Trabalho", color="#111111")
    personal = Category.objects.create(owner=user, name="Pessoal", color="#222222")
    Task.objects.create(owner=user, title="Reunião", category=work)
    Task.objects.create(owner=user, title="Academia", category=personal)

    response = authenticated_client.get(LIST_URL, {"category": work.id})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["title"] == "Reunião"


@pytest.mark.django_db
def test_filter_tasks_without_category(authenticated_client, user):
    category = Category.objects.create(owner=user, name="Trabalho", color="#111111")
    Task.objects.create(owner=user, title="Com categoria", category=category)
    Task.objects.create(owner=user, title="Sem categoria")

    response = authenticated_client.get(LIST_URL, {"category": "none"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["title"] == "Sem categoria"


@pytest.mark.django_db
def test_filter_by_completed(authenticated_client, user):
    Task.objects.create(owner=user, title="Feita", completed=True)
    Task.objects.create(owner=user, title="Pendente", completed=False)

    response = authenticated_client.get(LIST_URL, {"completed": "true"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["title"] == "Feita"
