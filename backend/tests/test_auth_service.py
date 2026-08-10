import requests
import pytest

from app.services.auth import AuthenticationError, SupabaseAuthService


class Response:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._payload = payload

    def json(self):
        return self._payload


def service():
    return SupabaseAuthService("https://example.supabase.co/", "publishable", 3)


def test_authenticate_staff_returns_active_profile(monkeypatch):
    responses = iter([
        Response(payload={"id": "user-1", "email": "staff@example.test"}),
        Response(payload=[{"user_id": "user-1", "role": "reviewer", "is_active": True}]),
    ])
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return next(responses)

    monkeypatch.setattr(requests, "get", fake_get)
    result = service().authenticate_staff("jwt")

    assert result["user"] == {"id": "user-1", "email": "staff@example.test"}
    assert result["staff_profile"]["role"] == "reviewer"
    assert calls[0][1]["headers"]["Authorization"] == "Bearer jwt"
    assert calls[1][1]["params"]["user_id"] == "eq.user-1"


def test_authentication_requires_configuration():
    with pytest.raises(AuthenticationError) as caught:
        SupabaseAuthService("", "").authenticate_staff("jwt")
    assert caught.value.code == "supabase_not_configured"
    assert caught.value.status == 503


@pytest.mark.parametrize(
    ("response", "code", "status"),
    [
        (Response(401, {}), "invalid_access_token", 401),
        (Response(500, {}), "authentication_service_error", 503),
        (Response(200, {}), "invalid_access_token", 401),
    ],
)
def test_user_lookup_errors(monkeypatch, response, code, status):
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: response)
    with pytest.raises(AuthenticationError) as caught:
        service().authenticate_staff("jwt")
    assert (caught.value.code, caught.value.status) == (code, status)


def test_user_lookup_network_error(monkeypatch):
    def fail(*args, **kwargs):
        raise requests.Timeout("timeout")

    monkeypatch.setattr(requests, "get", fail)
    with pytest.raises(AuthenticationError) as caught:
        service().authenticate_staff("jwt")
    assert caught.value.code == "authentication_service_unavailable"


@pytest.mark.parametrize(
    ("profile_response", "code", "status"),
    [
        (Response(403, {}), "staff_access_denied", 403),
        (Response(500, {}), "staff_profile_service_error", 503),
        (Response(200, []), "staff_profile_required", 403),
        (Response(200, [{"user_id": "user-1", "is_active": False}]), "staff_inactive", 403),
    ],
)
def test_staff_profile_errors(monkeypatch, profile_response, code, status):
    responses = iter([
        Response(payload={"id": "user-1", "email": "staff@example.test"}),
        profile_response,
    ])
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: next(responses))
    with pytest.raises(AuthenticationError) as caught:
        service().authenticate_staff("jwt")
    assert (caught.value.code, caught.value.status) == (code, status)


def test_staff_profile_network_error(monkeypatch):
    calls = 0

    def fake_get(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return Response(payload={"id": "user-1"})
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(requests, "get", fake_get)
    with pytest.raises(AuthenticationError) as caught:
        service().authenticate_staff("jwt")
    assert caught.value.code == "staff_profile_service_unavailable"
