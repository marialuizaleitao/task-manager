import datetime

import pytest
from django.urls import reverse
from rest_framework import status

from apps.tasks.models import Task

LIST_URL = reverse("tasks:task-list")


@pytest.mark.django_db
def test_search_matches_title(authenticated_client, user):
    Task.objects.create(owner=user, title="Comprar leite")
    Task.objects.create(owner=user, title="Estudar Django")

    response = authenticated_client.get(LIST_URL, {"search": "leite"})

    titles = [item["title"] for item in response.data["results"]]
    assert titles == ["Comprar leite"]


@pytest.mark.django_db
def test_search_matches_description(authenticated_client, user):
    Task.objects.create(owner=user, title="Tarefa A", description="revisar contrato")
    Task.objects.create(owner=user, title="Tarefa B", description="outra coisa")

    response = authenticated_client.get(LIST_URL, {"search": "contrato"})

    titles = [item["title"] for item in response.data["results"]]
    assert titles == ["Tarefa A"]


@pytest.mark.django_db
def test_search_is_case_insensitive(authenticated_client, user):
    Task.objects.create(owner=user, title="Estudar DJANGO")

    response = authenticated_client.get(LIST_URL, {"search": "django"})

    assert len(response.data["results"]) == 1


@pytest.mark.django_db
def test_search_only_returns_own_tasks(authenticated_client, user, another_user):
    Task.objects.create(owner=user, title="Relatório mensal")
    Task.objects.create(owner=another_user, title="Relatório mensal")

    response = authenticated_client.get(LIST_URL, {"search": "relatório"})

    assert len(response.data["results"]) == 1


@pytest.mark.django_db
def test_ordering_by_title_ascending(authenticated_client, user):
    Task.objects.create(owner=user, title="Zebra")
    Task.objects.create(owner=user, title="Abacaxi")

    response = authenticated_client.get(LIST_URL, {"ordering": "title"})

    titles = [item["title"] for item in response.data["results"]]
    assert titles == ["Abacaxi", "Zebra"]


@pytest.mark.django_db
def test_ordering_by_title_descending(authenticated_client, user):
    Task.objects.create(owner=user, title="Zebra")
    Task.objects.create(owner=user, title="Abacaxi")

    response = authenticated_client.get(LIST_URL, {"ordering": "-title"})

    titles = [item["title"] for item in response.data["results"]]
    assert titles == ["Zebra", "Abacaxi"]


@pytest.mark.django_db
def test_ordering_by_due_date(authenticated_client, user):
    Task.objects.create(owner=user, title="Depois", due_date=datetime.date(2026, 6, 1))
    Task.objects.create(owner=user, title="Antes", due_date=datetime.date(2026, 1, 1))

    response = authenticated_client.get(LIST_URL, {"ordering": "due_date"})

    titles = [item["title"] for item in response.data["results"]]
    assert titles == ["Antes", "Depois"]


@pytest.mark.django_db
def test_ordering_by_updated_at(authenticated_client, user):
    first = Task.objects.create(owner=user, title="Primeira")
    Task.objects.create(owner=user, title="Segunda")

    first.title = "Primeira editada"
    first.save()

    response = authenticated_client.get(LIST_URL, {"ordering": "-updated_at"})

    assert response.data["results"][0]["title"] == "Primeira editada"


@pytest.mark.django_db
def test_default_ordering_is_created_at_descending(authenticated_client, user):
    Task.objects.create(owner=user, title="Mais antiga")
    Task.objects.create(owner=user, title="Mais nova")

    response = authenticated_client.get(LIST_URL)

    titles = [item["title"] for item in response.data["results"]]
    assert titles == ["Mais nova", "Mais antiga"]


@pytest.mark.django_db
def test_unsafe_ordering_field_is_ignored(authenticated_client, user):
    Task.objects.create(owner=user, title="Mais antiga")
    Task.objects.create(owner=user, title="Mais nova")

    response = authenticated_client.get(LIST_URL, {"ordering": "owner_id"})

    assert response.status_code == status.HTTP_200_OK
    titles = [item["title"] for item in response.data["results"]]
    # Campo não incluído em ordering_fields é ignorado silenciosamente: cai
    # na ordenação padrão (-created_at), não gera erro nem expõe owner_id.
    assert titles == ["Mais nova", "Mais antiga"]
