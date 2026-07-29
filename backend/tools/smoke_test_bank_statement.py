"""Smoke test: upload bank_statement.pdf and trigger OCR for document_type=bank_statement_3m.

Usage:
    python tools/smoke_test_bank_statement.py
"""

import getpass
import mimetypes
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


DEFAULT_DOCUMENT = (
    Path(__file__).resolve().parents[2]
    / "mock-data"
    / "dataset"
    / "train"
    / "app_100004"
    / "bank_statement.pdf"
)

DOCUMENT_TYPE = "bank_statement_3m"


def fail(message):
    print(f"FAILED: {message}")
    raise SystemExit(1)


def error_code(response):
    try:
        return (response.json().get("error") or {}).get("code", "unknown_error")
    except (ValueError, AttributeError):
        return "unknown_error"


def login(supabase_url, key):
    email = input("Staff email: ").strip()
    password = getpass.getpass("Staff password (hidden): ")
    response = requests.post(
        f"{supabase_url}/auth/v1/token",
        params={"grant_type": "password"},
        headers={"apikey": key, "Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=20,
    )
    if not response.ok or not response.json().get("access_token"):
        fail(f"login failed with HTTP {response.status_code}")
    return response.json()["access_token"]


def main():
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    document = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_DOCUMENT
    if not document.is_file():
        fail(f"mock document not found: {document}")

    print(f"Document type : {DOCUMENT_TYPE}")
    print(f"Mock document : {document}")
    print("This creates persistent smoke-test records and performs Azure page analysis (may use multiple chunks for >2 pages).")
    if input("Continue? [y/N]: ").strip().lower() != "y":
        print("Cancelled. No data was written.")
        return

    token = login(supabase_url, key)
    headers = {"Authorization": f"Bearer {token}"}
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    application = requests.post(
        f"{backend_url}/api/v1/applications",
        headers=headers,
        json={
            "customer_name": f"SmartFinn OCR Smoke Test {timestamp}",
            "loan_type": "purchase",
            "source_channel": "ocr_smoke_test",
            "external_application_id": f"OCR-SMOKE-{DOCUMENT_TYPE}-{timestamp}",
        },
        timeout=20,
    )
    if not application.ok:
        fail(f"application creation failed: {error_code(application)}")
    application_data = application.json()

    mime_type = mimetypes.guess_type(document.name)[0] or "application/pdf"
    with document.open("rb") as stream:
        upload = requests.post(
            f"{backend_url}/api/v1/submissions/{application_data['submission_id']}/documents",
            headers=headers,
            data={"document_type": DOCUMENT_TYPE},
            files={"file": (document.name, stream, mime_type)},
            timeout=30,
        )
    if not upload.ok:
        fail(f"document upload failed: {error_code(upload)}")
    document_data = upload.json()

    ocr = requests.post(
        f"{backend_url}/api/v1/documents/{document_data['id']}/ocr",
        headers=headers,
        timeout=180,
    )
    if not ocr.ok:
        fail(f"OCR pipeline failed: HTTP {ocr.status_code} ({error_code(ocr)})")
    result = ocr.json()

    print("SUCCESS: complete OCR persistence pipeline finished")
    print(f"Application ID      : {application_data['application_id']}")
    print(f"Submission ID       : {application_data['submission_id']}")
    print(f"Document ID         : {document_data['id']}")
    print(f"OCR Job ID          : {result['job_id']}")
    print(f"Pages               : {result['pages']}")
    print(f"Tables              : {result['tables']}")
    print(f"Cells               : {result['cells']}")
    print(f"Standardised fields : {result['fields']}")
    if result["fields"] == 0:
        print("WARNING: 0 fields extracted — check parser regex against actual Azure OCR content.")


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException:
        fail("a network request failed")
    except KeyboardInterrupt:
        print("\nCancelled.")
        raise SystemExit(130)
