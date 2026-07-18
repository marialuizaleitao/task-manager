from datetime import date

import httpx
import pytest

from apps.integrations.exceptions import AuthenticationExpiredError, ExternalServiceError
from apps.integrations.google_calendar.client import GoogleCalendarClient


def _response(status_code, json_body=None, empty=False):
    if empty:
        return httpx.Response(status_code, request=httpx.Request("DELETE", "https://example.com"))
    return httpx.Response(status_code, json=json_body, request=httpx.Request("POST", "https://example.com"))


@pytest.fixture
def task_with_due_date(task_factory):
    return task_factory(due_date=date(2026, 8, 10), title="Revisar contrato")


@pytest.mark.django_db
def test_create_event_returns_event_id(monkeypatch, task_with_due_date):
    monkeypatch.setattr(httpx.Client, "request", lambda self, *a, **k: _response(200, {"id": "evt-1"}))

    with GoogleCalendarClient("valid-token") as client:
        event_id = client.create_event(task_with_due_date)

    assert event_id == "evt-1"


@pytest.mark.django_db
def test_create_event_sends_all_day_event_with_exclusive_end(monkeypatch, task_with_due_date):
    captured = {}

    def fake_request(self, method, path, json=None):
        captured["method"] = method
        captured["path"] = path
        captured["json"] = json
        return _response(200, {"id": "evt-1"})

    monkeypatch.setattr(httpx.Client, "request", fake_request)

    with GoogleCalendarClient("valid-token") as client:
        client.create_event(task_with_due_date)

    assert captured["method"] == "POST"
    assert captured["json"]["start"]["date"] == "2026-08-10"
    assert captured["json"]["end"]["date"] == "2026-08-11"


@pytest.mark.django_db
def test_update_event_returns_event_id(monkeypatch, task_with_due_date):
    monkeypatch.setattr(httpx.Client, "request", lambda self, *a, **k: _response(200, {"id": "evt-1"}))

    with GoogleCalendarClient("valid-token") as client:
        event_id = client.update_event(task_with_due_date, "evt-1")

    assert event_id == "evt-1"


@pytest.mark.django_db
def test_delete_event_succeeds_with_empty_response(monkeypatch, task_with_due_date):
    monkeypatch.setattr(httpx.Client, "request", lambda self, *a, **k: _response(204, empty=True))

    with GoogleCalendarClient("valid-token") as client:
        client.delete_event("evt-1")


@pytest.mark.django_db
def test_request_raises_authentication_expired_on_401(monkeypatch, task_with_due_date):
    monkeypatch.setattr(httpx.Client, "request", lambda self, *a, **k: _response(401, {"error": "unauthorized"}))

    with GoogleCalendarClient("expired-token") as client:
        with pytest.raises(AuthenticationExpiredError):
            client.create_event(task_with_due_date)


@pytest.mark.django_db
def test_request_raises_external_service_error_on_5xx(monkeypatch, task_with_due_date):
    monkeypatch.setattr(httpx.Client, "request", lambda self, *a, **k: _response(500, {"error": "server_error"}))

    with GoogleCalendarClient("valid-token") as client:
        with pytest.raises(ExternalServiceError):
            client.create_event(task_with_due_date)


@pytest.mark.django_db
def test_request_raises_external_service_error_on_timeout(monkeypatch, task_with_due_date):
    def _raise(self, *a, **k):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx.Client, "request", _raise)

    with GoogleCalendarClient("valid-token") as client:
        with pytest.raises(ExternalServiceError):
            client.create_event(task_with_due_date)


@pytest.mark.django_db
def test_request_raises_external_service_error_on_invalid_json(monkeypatch, task_with_due_date):
    response = httpx.Response(200, content=b"not-json", request=httpx.Request("POST", "https://example.com"))
    monkeypatch.setattr(httpx.Client, "request", lambda self, *a, **k: response)

    with GoogleCalendarClient("valid-token") as client:
        with pytest.raises(ExternalServiceError):
            client.create_event(task_with_due_date)
