from pathlib import Path

import fitz
import pytest

from app.normalization.fact_find import extract_fact_find_acroform
from app.normalization.values import australian_date, phone
from app.services.ocr_pipeline import OcrPipelineService

FIXTURE = Path(__file__).parent / "fixtures" / "fact_find_filled.pdf"


@pytest.fixture(scope="module")
def filled_pdf_bytes():
    return FIXTURE.read_bytes()


@pytest.fixture(scope="module")
def extraction(filled_pdf_bytes):
    return extract_fact_find_acroform(filled_pdf_bytes)


def test_detects_form_and_extracts_all_fields(extraction):
    assert extraction["has_form"] is True
    assert len(extraction["pages"]) == 7
    # The fixture has every mapped widget filled: 264 data fields.
    assert len(extraction["fields"]) == 264


def test_field_shape_matches_extracted_field_columns(extraction):
    field = extraction["fields"][0]
    expected_keys = {
        "section_name", "applicant_number", "field_key", "field_label",
        "raw_value", "normalised_value", "data_type", "confidence",
        "bounding_box", "mapped_table", "mapped_column", "review_status",
        "page_number",
    }
    assert set(field) == expected_keys
    assert field["confidence"] == 1.0
    assert field["review_status"] == "pending"
    assert isinstance(field["bounding_box"], list)
    assert len(field["bounding_box"]) == 8


def test_key_values_and_enum_normalisation(extraction):
    fields = {f["field_key"]: f for f in extraction["fields"]}

    assert fields["cover_customer_name"]["normalised_value"] == "John & Mary Citizen"
    assert fields["cover_form_date"]["normalised_value"] == "2020-03-15"

    # Radio groups normalise to mapping-matrix enum values.
    assert fields["applicant_1_marital_status"]["normalised_value"] == "single"
    assert fields["applicant_1_marital_status"]["mapped_table"] == "applicant"
    assert fields["applicant_1_current_address_ownership_status"]["normalised_value"] == "mortgage"
    assert fields["applicant_1_current_employment_basis"]["normalised_value"] == "full_time"

    # Applicant 2 fields stay separate from applicant 1.
    assert fields["applicant_2_full_name"]["applicant_number"] == 2
    assert fields["applicant_2_full_name"]["normalised_value"] == "Mary Citizen"

    # Combo boxes and money/date/phone normalisation.
    assert fields["vehicle_1_ownership"]["normalised_value"] == "applicant_1"
    assert fields["expense_groceries_monthly_amount"]["normalised_value"] == "2500.00"
    assert fields["applicant_1_mobile"]["normalised_value"] == "+61412345678"
    assert fields["applicant_1_email"]["normalised_value"] == "applicant1@example.com"
    assert fields["applicant_2_current_address_same_as_applicant_1"]["normalised_value"] == "true"
    # Bounding box is present and on-page for a known field.
    box = fields["applicant_1_mobile"]["bounding_box"]
    assert len(box) == 8
    assert all(isinstance(v, (int, float)) for v in box)


def test_blank_form_yields_no_fields():
    document = fitz.open()
    page = document.new_page()
    widget = fitz.Widget()
    widget.field_name = "Customer Name"  # mapped widget, but left empty
    widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    widget.rect = fitz.Rect(72, 72, 300, 92)
    page.add_widget(widget)
    blank = extract_fact_find_acroform(document.tobytes())
    assert blank["has_form"] is True
    assert blank["fields"] == []


def test_pdf_without_widgets_reports_no_form():
    document = fitz.open()
    document.new_page().insert_text((72, 72), "Scanned fact find placeholder")
    result = extract_fact_find_acroform(document.tobytes())
    assert result["has_form"] is False
    assert result["fields"] == []


class _FakeRepository:
    def __init__(self, content):
        self._content = content
        self.updates = []
        self.persisted = None

    def get_document(self, token, document_id):
        return {
            "id": document_id, "document_type": "fact_find",
            "mime_type": "application/pdf", "storage_uri": "source-documents/x/y.pdf",
        }

    def download(self, token, storage_uri):
        return self._content

    def create_job(self, token, payload):
        return payload

    def update(self, token, table, row_id, payload):
        self.updates.append((table, payload))

    def upload_raw_response(self, token, document_id, job_id, result):
        return f"ocr-responses/{document_id}/{job_id}.json"

    def persist_acroform(self, token, document_id, job_id, extraction):
        self.persisted = extraction
        return {"pages": len(extraction["pages"]), "tables": 0, "cells": 0,
                "fields": len(extraction["fields"])}


class _ExplodingAzure:
    def analyze(self, content, mime_type):
        raise AssertionError("Azure must not be called for a filled fact find form")


def test_pipeline_short_circuits_azure_for_filled_form(filled_pdf_bytes):
    repository = _FakeRepository(filled_pdf_bytes)
    service = OcrPipelineService(repository, _ExplodingAzure(), "prebuilt-layout")
    result = service.process("token", "doc-1")

    assert result["status"] == "completed"
    assert result["fields"] == 264
    assert repository.persisted is not None
    job_updates = [p for t, p in repository.updates if t == "ocr_extraction_job"]
    assert any(p.get("provider") == "acroform_direct_read" for p in job_updates)
    document_updates = [p for t, p in repository.updates if t == "source_document"]
    assert any(p.get("processing_status") == "extracted" for p in document_updates)


def test_extended_date_formats():
    assert australian_date("02/06/2026") == "2026-06-02"  # existing behaviour
    assert australian_date("2026.8.1") == "2026-08-01"
    assert australian_date("01 Aug 2026") == "2026-08-01"
    assert australian_date("8/2026") == "2026-08-01"
    assert australian_date("not a date") is None


def test_phone_normalisation_to_e164():
    assert phone("0412 345 678") == "+61412345678"
    assert phone("+61 412-345-678") == "+61412345678"
    assert phone("61412345678") == "+61412345678"
    assert phone("not a phone") is None
