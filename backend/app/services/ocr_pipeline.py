import json
import uuid
from datetime import datetime, timezone
from pathlib import PurePosixPath
from urllib.parse import quote

import requests

from app.services.azure_document_intelligence import DocumentIntelligenceError
from app.services.azure_paging import analyze_pdf_in_page_chunks
from app.services.intake import IntakeError
from app.normalization.fact_find import extract_fact_find_acroform
from app.normalization.fact_find_ocr import extract_fact_find_ocr_fields
from app.normalization.payslip import extract_payslip_fields


def _now():
    return datetime.now(timezone.utc).isoformat()


def _bounding_box(item):
    regions = item.get("boundingRegions") or []
    return regions[0].get("polygon") if regions else None


class SupabaseOcrRepository:
    def __init__(self, url, key, timeout=30.0):
        self._url = url.rstrip("/")
        self._key = key
        self._timeout = timeout

    def get_document(self, token, document_id):
        response = self._request(
            "get", "/rest/v1/source_document", token,
            params={"select": "*", "id": f"eq.{document_id}", "limit": "1"},
        )
        self._ok(response, "document_lookup_failed")
        rows = response.json()
        if not rows:
            raise IntakeError("document_not_found", "Document not found.", 404)
        return rows[0]

    def download(self, token, storage_uri):
        bucket, path = storage_uri.split("/", 1)
        response = self._request(
            "get", f"/storage/v1/object/authenticated/{bucket}/{quote(path, safe='/')}", token
        )
        self._ok(response, "document_download_failed")
        return response.content

    def create_job(self, token, payload):
        return self._insert(token, "ocr_extraction_job", payload)[0]

    def update(self, token, table, row_id, payload):
        response = self._request(
            "patch", f"/rest/v1/{table}", token,
            params={"id": f"eq.{row_id}"}, json=payload,
        )
        self._ok(response, f"{table}_update_failed")

    def upload_raw_response(self, token, document_id, job_id, result):
        path = f"{document_id}/{job_id}.json"
        response = self._request(
            "post", f"/storage/v1/object/ocr-responses/{path}", token,
            data=json.dumps(result, separators=(",", ":")).encode("utf-8"),
            extra_headers={"Content-Type": "application/json", "x-upsert": "false"},
        )
        self._ok(response, "ocr_response_storage_failed")
        return f"ocr-responses/{path}"

    def persist_analysis(self, token, document_id, job_id, document_type, result):
        analysis = result.get("analyzeResult") or {}
        page_ids = {}
        pages = []
        for page in analysis.get("pages") or []:
            page_id = str(uuid.uuid4())
            page_number = page.get("pageNumber")
            page_ids[page_number] = page_id
            pages.append({
                "id": page_id,
                "source_document_id": document_id,
                "page_number": page_number,
                "page_label": str(page_number),
                "width": page.get("width"),
                "height": page.get("height"),
                "raw_text": "\n".join(line.get("content", "") for line in page.get("lines") or []),
            })
        if pages:
            self._insert(token, "document_page", pages)

        table_count = 0
        cell_count = 0
        for index, table in enumerate(analysis.get("tables") or [], start=1):
            regions = table.get("boundingRegions") or []
            page_number = regions[0].get("pageNumber") if regions else None
            table_id = str(uuid.uuid4())
            self._insert(token, "extracted_table", {
                "id": table_id,
                "ocr_extraction_job_id": job_id,
                "source_document_id": document_id,
                "document_page_id": page_ids.get(page_number),
                "table_name": f"table_{index}",
                "section_name": "layout",
                "row_count": table.get("rowCount"),
                "column_count": table.get("columnCount"),
                "bounding_box": _bounding_box(table),
            })
            cells = [{
                "extracted_table_id": table_id,
                "row_index": cell.get("rowIndex"),
                "column_index": cell.get("columnIndex"),
                "column_name": cell.get("kind"),
                "raw_value": cell.get("content"),
                "normalised_value": cell.get("content"),
                "data_type": "text",
                "confidence": cell.get("confidence"),
                "bounding_box": _bounding_box(cell),
            } for cell in table.get("cells") or []]
            if cells:
                self._insert(token, "extracted_table_cell", cells)
            table_count += 1
            cell_count += len(cells)
        extracted_fields = []
        if document_type == "payslip":
            extracted_fields = extract_payslip_fields(result)
        elif document_type == "fact_find":
            extracted_fields = extract_fact_find_ocr_fields(result)
        for field in extracted_fields:
            field.update({
                "ocr_extraction_job_id": job_id,
                "source_document_id": document_id,
            })
        if extracted_fields:
            self._insert(token, "extracted_field", extracted_fields)
        return {
            "pages": len(pages), "tables": table_count,
            "cells": cell_count, "fields": len(extracted_fields),
        }

    def persist_acroform(self, token, document_id, job_id, extraction):
        """Persist fields read directly from a fillable PDF (no OCR involved)."""
        page_ids = {}
        pages = []
        for page in extraction["pages"]:
            page_id = str(uuid.uuid4())
            page_ids[page["page_number"]] = page_id
            pages.append({
                "id": page_id,
                "source_document_id": document_id,
                "page_number": page["page_number"],
                "page_label": str(page["page_number"]),
                "width": page["width"],
                "height": page["height"],
                "raw_text": page["raw_text"],
            })
        if pages:
            self._insert(token, "document_page", pages)

        fields = []
        for field in extraction["fields"]:
            field = dict(field)
            field["document_page_id"] = page_ids.get(field.pop("page_number", None))
            field.update({
                "ocr_extraction_job_id": job_id,
                "source_document_id": document_id,
            })
            fields.append(field)
        if fields:
            self._insert(token, "extracted_field", fields)
        return {"pages": len(pages), "tables": 0, "cells": 0, "fields": len(fields)}

    def _insert(self, token, table, payload):
        response = self._request(
            "post", f"/rest/v1/{table}", token, json=payload,
            extra_headers={"Prefer": "return=representation"},
        )
        self._ok(response, f"{table}_insert_failed")
        return response.json()

    def _request(self, method, path, token, extra_headers=None, **kwargs):
        headers = {"apikey": token, "Authorization": f"Bearer {token}", **(extra_headers or {})}
        try:
            return requests.request(method, f"{self._url}{path}", headers=headers, timeout=self._timeout, **kwargs)
        except requests.RequestException as error:
            raise IntakeError("supabase_unavailable", "Supabase is unavailable.", 503) from error

    @staticmethod
    def _ok(response, code):
        if not response.ok:
            status = 403 if response.status_code in (401, 403) else 502
            raise IntakeError(code, "Supabase could not complete the OCR operation.", status)


