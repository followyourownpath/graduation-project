"""Create one test application and upload one tiny PDF through the real API."""

import getpass
import os
import sys
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv


def fail(message: str) -> None:
    print(f"FAILED: {message}")
    raise SystemExit(1)


def response_error(response: requests.Response) -> str:
    try:
        code = (response.json().get("error") or {}).get("code")
    except (ValueError, AttributeError):
        code = None
    return f"HTTP {response.status_code}" + (f" ({code})" if code else "")


def login(supabase_url: str, publishable_key: str) -> str:
    email = input("Staff email: ").strip()
    password = getpass.getpass("Staff password (hidden): ")
    try:
        response = requests.post(
            f"{supabase_url}/auth/v1/token",
            params={"grant_type": "password"},
            headers={"apikey": publishable_key, "Content-Type": "application/json"},
            json={"email": email, "password": password},
            timeout=20,
        )
    except requests.RequestException:
        fail("could not connect to Supabase Auth")
    if not response.ok:
        fail(f"Supabase login returned HTTP {response.status_code}")
    token = response.json().get("access_token")
    if not token:
        fail("Supabase login did not return an access token")
    return token


def main() -> None:
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    publishable_key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    backend_url = os.getenv("BACKEND_URL", "http://localhost:5000").rstrip("/")
    if not supabase_url or not publishable_key:
        fail("Supabase settings are missing from .env")

    print("This test will create one persistent test application and one test document.")
    if input("Continue? [y/N]: ").strip().lower() != "y":
        print("Cancelled. No data was written.")
        return

    token = login(supabase_url, publishable_key)
    headers = {"Authorization": f"Bearer {token}"}
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    try:
        application = requests.post(
            f"{backend_url}/api/v1/applications",
            headers=headers,
            json={
                "customer_name": f"SmartFinn Smoke Test {timestamp}",
                "loan_type": "purchase",
                "source_channel": "backend_smoke_test",
                "external_application_id": f"SMOKE-{timestamp}",
            },
            timeout=20,
        )
    except requests.RequestException:
        fail("could not connect to the local SmartFinn backend")
    if not application.ok:
        fail(f"application creation failed: {response_error(application)}")

    created = application.json()
    submission_id = created["submission_id"]
    pdf = b"%PDF-1.4\n% SmartFinn upload smoke test\n%%EOF\n"

    try:
        document = requests.post(
            f"{backend_url}/api/v1/submissions/{submission_id}/documents",
            headers=headers,
            data={"document_type": "payslip"},
            files={"file": (f"smoke-test-{timestamp}.pdf", pdf, "application/pdf")},
            timeout=30,
        )
    except requests.RequestException:
        fail(
            "document upload connection failed; the test application was still created"
        )
    if not document.ok:
        fail(
            f"document upload failed: {response_error(document)}; "
            "the test application was still created"
        )

    uploaded = document.json()
    print("SUCCESS: application and document were persisted")
    print(f"Application ID: {created['application_id']}")
    print(f"Submission ID: {submission_id}")
    print(f"Document ID: {uploaded['id']}")
    print(f"Document status: {uploaded['processing_status']}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)
