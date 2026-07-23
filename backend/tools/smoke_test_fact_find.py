"""Run the real upload pipeline with a filled fact-find PDF.

Unlike the payslip smoke test, a completed fact-find form is read directly
from its AcroForm data (no Azure call, no OCR quota used).
"""

import getpass
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


DEFAULT_DOCUMENT = (
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "fact_find_filled.pdf"
)


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
    backend_url = os.getenv("BACKEND_URL", "http://localhost:5000").rstrip("/")
    document = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_DOCUMENT
    if not document.is_file():
        fail(f"document not found: {document}")

    print(f"Fact find document: {document}")
    print("This creates persistent smoke-test records. No Azure quota is used "
          "when the form is read directly.")
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
            "customer_name": f"SmartFinn Fact Find Smoke Test {timestamp}",
            "loan_type": "purchase",
            "source_channel": "fact_find_smoke_test",
            "external_application_id": f"FF-SMOKE-{timestamp}",
        },
        timeout=20,
    )
    if not application.ok:
        fail(f"application creation failed: {error_code(application)}")
    application_data = application.json()

    with document.open("rb") as stream:
        upload = requests.post(
            f"{backend_url}/api/v1/submissions/{application_data['submission_id']}/documents",
            headers=headers,
            data={"document_type": "fact_find"},
            files={"file": (document.name, stream, "application/pdf")},
            timeout=30,
        )
    if not upload.ok:
        fail(f"document upload failed: {error_code(upload)}")
    document_data = upload.json()

    processing = requests.post(
        f"{backend_url}/api/v1/documents/{document_data['id']}/ocr",
        headers=headers,
        timeout=180,
    )
    if not processing.ok:
        fail(f"pipeline failed: HTTP {processing.status_code} ({error_code(processing)})")
    result = processing.json()

    print("SUCCESS: fact find pipeline finished")
    print(f"Application ID: {application_data['application_id']}")
    print(f"Submission ID: {application_data['submission_id']}")
    print(f"Document ID: {document_data['id']}")
    print(f"Job ID: {result['job_id']}")
    print(f"Pages: {result['pages']}")
    print(f"Standardised fields: {result['fields']}")
    if result["fields"] == 0:
        print("WARNING: 0 fields extracted - the PDF probably has no AcroForm data.")


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException:
        fail("a network request failed")
    except KeyboardInterrupt:
        print("\nCancelled.")
        raise SystemExit(130)
