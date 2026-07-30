#!/usr/bin/env python3
"""Non-interactive E2E: upload → OCR → fetch extracted-data → compare to offline goldens.

Requires backend running with AUTH_DEMO_BYPASS=true (uses secret key for Supabase writes).
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
OFFLINE = REPO.parent / "1" / "ocr_id_noa_offline"

CASES = [
    {
        "document_type": "id_100",
        "path": Path("/Users/xjwzd/Documents/UNSW/2026 T2/9900/MOCK_DATA/id/WechatIMG2429.jpg"),
        "expected": OFFLINE / "expected" / "id_licence.fields.json",
        "min_fields": 9,
    },
    {
        "document_type": "ato_notice",
        "path": Path("/Users/xjwzd/Documents/UNSW/2026 T2/9900/MOCK_DATA/NOA/Mock_Notice_of_Assessment.pdf"),
        "expected": OFFLINE / "expected" / "noa.fields.json",
        "min_fields": 20,
    },
]


def fail(msg: str):
    print(f"FAILED: {msg}")
    raise SystemExit(1)


def main():
    load_dotenv(BACKEND / ".env")
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    # Force 8000 if mis-set to 5000 while wsgi listens on 8000
    if backend_url.endswith(":5000"):
        backend_url = "http://localhost:8000"
        print(f"NOTE: overriding BACKEND_URL to {backend_url} (wsgi default)")

    # Health
    try:
        health = requests.get(f"{backend_url}/api/v1/health", timeout=5)
    except requests.RequestException as exc:
        fail(f"backend not reachable at {backend_url}: {exc}")
    if not health.ok:
        fail(f"health check failed: HTTP {health.status_code}")
    print(f"Backend OK: {backend_url}")

    headers = {"Authorization": "Bearer demo-bypass"}
    all_errors: list[str] = []

    for case in CASES:
        doc_type = case["document_type"]
        path: Path = case["path"]
        print("\n" + "=" * 60)
        print(f"CASE: {doc_type}")
        print(f"FILE: {path}")
        if not path.is_file():
            fail(f"sample missing: {path}")

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        app = requests.post(
            f"{backend_url}/api/v1/applications",
            headers=headers,
            json={
                "customer_name": f"E2E {doc_type} {ts}",
                "loan_type": "purchase",
                "source_channel": "e2e_agent_test",
                "external_application_id": f"E2E-{doc_type}-{ts}",
            },
            timeout=30,
        )
        if not app.ok:
            fail(f"create application: HTTP {app.status_code} {app.text[:300]}")
        app_data = app.json()
        print(f"Application : {app_data.get('application_id')}")
        print(f"Submission  : {app_data.get('submission_id')}")

        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        with path.open("rb") as stream:
            upload = requests.post(
                f"{backend_url}/api/v1/submissions/{app_data['submission_id']}/documents",
                headers=headers,
                data={"document_type": doc_type},
                files={"file": (path.name, stream, mime)},
                timeout=60,
            )
        if not upload.ok:
            fail(f"upload: HTTP {upload.status_code} {upload.text[:300]}")
        doc = upload.json()
        doc_id = doc["id"]
        print(f"Document ID : {doc_id}")

        print("OCR running (Azure)...")
        ocr = requests.post(
            f"{backend_url}/api/v1/documents/{doc_id}/ocr",
            headers=headers,
            timeout=180,
        )
        if not ocr.ok:
            fail(f"ocr: HTTP {ocr.status_code} {ocr.text[:400]}")
        ocr_data = ocr.json()
        print(
            f"OCR result  : pages={ocr_data.get('pages')} tables={ocr_data.get('tables')} "
            f"fields={ocr_data.get('fields')} job={ocr_data.get('job_id')}"
        )
        if (ocr_data.get("fields") or 0) < case["min_fields"]:
            all_errors.append(
                f"{doc_type}: fields={ocr_data.get('fields')} < expected min {case['min_fields']}"
            )

        extracted = requests.get(
            f"{backend_url}/api/v1/documents/{doc_id}/extracted-data",
            headers=headers,
            timeout=30,
        )
        if not extracted.ok:
            fail(f"extracted-data: HTTP {extracted.status_code} {extracted.text[:300]}")
        payload = extracted.json()
        # API may return {fields: [...]} or a list
        if isinstance(payload, dict):
            field_rows = payload.get("fields") or payload.get("extracted_fields") or payload.get("data") or []
            if not field_rows and any(k in payload for k in ("field_key",)):
                field_rows = [payload]
        else:
            field_rows = payload

        actual = {
            row["field_key"]: row.get("raw_value")  # API exposes display value as raw_value
            for row in field_rows
            if isinstance(row, dict) and row.get("field_key")
        }
        print(f"API fields  : {len(actual)}")
        for key, val in actual.items():
            print(f"  {key}: {val!r}")

        expected_path: Path = case["expected"]
        if expected_path.is_file():
            expected = {
                k: v.get("normalised_value")
                for k, v in json.loads(expected_path.read_text(encoding="utf-8")).items()
            }
            for key, exp in expected.items():
                got = actual.get(key)
                if got != exp:
                    # Allow null vs missing for optional empties only if both falsy? No — strict.
                    all_errors.append(f"{doc_type}.{key}: got {got!r}, expected {exp!r}")
            missing = set(expected) - set(actual)
            if missing:
                all_errors.append(f"{doc_type}: missing keys {sorted(missing)}")
        else:
            print(f"NOTE: no golden at {expected_path}, skipped value compare")

        out = OFFLINE / "actual" / f"e2e_{doc_type}.fields.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(actual, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {out}")

    print("\n" + "=" * 60)
    if all_errors:
        print("VERIFICATION FAILED")
        for err in all_errors:
            print(" -", err)
        raise SystemExit(1)
    print("VERIFICATION OK: both samples persisted and match offline goldens.")


if __name__ == "__main__":
    main()
