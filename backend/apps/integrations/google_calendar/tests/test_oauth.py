import httpx
import pytest
from django.core import signing
from django.utils import timezone

from apps.integrations.exceptions import AuthenticationExpiredError, ExternalServiceError
from apps.integrations.google_calendar import oauth


def _json_response(status_code, payload):
    return httpx.Response(status_code, json=payload, request=httpx.Request("POST", "https://example.com"))


def test_build_authorization_url_contains_expected_params():
    url = oauth.build_authorization_url(user_id=42)

    assert url.startswith(oauth.AUTHORIZATION_ENDPOINT)
    assert "access_type=offline" in url
    assert "prompt=consent" in url
    assert "scope=" in url
    assert "state=" in url


def test_resolve_user_id_from_state_round_trip():
    state = signing.dumps({"user_id": 42}, salt=oauth._STATE_SALT)

    assert oauth.resolve_user_id_from_state(state) == 42


def test_resolve_user_id_from_state_rejects_invalid_signature():
    with pytest.raises(AuthenticationExpiredError):
        oauth.resolve_user_id_from_state("not-a-valid-state")


def test_exchange_code_for_tokens_success(monkeypatch):
    payload = {"access_token": "at", "refresh_token": "rt", "expires_in": 3600}
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _json_response(200, payload))

    token = oauth.exchange_code_for_tokens("auth-code")

    assert token.access_token == "at"
    assert token.refresh_token == "rt"
    assert token.expires_at > timezone.now()


def test_exchange_code_for_tokens_without_refresh_token_raises(monkeypatch):
    payload = {"access_token": "at", "expires_in": 3600}
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _json_response(200, payload))

    with pytest.raises(AuthenticationExpiredError):
        oauth.exchange_code_for_tokens("auth-code")


def test_token_request_handles_invalid_grant(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _json_response(400, {"error": "invalid_grant"}))

    with pytest.raises(AuthenticationExpiredError):
        oauth.refresh_access_token("stale-refresh-token")


def test_token_request_handles_generic_http_error(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _json_response(500, {"error": "server_error"}))

    with pytest.raises(ExternalServiceError):
        oauth.refresh_access_token("refresh-token")


def test_token_request_handles_timeout(monkeypatch):
    def _raise(*args, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "post", _raise)

    with pytest.raises(ExternalServiceError):
        oauth.refresh_access_token("refresh-token")


def test_token_request_handles_network_error(monkeypatch):
    def _raise(*args, **kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "post", _raise)

    with pytest.raises(ExternalServiceError):
        oauth.refresh_access_token("refresh-token")


def test_token_request_handles_invalid_json_response(monkeypatch):
    response = httpx.Response(200, content=b"not-json", request=httpx.Request("POST", "https://example.com"))
    monkeypatch.setattr(httpx, "post", lambda *a, **k: response)

    with pytest.raises(ExternalServiceError):
        oauth.refresh_access_token("refresh-token")


def test_refresh_access_token_reuses_old_token_when_not_reissued(monkeypatch):
    payload = {"access_token": "new-at", "expires_in": 3600}
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _json_response(200, payload))

    token = oauth.refresh_access_token("old-refresh-token")

    assert token.refresh_token == "old-refresh-token"


def test_revoke_token_never_raises_on_failure(monkeypatch):
    def _raise(*args, **kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "post", _raise)

    oauth.revoke_token("some-token")
