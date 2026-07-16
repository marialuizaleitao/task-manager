import pytest

from apps.categories.models import Category

from .models import TelegramConnection


@pytest.fixture
def category_factory(user):
    def _factory(**kwargs):
        kwargs.setdefault("owner", user)
        kwargs.setdefault("name", "Categoria de teste")
        kwargs.setdefault("color", "#1A2B3C")
        return Category.objects.create(**kwargs)

    return _factory


@pytest.fixture
def telegram_connection(user):
    return TelegramConnection.objects.create(
        owner=user,
        telegram_chat_id="123456789",
        telegram_username="maria_dev",
        enabled=True,
    )


@pytest.fixture
def pending_telegram_connection(user):
    return TelegramConnection.objects.create(
        owner=user,
        linking_code="abc123linkcode",
    )
