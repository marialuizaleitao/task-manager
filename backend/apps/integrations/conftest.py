import pytest

from apps.tasks.models import Task


@pytest.fixture
def task_factory(user):
    """Cria Tasks persistidas para os testes de sincronização.

    Compartilhado entre os testes de apps.integrations e
    apps.integrations.google_calendar (pytest aplica conftest.py também às
    subpastas) — GoogleCalendarEventLink exige uma Task com pk real (FK),
    então o factory sempre persiste no banco.
    """

    def _factory(**kwargs):
        kwargs.setdefault("owner", user)
        kwargs.setdefault("title", "Tarefa de teste")
        return Task.objects.create(**kwargs)

    return _factory
