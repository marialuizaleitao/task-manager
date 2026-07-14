import pytest
from django.urls import reverse
from rest_framework import status

from apps.categories.models import Category

LIST_URL = reverse("categories:category-list")


@pytest.mark.django_db
def test_list_is_paginated(authenticated_client, user):
    for index in range(15):
        Category.objects.create(owner=user, name=f"Categoria {index:02d}", color="#111111")

    response = authenticated_client.get(LIST_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 15
    assert len(response.data["results"]) == 10
    assert response.data["next"] is not None


@pytest.mark.django_db
def test_filter_by_name(authenticated_client, user):
    Category.objects.create(owner=user, name="Trabalho", color="#111111")
    Category.objects.create(owner=user, name="Estudos", color="#222222")

    response = authenticated_client.get(LIST_URL, {"name": "trab"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == "Trabalho"
