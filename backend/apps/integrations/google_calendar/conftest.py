from datetime import timedelta

import pytest
from django.utils import timezone

from .models import GoogleCalendarCredential


@pytest.fixture
def connected_credential(user):
    return GoogleCalendarCredential.objects.create(
        owner=user,
        access_token="valid-access-token",
        refresh_token="valid-refresh-token",
        expires_at=timezone.now() + timedelta(hours=1),
        enabled=True,
    )


@pytest.fixture
def expired_credential(user):
    return GoogleCalendarCredential.objects.create(
        owner=user,
        access_token="expired-access-token",
        refresh_token="valid-refresh-token",
        expires_at=timezone.now() - timedelta(minutes=5),
        enabled=True,
    )
