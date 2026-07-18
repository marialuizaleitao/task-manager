"""Testes das views de infraestrutura (config/views.py).

Um único módulo de teste, não um pacote tests/, porque config/ concentra
apenas a view de health check — sem volume ou variação de cenários que
justifique a mesma estrutura de subpastas usada em apps/.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_check_returns_ok_without_authentication():
    response = APIClient().get(reverse("health-check"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {"status": "ok"}
