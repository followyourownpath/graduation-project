from datetime import datetime, timezone
from urllib.parse import quote

import requests

from app.services.intake import IntakeError


def _now():
    return datetime.now(timezone.utc).isoformat()


class SupabaseReviewService:
    BUCKET = "source-documents"

    def __init__(self, supabase_url, publishable_key, timeout_seconds=20.0):
        self._url = supabase_url.rstrip("/")
        self._key = publishable_key
        self._timeout = timeout_seconds

    def list_submissions(self, token, page=1, limit=50, status=None):
        offset = (page - 1) * limit
        params = {
            "select": (
                "id,crm_application_id,customer_name,submission_status,"
                "extraction_status,created_at"
            ),
            "order": "created_at.desc",
            "offset": str(offset),
            "limit": str(limit),
        }
        if status:
            params["submission_status"] = f"eq.{status}"

        response = self._request(
            "get",
            "/rest/v1/fact_find_submission",
            token,
            params=params,
            extra_headers={"Prefer": "count=exact"},
        )
        self._require_ok(response, "submission_list_failed")
        submissions = response.json()
        applications = self._applications_by_id(
            token, [row.get("crm_application_id") for row in submissions]
        )

        data = []
        for row in submissions:
            application = applications.get(row.get("crm_application_id"), {})
            data.append({
                "id": row["id"],
                "customer_name": row.get("customer_name"),
                "loan_type": application.get("loan_type"),
                "submission_status": row.get("submission_status"),
                "extraction_status": row.get("extraction_status"),
                "created_at": row.get("created_at"),
                "risk_level": None,
                "overall_risk_score": None,
            })

        return {"total_count": self._total_count(response, len(data)), "data": data}

    def get_submission(self, token, submission_id):
        response = self._request(
            "get",
            "/rest/v1/fact_find_submission",
            token,
            params={
                "select": (
                    "id,crm_application_id,customer_name,submission_status,"
                    "extraction_status,created_at"
                ),
                "id": f"eq.{submission_id}",
                "limit": "1",
            },
        )
        self._require_ok(response, "submission_lookup_failed")
        rows = response.json()
        if not rows:
            raise IntakeError("submission_not_found", "Submission not found.", 404)
        submission = rows[0]

        application = self._application(token, submission.get("crm_application_id"))
        documents = self._documents(token, submission_id)
        return {
            "id": submission["id"],
            "customer_name": submission.get("customer_name"),
            "loan_type": application.get("loan_type"),
            "submission_status": submission.get("submission_status"),
            "extraction_status": submission.get("extraction_status"),
            "created_at": submission.get("created_at"),
            "risk_level": None,
            "overall_risk_score": None,
            "documents": documents,
        }

    def get_extracted_data(self, token, document_id):
        document_response = self._request(
            "get", "/rest/v1/source_document", token,
            params={
                "select": "id,document_type",
                "id": f"eq.{document_id}",
                "limit": "1",
            },
        )
        self._require_ok(document_response, "document_lookup_failed")
        documents = document_response.json()
        if not documents:
            raise IntakeError("document_not_found", "Document not found.", 404)

        job_response = self._request(
            "get", "/rest/v1/ocr_extraction_job", token,
            params={
                "select": "id",
                "source_document_id": f"eq.{document_id}",
                "job_status": "eq.completed",
                "order": "completed_at.desc",
                "limit": "1",
            },
        )
        self._require_ok(job_response, "extraction_lookup_failed")
        jobs = job_response.json()
        fields = []
        if jobs:
            fields_response = self._request(
                "get", "/rest/v1/extracted_field", token,
                params={
                    "select": (
                        "id,section_name,field_key,field_label,raw_value,"
                        "normalised_value,confidence,review_status"
                    ),
                    "ocr_extraction_job_id": f"eq.{jobs[0]['id']}",
                    "order": "created_at.asc",
                },
            )
            self._require_ok(fields_response, "extracted_fields_lookup_failed")
            fields = []
            for row in fields_response.json():
                display_value = row.get("normalised_value")
                if display_value is None:
                    display_value = row.get("raw_value")
                fields.append({
                    "field_id": row["id"],
                    "section_name": row.get("section_name"),
                    "field_key": row.get("field_key"),
                    "field_label": row.get("field_label"),
                    "raw_value": display_value,
                    "confidence": row.get("confidence"),
                    "review_status": row.get("review_status") or "pending",
                })

        return {
            "doc_id": documents[0]["id"],
            "document_type": documents[0].get("document_type"),
            "fields": fields,
        }

    def review_field(self, token, field_id, payload, reviewed_by):
        lookup = self._request(
            "get", "/rest/v1/extracted_field", token,
            params={
                "select": "id,raw_value,normalised_value",
                "id": f"eq.{field_id}",
                "limit": "1",
            },
        )
        self._require_ok(lookup, "field_lookup_failed")
        rows = lookup.json()
        if not rows:
            raise IntakeError("field_not_found", "Extracted field not found.", 404)

        corrected_value = payload.get("corrected_value")
        review_status = payload["review_status"]
        update = self._request(
            "patch", "/rest/v1/extracted_field", token,
            params={"id": f"eq.{field_id}"},
            json={"normalised_value": corrected_value, "review_status": review_status},
        )
        self._require_ok(update, "field_update_failed")

        audit = self._request(
            "post", "/rest/v1/field_review", token,
            json={
                "extracted_field_id": field_id,
                "reviewed_by": reviewed_by,
                "review_status": review_status,
                "original_value": rows[0].get("raw_value"),
                "corrected_value": corrected_value,
                "review_notes": payload.get("review_notes"),
                "reviewed_at": _now(),
            },
        )
        self._require_ok(audit, "field_review_audit_failed")
        return {"message": "Updated successfully"}

    def _documents(self, token, submission_id):
        response = self._request(
            "get", "/rest/v1/source_document", token,
            params={
                "select": (
                    "id,original_file_name,document_type,processing_status,storage_uri"
                ),
                "fact_find_submission_id": f"eq.{submission_id}",
                "order": "created_at.asc",
            },
        )
        self._require_ok(response, "document_list_failed")
        documents = []
        for row in response.json():
            documents.append({
                "doc_id": row["id"],
                "original_file_name": row.get("original_file_name"),
                "document_type": row.get("document_type"),
                "processing_status": self._frontend_processing_status(
                    row.get("processing_status")
                ),
                "storage_uri": self._signed_url(token, row.get("storage_uri")),
            })
        return documents

    def _application(self, token, application_id):
        if not application_id:
            return {}
        response = self._request(
            "get", "/rest/v1/crm_application", token,
            params={"select": "id,loan_type", "id": f"eq.{application_id}", "limit": "1"},
        )
        self._require_ok(response, "application_lookup_failed")
        rows = response.json()
        return rows[0] if rows else {}

    def _applications_by_id(self, token, application_ids):
        ids = [value for value in dict.fromkeys(application_ids) if value]
        if not ids:
            return {}
        response = self._request(
            "get", "/rest/v1/crm_application", token,
            params={"select": "id,loan_type", "id": f"in.({','.join(ids)})"},
        )
        self._require_ok(response, "application_lookup_failed")
        return {row["id"]: row for row in response.json()}

    def _signed_url(self, token, storage_uri):
        if not storage_uri:
            return ""
        bucket, path = storage_uri.split("/", 1)
        response = self._request(
            "post", f"/storage/v1/object/sign/{bucket}/{quote(path, safe='/')}", token,
            json={"expiresIn": 3600},
        )
        self._require_ok(response, "document_url_failed")
        signed_url = response.json().get("signedURL", "")
        if signed_url.startswith("/"):
            return f"{self._url}/storage/v1{signed_url}" if not signed_url.startswith("/storage/v1") else f"{self._url}{signed_url}"
        return signed_url

    def _request(self, method, path, token, extra_headers=None, **kwargs):
        headers = {
            "apikey": token,
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            **(extra_headers or {}),
        }
        try:
            return requests.request(
                method, f"{self._url}{path}", headers=headers,
                timeout=self._timeout, **kwargs,
            )
        except requests.RequestException as error:
            raise IntakeError(
                "supabase_unavailable", "Supabase is unavailable.", 503
            ) from error

    @staticmethod
    def _frontend_processing_status(status):
        return "completed" if status == "extracted" else status

    @staticmethod
    def _total_count(response, fallback):
        content_range = response.headers.get("Content-Range", "")
        try:
            return int(content_range.rsplit("/", 1)[1])
        except (IndexError, ValueError):
            return fallback

    @staticmethod
    def _require_ok(response, code):
        if response.status_code in (401, 403):
            raise IntakeError(code, "Supabase denied this operation.", 403)
        if not response.ok:
            raise IntakeError(code, "Supabase could not complete this operation.", 502)
