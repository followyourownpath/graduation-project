"""Non-interactive smoke test helper for CI / automated runs.
Pass email, password, and document_type as positional arguments:
    python tools/smoke_run.py <email> <password> <document_type> [pdf_path]
"""

import mimetypes
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

DOCUMENT_DEFAULTS = {
    "payslip": "mock-data/dataset/train/app_100004/payslip.pdf",
    "id_100": "mock-data/dataset/train/app_100004/id.pdf",
    "bank_statement_3m": "mock-data/dataset/train/app_100004/bank_statement.pdf",
}


def fail(message):
    print(f"FAILED: {message}")
    raise SystemExit(1)


def error_code(response):
    try:
        return (response.json().get("error") or {}).get("code", "unknown_error")
    except (ValueError, AttributeError):
        return "unknown_error"


def main():
    if len(sys.argv) < 4:
        print("Usage: python tools/smoke_run.py <email> <password> <document_type> [pdf_path]")
        raise SystemExit(1)

    email = sys.argv[1]
    password = sys.argv[2]
    document_type = sys.argv[3]

    load_dotenv()
    repo_root = Path(__file__).resolve().parents[2]
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

    if len(sys.argv) >= 5:
        document = Path(sys.argv[4]).resolve()
    else:
        rel = DOCUMENT_DEFAULTS.get(document_type)
        if not rel:
            fail(f"No default document path for type '{document_type}'. Provide pdf_path as 4th argument.")
        document = (repo_root / rel).resolve()

    if not document.is_file():
        fail(f"Document not found: {document}")

    print(f"Document type : {document_type}")
    print(f"PDF           : {document}")

    # Login
    response = requests.post(
        f"{supabase_url}/auth/v1/token",
        params={"grant_type": "password"},
        headers={"apikey": key, "Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=20,
    )
    if not response.ok or not response.json().get("access_token"):
        fail(f"Login failed HTTP {response.status_code}: {response.text[:200]}")
    token = response.json()["access_token"]
    print("Login         : OK")

    headers = {"Authorization": f"Bearer {token}"}
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # Create application
    application = requests.post(
        f"{backend_url}/api/v1/applications",
        headers=headers,
        json={
            "customer_name": f"SmartFinn Smoke {document_type} {timestamp}",
            "loan_type": "purchase",
            "source_channel": "ocr_smoke_test",
            "external_application_id": f"SMOKE-{document_type}-{timestamp}",
        },
        timeout=20,
    )
    if not application.ok:
        fail(f"Application creation failed: {error_code(application)} — {application.text[:200]}")
    application_data = application.json()
    print(f"Application   : {application_data.get('application_id')}")

    # Upload document
    mime_type = mimetypes.guess_type(document.name)[0] or "application/pdf"
    with document.open("rb") as stream:
        upload = requests.post(
            f"{backend_url}/api/v1/submissions/{application_data['submission_id']}/documents",
            headers=headers,
            data={"document_type": document_type},
            files={"file": (document.name, stream, mime_type)},
            timeout=30,
        )
    if not upload.ok:
        fail(f"Upload failed: {error_code(upload)} — {upload.text[:200]}")
    document_data = upload.json()
    print(f"Document ID   : {document_data['id']}")

    # Trigger OCR
    print("Triggering OCR (may take up to 60s for multi-page PDFs)...")
    ocr = requests.post(
        f"{backend_url}/api/v1/documents/{document_data['id']}/ocr",
        headers=headers,
        timeout=180,
    )
    if not ocr.ok:
        fail(f"OCR failed: HTTP {ocr.status_code} — {ocr.text[:200]}")
    result = ocr.json()

    print("")
    print("=" * 50)
    print("SUCCESS")
    print(f"  Pages               : {result['pages']}")
    print(f"  Tables              : {result['tables']}")
    print(f"  Cells               : {result['cells']}")
    print(f"  Standardised fields : {result['fields']}")
    if result["fields"] == 0:
        print("  WARNING: 0 fields — regex may not match actual Azure OCR output layout.")
    print("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as e:
        print(f"FAILED: network error — {e}")
        raise SystemExit(1)
