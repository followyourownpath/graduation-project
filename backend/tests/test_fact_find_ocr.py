"""Tests for Fact Find Azure OCR field extraction and page-chunk merging."""

import json
from pathlib import Path

import fitz
import pytest

from app.normalization.fact_find_ocr import extract_fact_find_ocr_fields
from app.services.azure_paging import (
    analyze_pdf_in_page_chunks,
    merge_chunk_results,
    pdf_page_count,
    split_pdf_chunks,
)
from app.services.ocr_pipeline import OcrPipelineService

SLIM_AZURE = Path(__file__).parent / "fixtures" / "fact_find_azure_paged_slim.json"
FILLED_PDF = Path(__file__).parent / "fixtures" / "fact_find_filled.pdf"


@pytest.fixture(scope="module")
def slim_azure():
    return json.loads(SLIM_AZURE.read_text())


def test_ocr_extractor_returns_full_field_set(slim_azure):
    fields = extract_fact_find_ocr_fields(slim_azure)
    by_key = {f["field_key"]: f for f in fields}
    assert len(fields) == 264
    assert by_key["cover_customer_name"]["normalised_value"] == "John & Mary Citizen"
    assert by_key["applicant_1_mobile"]["normalised_value"] == "+61412345678"
    assert by_key["applicant_1_current_employment_basis"]["normalised_value"] == "full_time"
    assert by_key["expense_groceries_monthly_amount"]["normalised_value"] == "2500.00"
    assert set(fields[0]) >= {
        "section_name", "applicant_number", "field_key", "field_label",
        "raw_value", "normalised_value", "data_type", "review_status",
        "mapped_table", "mapped_column",
    }


def test_merge_chunk_results_remaps_page_numbers():
    chunk1 = {
        "analyzeResult": {
            "apiVersion": "2024-11-30",
            "modelId": "prebuilt-layout",
            "content": "page1",
            "pages": [{"pageNumber": 1, "width": 1}],
            "tables": [{"boundingRegions": [{"pageNumber": 1}], "cells": []}],
            "paragraphs": [],
        }
    }
    chunk2 = {
        "analyzeResult": {
            "content": "page3",
            "pages": [{"pageNumber": 1, "width": 1}, {"pageNumber": 2, "width": 1}],
            "tables": [{"boundingRegions": [{"pageNumber": 2}], "cells": []}],
            "paragraphs": [],
        }
    }
    merged = merge_chunk_results([(1, chunk1), (3, chunk2)])
    pages = [p["pageNumber"] for p in merged["analyzeResult"]["pages"]]
    assert pages == [1, 3, 4]
    assert "page1" in merged["analyzeResult"]["content"]
    assert "page3" in merged["analyzeResult"]["content"]
    table_pages = [
        t["boundingRegions"][0]["pageNumber"]
        for t in merged["analyzeResult"]["tables"]
    ]
    assert table_pages == [1, 4]


def test_split_pdf_chunks_respects_two_page_cap():
    document = fitz.open()
    for _ in range(5):
        document.new_page()
    pdf_bytes = document.tobytes()
    document.close()

    assert pdf_page_count(pdf_bytes) == 5
    chunks = split_pdf_chunks(pdf_bytes, pages_per_chunk=2)
    assert [(start, end) for start, end, _ in chunks] == [(1, 2), (3, 4), (5, 5)]
    for _, _, chunk_bytes in chunks:
        part = fitz.open(stream=chunk_bytes, filetype="pdf")
        assert len(part) <= 2
        part.close()


def test_analyze_pdf_in_page_chunks_calls_azure_per_chunk():
    document = fitz.open()
    for _ in range(3):
        document.new_page()
    pdf_bytes = document.tobytes()
    document.close()

    calls = []

    class FakeAzure:
        def analyze(self, content, mime_type):
            calls.append((len(content), mime_type))
            page_count = len(fitz.open(stream=content, filetype="pdf"))
            return {
                "status": "succeeded",
                "analyzeResult": {
                    "content": f"chunk-{len(calls)}",
                    "pages": [{"pageNumber": i + 1} for i in range(page_count)],
                    "tables": [],
                    "paragraphs": [],
                },
            }

        _sleep = lambda self, _: None  # noqa: E731

    merged = analyze_pdf_in_page_chunks(FakeAzure(), pdf_bytes, chunk_pause_seconds=0)
    assert len(calls) == 2
    assert [p["pageNumber"] for p in merged["analyzeResult"]["pages"]] == [1, 2, 3]


class _ScanRepository:
    def __init__(self, content):
        self._content = content
        self.azure_result = None
        self.persisted_fields = None

    def get_document(self, token, document_id):
        return {
            "id": document_id,
            "document_type": "fact_find",
            "mime_type": "application/pdf",
            "storage_uri": "source-documents/x/scan.pdf",
        }

    def download(self, token, storage_uri):
        return self._content

    def create_job(self, token, payload):
        return payload

    def update(self, token, table, row_id, payload):
        pass

    def upload_raw_response(self, token, document_id, job_id, result):
        self.azure_result = result
        return f"ocr-responses/{document_id}/{job_id}.json"

    def persist_analysis(self, token, document_id, job_id, document_type, result):
        from app.normalization.fact_find_ocr import extract_fact_find_ocr_fields
        fields = extract_fact_find_ocr_fields(result)
        self.persisted_fields = fields
        return {
            "pages": len((result.get("analyzeResult") or {}).get("pages") or []),
            "tables": 0,
            "cells": 0,
            "fields": len(fields),
        }


def test_pipeline_uses_paged_azure_for_scanned_fact_find(slim_azure):
    # Flattened PDF (no widgets) forces Azure path.
    document = fitz.open()
    for _ in range(3):
        document.new_page().insert_text((72, 72), "scanned fact find")
    pdf_bytes = document.tobytes()
    document.close()

    class FakeAzure:
        def analyze(self, content, mime_type):
            # Return one page of the slim fixture per chunk call.
            pages = (slim_azure.get("analyzeResult") or {}).get("pages") or []
            page = pages[min(len(calls), len(pages) - 1)] if pages else {"pageNumber": 1}
            calls.append(1)
            return {
                "status": "succeeded",
                "analyzeResult": {
                    "content": (slim_azure.get("analyzeResult") or {}).get("content", ""),
                    "pages": [dict(page, pageNumber=1)],
                    "tables": (slim_azure.get("analyzeResult") or {}).get("tables") or [],
                    "paragraphs": [],
                },
            }

        _sleep = lambda self, _: None  # noqa: E731

    calls = []
    repository = _ScanRepository(pdf_bytes)
    service = OcrPipelineService(repository, FakeAzure(), "prebuilt-layout")
    result = service.process("token", "doc-scan")

    assert result["status"] == "completed"
    assert len(calls) == 2  # 3 pages -> 2 chunks
    assert repository.persisted_fields is not None
    assert len(repository.persisted_fields) == 264
