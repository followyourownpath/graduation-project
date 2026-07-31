from app import create_app
from app.config import TestConfig
from app.services.auth import AuthenticationError


class FakeAuthService:
    def __init__(self, identity=None, error=None):
        self.identity = identity
        self.error = error
        self.received_token = None

    def authenticate_staff(self, access_token):
        self.received_token = access_token
        if self.error:
            raise self.error
        return self.identity


def _client_for(service):
    return create_app(TestConfig, auth_service=service).test_client()


def test_me_requires_bearer_token(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "bearer_token_required"


def test_me_rejects_non_bearer_authorization(client):
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Basic credentials"}
    )

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "bearer_token_required"


def test_demo_bypass_environment_variable_cannot_disable_authentication(client, monkeypatch):
    monkeypatch.setenv("AUTH_DEMO_BYPASS", "true")

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "bearer_token_required"


def test_me_returns_authenticated_active_staff():
    identity = {
        "user": {"id": "user-id", "email": "staff@example.test"},
        "staff_profile": {
            "user_id": "user-id",
            "full_name": "Test Staff",
            "role": "analyst",
            "is_active": True,
        },
    }
    service = FakeAuthService(identity=identity)
    client = _client_for(service)

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    assert response.get_json() == identity
    assert service.received_token == "test-token"


def test_me_returns_authentication_service_error():
    service = FakeAuthService(
        error=AuthenticationError(
            "staff_inactive", "This staff account is inactive.", 403
        )
    )
    client = _client_for(service)

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "staff_inactive"
