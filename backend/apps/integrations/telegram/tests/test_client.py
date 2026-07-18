import httpx
import pytest

from apps.integrations.exceptions import AuthenticationExpiredError, ExternalServiceError
from apps.integrations.telegram.client import ChatUnreachableError, TelegramClient


def _ok_response(result):
    return httpx.Response(200, json={"ok": True, "result": result}, request=httpx.Request("GET", "https://example.com"))


def _error_response(status_code, error_code, description):
    return httpx.Response(
        status_code,
        json={"ok": False, "error_code": error_code, "description": description},
        request=httpx.Request("GET", "https://example.com"),
    )


def test_get_me_returns_bot_data(monkeypatch):
    monkeypatch.setattr(
        httpx.Client, "request", lambda self, *a, **k: _ok_response({"id": 1, "username": "task_manager_bot"})
    )

    with TelegramClient("fake-token") as client:
        bot = client.get_me()

    assert bot["username"] == "task_manager_bot"


def test_send_message_returns_result(monkeypatch):
    captured = {}

    def fake_request(self, method, path, json=None, params=None):
        captured["method"] = method
        captured["path"] = path
        captured["json"] = json
        return _ok_response({"message_id": 42})

    monkeypatch.setattr(httpx.Client, "request", fake_request)

    with TelegramClient("fake-token") as client:
        result = client.send_message("123", "Olá")

    assert result["message_id"] == 42
    assert captured["method"] == "POST"
    assert captured["path"] == "/sendMessage"
    assert captured["json"] == {"chat_id": "123", "text": "Olá"}


def test_get_updates_sends_timeout_zero_and_no_offset_by_default(monkeypatch):
    captured = {}

    def fake_request(self, method, path, json=None, params=None):
        captured["params"] = params
        return _ok_response([])

    monkeypatch.setattr(httpx.Client, "request", fake_request)

    with TelegramClient("fake-token") as client:
        client.get_updates()

    assert captured["params"] == {"timeout": 0}


def test_get_updates_includes_offset_when_given(monkeypatch):
    captured = {}

    def fake_request(self, method, path, json=None, params=None):
        captured["params"] = params
        return _ok_response([])

    monkeypatch.setattr(httpx.Client, "request", fake_request)

    with TelegramClient("fake-token") as client:
        client.get_updates(offset=10)

    assert captured["params"] == {"timeout": 0, "offset": 10}


def test_request_raises_authentication_expired_on_401(monkeypatch):
    monkeypatch.setattr(
        httpx.Client, "request", lambda self, *a, **k: _error_response(401, 401, "Unauthorized")
    )

    with TelegramClient("invalid-token") as client:
        with pytest.raises(AuthenticationExpiredError):
            client.get_me()


def test_request_raises_chat_unreachable_when_bot_blocked(monkeypatch):
    monkeypatch.setattr(
        httpx.Client,
        "request",
        lambda self, *a, **k: _error_response(403, 403, "Forbidden: bot was blocked by the user"),
    )

    with TelegramClient("fake-token") as client:
        with pytest.raises(ChatUnreachableError):
            client.send_message("123", "Olá")


def test_request_raises_chat_unreachable_when_chat_not_found(monkeypatch):
    monkeypatch.setattr(
        httpx.Client,
        "request",
        lambda self, *a, **k: _error_response(400, 400, "Bad Request: chat not found"),
    )

    with TelegramClient("fake-token") as client:
        with pytest.raises(ChatUnreachableError):
            client.send_message("999", "Olá")


def test_request_raises_external_service_error_on_generic_error(monkeypatch):
    monkeypatch.setattr(
        httpx.Client,
        "request",
        lambda self, *a, **k: _error_response(429, 429, "Too Many Requests: retry later"),
    )

    with TelegramClient("fake-token") as client:
        with pytest.raises(ExternalServiceError):
            client.send_message("123", "Olá")


def test_request_raises_external_service_error_on_timeout(monkeypatch):
    def _raise(self, *a, **k):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx.Client, "request", _raise)

    with TelegramClient("fake-token") as client:
        with pytest.raises(ExternalServiceError):
            client.get_me()


def test_request_raises_external_service_error_on_network_error(monkeypatch):
    def _raise(self, *a, **k):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx.Client, "request", _raise)

    with TelegramClient("fake-token") as client:
        with pytest.raises(ExternalServiceError):
            client.get_me()


def test_request_raises_external_service_error_on_invalid_json(monkeypatch):
    response = httpx.Response(200, content=b"not-json", request=httpx.Request("GET", "https://example.com"))
    monkeypatch.setattr(httpx.Client, "request", lambda self, *a, **k: response)

    with TelegramClient("fake-token") as client:
        with pytest.raises(ExternalServiceError):
            client.get_me()