class OcrPipelineService:
    def __init__(self, repository, azure_client, model_name):
        self._repository = repository
        self._azure = azure_client
        self._model_name = model_name

    def process(self, token, document_id):
        document = self._repository.get_document(token, document_id)
        job_id = str(uuid.uuid4())
        self._repository.create_job(token, {
            "id": job_id, "source_document_id": document_id,
            "provider": "azure_document_intelligence", "model_name": self._model_name,
            "job_status": "processing", "started_at": _now(),
        })
        self._repository.update(token, "source_document", document_id, {"processing_status": "processing"})
        try:
            content = self._repository.download(token, document["storage_uri"])

            # Fact-find forms filled electronically carry their values as
            # AcroForm widget data; read them directly and skip Azure OCR.
            if document.get("document_type") == "fact_find" and document.get("mime_type") == "application/pdf":
                extraction = extract_fact_find_acroform(content)
                if extraction["fields"]:
                    counts = self._repository.persist_acroform(token, document_id, job_id, extraction)
                    raw_uri = self._repository.upload_raw_response(
                        token, document_id, job_id,
                        {"source": "acroform_direct_read", "fields": extraction["fields"]},
                    )
                    self._repository.update(token, "ocr_extraction_job", job_id, {
                        "provider": "acroform_direct_read", "model_name": "pymupdf",
                        "job_status": "completed", "completed_at": _now(), "raw_response_uri": raw_uri,
                    })
                    self._repository.update(token, "source_document", document_id, {
                        "processing_status": "extracted", "page_count": counts["pages"],
                    })
                    return {"job_id": job_id, "document_id": document_id, "status": "completed", **counts}
                if extraction["has_form"]:
                    # A fillable form with no values entered: OCR would only
                    # see the blank template, so reject instead of wasting quota.
                    raise IntakeError(
                        "fact_find_blank_form",
                        "The fact find form contains no filled-in values. Please upload a completed copy.",
                        422,
                    )
                # No widgets at all (scanned or flattened copy): fall through
                # to the regular Azure OCR route below.

            mime_type = document.get("mime_type") or "application/pdf"
            if mime_type == "application/pdf":
                # F0 (and similar tiers) allow only 2 pages per analyze call.
                result = analyze_pdf_in_page_chunks(self._azure, content)
            else:
                result = self._azure.analyze(content, mime_type)
            raw_uri = self._repository.upload_raw_response(token, document_id, job_id, result)
            counts = self._repository.persist_analysis(
                token, document_id, job_id, document.get("document_type"), result
            )
            completed = _now()
            self._repository.update(token, "ocr_extraction_job", job_id, {
                "job_status": "completed", "completed_at": completed, "raw_response_uri": raw_uri,
            })
            self._repository.update(token, "source_document", document_id, {
                "processing_status": "extracted", "page_count": counts["pages"],
            })
            return {"job_id": job_id, "document_id": document_id, "status": "completed", **counts}
        except (DocumentIntelligenceError, IntakeError) as error:
            self._repository.update(token, "ocr_extraction_job", job_id, {
                "job_status": "failed", "completed_at": _now(), "error_message": error.code,
            })
            self._repository.update(token, "source_document", document_id, {"processing_status": "failed"})
            raise
