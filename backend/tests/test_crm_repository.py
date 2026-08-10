import pytest
import requests

from app.services.crm_repository import SupabaseCrmRepository
from app.services.intake import IntakeError


class Response:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


def repository():
    return SupabaseCrmRepository("https://db.example/", "secret", 4)


def test_request_uses_service_credentials(monkeypatch):
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return Response(payload=[])

    monkeypatch.setattr(requests, "request", fake_request)
    repository().get_pending_trackings()
    assert captured["headers"]["apikey"] == "secret"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["timeout"] == 4


def test_request_network_failure_is_normalised(monkeypatch):
    monkeypatch.setattr(requests, "request", lambda *args, **kwargs: (_ for _ in ()).throw(requests.Timeout("offline")))
    with pytest.raises(IntakeError) as caught:
        repository().get_pending_trackings()
    assert caught.value.code == "supabase_unavailable"


def test_tracking_queries_handle_success_and_failure(monkeypatch):
    repo = repository()
    responses = iter([
        Response(payload=[{"id": "track-1"}]),
        Response(500, [], "failed"),
        Response(payload=[{"id": "track-1"}]),
        Response(payload=[]),
        Response(payload=[{"id": "item-1"}]),
        Response(500, [], "failed"),
    ])
    monkeypatch.setattr(repo, "_request", lambda *args, **kwargs: next(responses))

    assert repo.get_pending_trackings() == [{"id": "track-1"}]
    assert repo.get_pending_trackings() == []
    assert repo.get_tracking("track-1") == {"id": "track-1"}
    assert repo.get_tracking("missing") is None
    assert repo.get_update_items("track-1") == [{"id": "item-1"}]
    assert repo.get_update_items("track-1") == []


def test_update_tracking_returns_operation_status(monkeypatch):
    repo = repository()
    responses = iter([Response(), Response(500, {}, "failed")])
    monkeypatch.setattr(repo, "_request", lambda *args, **kwargs: next(responses))
    assert repo.update_tracking("track-1", {"update_status": "completed"}) is True
    assert repo.update_tracking("track-1", {"update_status": "failed"}) is False


def test_upsert_update_item_updates_existing_or_inserts(monkeypatch):
    repo = repository()
    item = {"crm_update_tracking_id": "track-1", "sequence_number": 1}
    responses = iter([
        Response(payload=[{"id": "existing"}]),
        Response(payload=[{"id": "existing"}]),
        Response(payload=[]),
        Response(payload=[{"id": "created"}]),
        Response(payload=[]),
        Response(500, [], "failed"),
    ])
    calls = []

    def fake_request(*args, **kwargs):
        calls.append((args, kwargs))
        return next(responses)

    monkeypatch.setattr(repo, "_request", fake_request)
    assert repo.upsert_update_item(item) == "existing"
    assert calls[1][0][0] == "patch"
    assert repo.upsert_update_item(item) == "created"
    assert calls[3][0][0] == "post"
    assert repo.upsert_update_item(item) is None


def test_update_local_ids_and_sync_status(monkeypatch):
    repo = repository()
    responses = iter([
        Response(), Response(),
        Response(500, {}, "app failed"),
        Response(), Response(500, {}, "submission failed"),
    ])
    monkeypatch.setattr(repo, "_request", lambda *args, **kwargs: next(responses))

    assert repo.update_local_ids_and_sync_status("sub-1", "app-1", "M-1", "completed") is True
    assert repo.update_local_ids_and_sync_status("sub-1", "app-1", "M-1", "completed") is False
    assert repo.update_local_ids_and_sync_status("sub-1", "app-1", "M-1", "completed") is False
