import requests
import pytest

from app.services.azure_document_intelligence import DocumentIntelligenceError
from app.services.intake import IntakeError
from app.services.ocr_pipeline import OcrPipelineService, SupabaseOcrRepository


class Response:
    def __init__(self, status_code=200, payload=None, content=b""):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._payload = payload
        self.content = content

    def json(self):
        return self._payload


def test_repository_document_download_and_mutations(monkeypatch):
    repo = SupabaseOcrRepository("https://db.example/", "key", 4)
    responses = iter([
        Response(payload=[{"id": "doc-1", "storage_uri": "bucket/file.pdf"}]),
        Response(content=b"pdf"),
        Response(payload=[{"id": "job-1"}]),
        Response(),
        Response(),
    ])
    calls = []

    def fake_request(*args, **kwargs):
        calls.append((args, kwargs))
        return next(responses)

    monkeypatch.setattr(repo, "_request", fake_request)
    assert repo.get_document("jwt", "doc-1")["id"] == "doc-1"
    assert repo.download("jwt", "bucket/folder/file.pdf") == b"pdf"
    assert repo.create_job("jwt", {"id": "job-1"})["id"] == "job-1"
    repo.update("jwt", "source_document", "doc-1", {"processing_status": "processing"})
    uri = repo.upload_raw_response("jwt", "doc-1", "job-1", {"status": "succeeded"})
    assert uri == "ocr-responses/doc-1/job-1.json"
    assert calls[-1][1]["extra_headers"]["Content-Type"] == "application/json"


def test_repository_reports_missing_document(monkeypatch):
    repo = SupabaseOcrRepository("https://db.example", "key")
    monkeypatch.setattr(repo, "_request", lambda *args, **kwargs: Response(payload=[]))
    with pytest.raises(IntakeError) as caught:
        repo.get_document("jwt", "missing")
    assert (caught.value.code, caught.value.status) == ("document_not_found", 404)


def test_repository_normalises_request_and_response_errors(monkeypatch):
    repo = SupabaseOcrRepository("https://db.example", "key")

    def fail(*args, **kwargs):
        raise requests.Timeout("offline")

    monkeypatch.setattr(requests, "request", fail)
    with pytest.raises(IntakeError) as caught:
        repo._request("get", "/rest/v1/source_document", "jwt")
    assert caught.value.code == "supabase_unavailable"

    for status, expected in [(401, 403), (500, 502)]:
        with pytest.raises(IntakeError) as response_error:
            repo._ok(Response(status), "operation_failed")
        assert response_error.value.status == expected


def test_persist_analysis_writes_pages_tables_cells_and_fields(monkeypatch):
    repo = SupabaseOcrRepository("https://db.example", "key")
    inserts = []

    def fake_insert(_token, table, payload):
        inserts.append((table, payload))
        return payload if isinstance(payload, list) else [payload]

    monkeypatch.setattr(repo, "_insert", fake_insert)
    monkeypatch.setattr(
        "app.services.ocr_pipeline.extract_payslip_fields",
        lambda _result: [{"field_key": "employee_name", "raw_value": "Alice"}],
    )
    result = {
        "analyzeResult": {
            "pages": [{
                "pageNumber": 1,
                "width": 8.5,
                "height": 11,
                "lines": [{"content": "Alice payslip"}],
            }],
            "tables": [{
                "rowCount": 1,
                "columnCount": 1,
                "boundingRegions": [{"pageNumber": 1, "polygon": [0, 0, 1, 1]}],
                "cells": [{
                    "rowIndex": 0,
                    "columnIndex": 0,
                    "kind": "content",
                    "content": "Alice",
                    "confidence": 0.99,
                    "boundingRegions": [{"pageNumber": 1, "polygon": [0, 0, 1, 1]}],
                }],
            }],
        }
    }

    counts = repo.persist_analysis("jwt", "doc-1", "job-1", "payslip", result)
    assert counts == {"pages": 1, "tables": 1, "cells": 1, "fields": 1}
    assert {table for table, _payload in inserts} == {
        "document_page", "extracted_table", "extracted_table_cell", "extracted_field"
    }
    field = next(payload for table, payload in inserts if table == "extracted_field")[0]
    assert field["ocr_extraction_job_id"] == "job-1"
    assert field["source_document_id"] == "doc-1"


