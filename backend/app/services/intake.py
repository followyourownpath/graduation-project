import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests


@dataclass
class IntakeError(Exception):
    code: str
    message: str
    status: int


class SupabaseIntakeService:
    BUCKET = "source-documents"

    def __init__(self, supabase_url: str, publishable_key: str, timeout_seconds=20.0):
        self._url = supabase_url.rstrip("/")
        self._key = publishable_key
        self._timeout = timeout_seconds

    def create_application(self, token: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request(
            "post",
            "/rest/v1/rpc/create_application_intake",
            token,
            json={
                "p_customer_name": payload["customer_name"],
                "p_loan_type": payload["loan_type"],
                "p_source_channel": payload.get("source_channel", "web"),
                "p_external_application_id": payload.get("external_application_id"),
            },
        )
        self._require_ok(response, "application_create_failed")
        rows = response.json()
        return rows[0] if isinstance(rows, list) else rows

    def upload_document(
        self,
        token: str,
        submission_id: str,
        document_type: str,
        filename: str,
        mime_type: str,
        content: bytes,
    ) -> dict[str, Any]:
        document_id = str(uuid.uuid4())
        object_path = f"{submission_id}/{document_id}/{filename}"
        encoded_path = quote(object_path, safe="/")

        upload = self._request(
            "post",
            f"/storage/v1/object/{self.BUCKET}/{encoded_path}",
            token,
            data=content,
            extra_headers={"Content-Type": mime_type, "x-upsert": "false"},
        )
        self._require_ok(upload, "document_storage_failed")

        record = {
            "id": document_id,
            "fact_find_submission_id": submission_id,
            "original_file_name": filename,
            "file_type": Path(filename).suffix.lower().lstrip("."),
            "mime_type": mime_type,
            "file_size_bytes": len(content),
            "file_hash_sha256": hashlib.sha256(content).hexdigest(),
            "storage_uri": f"{self.BUCKET}/{object_path}",
            "document_type": document_type,
            "upload_source": "web",
            "processing_status": "uploaded",
        }

        metadata = self._request(
            "post",
            "/rest/v1/source_document",
            token,
            json=record,
            extra_headers={"Prefer": "return=representation"},
        )
        if not metadata.ok:
            self._request(
                "delete",
                f"/storage/v1/object/{self.BUCKET}/{encoded_path}",
                token,
            )
            self._require_ok(metadata, "document_metadata_failed")

        rows = metadata.json()
        return rows[0] if isinstance(rows, list) else rows

    def _request(self, method, path, token, extra_headers=None, **kwargs):
        headers = {
            "apikey": self._key,
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            **(extra_headers or {}),
        }
        try:
            return requests.request(
                method,
                f"{self._url}{path}",
                headers=headers,
                timeout=self._timeout,
                **kwargs,
            )
        except requests.RequestException as error:
            raise IntakeError(
                "supabase_unavailable", "Supabase is unavailable.", 503
            ) from error

    @staticmethod
    def _require_ok(response, code):
        if response.status_code in (401, 403):
            raise IntakeError(code, "Supabase denied this operation.", 403)
        if not response.ok:
            raise IntakeError(code, "Supabase could not complete this operation.", 502)
