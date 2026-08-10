import hashlib

import pytest
import requests

from app.services.intake import IntakeError, SupabaseIntakeService


class Response:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._payload = payload

    def json(self):
        return self._payload


def test_create_application_maps_rpc_payload(monkeypatch):
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return Response(payload=[{"application_id": "app-1", "submission_id": "sub-1"}])

    monkeypatch.setattr(requests, "request", fake_request)
    result = SupabaseIntakeService("https://db.example/", "key", 4).create_application(
        "jwt", {"customer_name": "Alice", "loan_type": "purchase"}
    )

    assert result["submission_id"] == "sub-1"
    assert captured["url"].endswith("/rest/v1/rpc/create_application_intake")
    assert captured["json"]["p_source_channel"] == "web"
    assert captured["headers"]["Authorization"] == "Bearer jwt"
    assert captured["timeout"] == 4


def test_upload_document_persists_hash_and_metadata(monkeypatch):
    calls = []
    responses = iter([
        Response(),
        Response(payload=[{"id": "doc-1", "processing_status": "uploaded"}]),
    ])

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return next(responses)

    monkeypatch.setattr(requests, "request", fake_request)
    content = b"%PDF-1.7 test"
    result = SupabaseIntakeService("https://db.example", "key").upload_document(
        "jwt", "sub-1", "payslip", "pay slip.pdf", "application/pdf", content
    )

    assert result["id"] == "doc-1"
    metadata = calls[1][2]["json"]
    assert metadata["file_hash_sha256"] == hashlib.sha256(content).hexdigest()
    assert metadata["file_type"] == "pdf"
    assert metadata["file_size_bytes"] == len(content)
    assert calls[0][2]["headers"]["Content-Type"] == "application/pdf"


def test_upload_document_rolls_back_object_when_metadata_fails(monkeypatch):
    calls = []
    responses = iter([Response(), Response(500, {}), Response(204, None)])

    def fake_request(method, url, **kwargs):
        calls.append((method, url))
        return next(responses)

    monkeypatch.setattr(requests, "request", fake_request)
    with pytest.raises(IntakeError) as caught:
        SupabaseIntakeService("https://db.example", "key").upload_document(
            "jwt", "sub-1", "payslip", "payslip.pdf", "application/pdf", b"pdf"
        )
    assert caught.value.code == "document_metadata_failed"
    assert caught.value.status == 502
    assert calls[-1][0] == "delete"


def test_request_network_failure_is_normalised(monkeypatch):
    def fail(*args, **kwargs):
        raise requests.Timeout("timeout")

    monkeypatch.setattr(requests, "request", fail)
    with pytest.raises(IntakeError) as caught:
        SupabaseIntakeService("https://db.example", "key").create_application(
            "jwt", {"customer_name": "Alice", "loan_type": "purchase"}
        )
    assert (caught.value.code, caught.value.status) == ("supabase_unavailable", 503)


@pytest.mark.parametrize(("status_code", "expected"), [(401, 403), (403, 403), (500, 502)])
def test_supabase_failures_use_safe_status(status_code, expected):
    with pytest.raises(IntakeError) as caught:
        SupabaseIntakeService._require_ok(Response(status_code, {}), "operation_failed")
    assert caught.value.status == expected
    assert caught.value.code == "operation_failed"