def test_persist_acroform_maps_fields_to_pages(monkeypatch):
    repo = SupabaseOcrRepository("https://db.example", "key")
    inserts = []
    monkeypatch.setattr(repo, "_insert", lambda _token, table, payload: inserts.append((table, payload)) or payload)
    extraction = {
        "pages": [{"page_number": 1, "width": 8.5, "height": 11, "raw_text": "Fact Find"}],
        "fields": [{"page_number": 1, "field_key": "full_name", "raw_value": "Alice"}],
    }
    counts = repo.persist_acroform("jwt", "doc-1", "job-1", extraction)
    assert counts == {"pages": 1, "tables": 0, "cells": 0, "fields": 1}
    field = next(payload for table, payload in inserts if table == "extracted_field")[0]
    assert field["document_page_id"]
    assert "page_number" not in field


class PipelineRepository:
    def __init__(self, document):
        self.document = document
        self.updates = []

    def get_document(self, _token, _document_id):
        return self.document

    def create_job(self, _token, payload):
        self.job = payload
        return payload

    def update(self, _token, table, row_id, payload):
        self.updates.append((table, row_id, payload))

    def download(self, _token, _storage_uri):
        return b"document"

    def upload_raw_response(self, _token, _document_id, _job_id, _result):
        return "ocr-responses/raw.json"

    def persist_analysis(self, *_args):
        return {"pages": 1, "tables": 0, "cells": 0, "fields": 2}

    def persist_acroform(self, *_args):
        return {"pages": 2, "tables": 0, "cells": 0, "fields": 4}


class Azure:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def analyze(self, content, mime_type):
        self.calls.append((content, mime_type))
        if self.error:
            raise self.error
        return {"status": "succeeded", "analyzeResult": {}}


def test_pipeline_processes_image_and_completes_document():
    repo = PipelineRepository({
        "id": "doc-1", "storage_uri": "bucket/image.jpg",
        "document_type": "id_100", "mime_type": "image/jpeg",
    })
    azure = Azure()
    result = OcrPipelineService(repo, azure, "layout").process("jwt", "doc-1")
    assert result["status"] == "completed"
    assert result["fields"] == 2
    assert azure.calls == [(b"document", "image/jpeg")]
    assert repo.updates[-1][2] == {"processing_status": "extracted", "page_count": 1}


def test_pipeline_marks_job_and_document_failed():
    repo = PipelineRepository({
        "id": "doc-1", "storage_uri": "bucket/image.jpg",
        "document_type": "id_100", "mime_type": "image/jpeg",
    })
    azure = Azure(DocumentIntelligenceError("azure_unavailable", "Unavailable", 503))
    with pytest.raises(DocumentIntelligenceError):
        OcrPipelineService(repo, azure, "layout").process("jwt", "doc-1")
    assert repo.updates[-2][2]["error_message"] == "azure_unavailable"
    assert repo.updates[-1][2] == {"processing_status": "failed"}


def test_pipeline_reads_completed_acroform_without_azure(monkeypatch):
    repo = PipelineRepository({
        "id": "doc-1", "storage_uri": "bucket/fact-find.pdf",
        "document_type": "fact_find", "mime_type": "application/pdf",
    })
    azure = Azure()
    monkeypatch.setattr(
        "app.services.ocr_pipeline.extract_fact_find_acroform",
        lambda _content: {"has_form": True, "pages": [], "fields": [{"field_key": "full_name"}]},
    )
    result = OcrPipelineService(repo, azure, "layout").process("jwt", "doc-1")
    assert result["fields"] == 4
    assert azure.calls == []


def test_pipeline_rejects_blank_acroform(monkeypatch):
    repo = PipelineRepository({
        "id": "doc-1", "storage_uri": "bucket/fact-find.pdf",
        "document_type": "fact_find", "mime_type": "application/pdf",
    })
    monkeypatch.setattr(
        "app.services.ocr_pipeline.extract_fact_find_acroform",
        lambda _content: {"has_form": True, "pages": [], "fields": []},
    )
    with pytest.raises(IntakeError) as caught:
        OcrPipelineService(repo, Azure(), "layout").process("jwt", "doc-1")
    assert caught.value.code == "fact_find_blank_form"
    assert repo.updates[-1][2] == {"processing_status": "failed"}
