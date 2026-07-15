import pytest
from django.urls import reverse
from rest_framework import status

from apps.categories.models import Category
from apps.tasks.models import Task

LIST_URL = reverse("tasks:task-list")


@pytest.mark.django_db
def test_title_is_required(authenticated_client):
    response = authenticated_client.post(LIST_URL, {})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "title" in response.data


@pytest.mark.django_db
def test_cannot_use_category_from_another_user(authenticated_client, another_user):
    foreign_category = Category.objects.create(owner=another_user, name="Alheia", color="#111111")

    response = authenticated_client.post(
        LIST_URL, {"title": "Tarefa", "category": foreign_category.id}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "category" in response.data
    assert not Task.objects.filter(title="Tarefa").exists()


@pytest.mark.django_db
def test_due_date_must_be_a_valid_date(authenticated_client):
    response = authenticated_client.post(
        LIST_URL, {"title": "Tarefa", "due_date": "data-invalida"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "due_date" in response.data


@pytest.mark.django_db
def test_completed_must_be_boolean(authenticated_client):
    response = authenticated_client.post(
        LIST_URL, {"title": "Tarefa", "completed": "não-é-booleano"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "completed" in response.data


@pytest.mark.django_db
def test_past_due_date_is_allowed(authenticated_client):
    response = authenticated_client.post(
        LIST_URL, {"title": "Tarefa atrasada", "due_date": "2020-01-01"}
    )

    assert response.status_code == status.HTTP_201_CREATED
