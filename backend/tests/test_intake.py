import io

from app import create_app
from app.config import TestConfig


IDENTITY = {
    "user": {"id": "user-id", "email": "staff@example.test"},
    "staff_profile": {"user_id": "user-id", "role": "analyst", "is_active": True},
}


class Auth:
    def authenticate_staff(self, _token):
        return IDENTITY


class Intake:
    def __init__(self):
        self.application_payload = None
        self.document_args = None

    def create_application(self, token, payload):
        self.application_payload = (token, payload)
        return {"application_id": "app-id", "submission_id": "submission-id"}

    def upload_document(self, *args):
        self.document_args = args
        return {"id": "document-id", "processing_status": "uploaded"}


def make_client():
    intake = Intake()
    app = create_app(TestConfig, auth_service=Auth(), intake_service=intake)
    return app.test_client(), intake


def test_create_application():
    client, intake = make_client()
    response = client.post(
        "/api/v1/applications",
        headers={"Authorization": "Bearer token"},
        json={"customer_name": " Alice Smith ", "loan_type": "purchase"},
    )
    assert response.status_code == 201
    assert intake.application_payload[0] == "token"
    assert intake.application_payload[1]["customer_name"] == "Alice Smith"


def test_create_application_rejects_unknown_loan_type():
    client, _ = make_client()
    response = client.post(
        "/api/v1/applications",
        headers={"Authorization": "Bearer token"},
        json={"customer_name": "Alice", "loan_type": "unknown"},
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_loan_type"


def test_upload_document_accepts_pdf_signature():
    client, intake = make_client()
    response = client.post(
        "/api/v1/submissions/123e4567-e89b-12d3-a456-426614174000/documents",
        headers={"Authorization": "Bearer token"},
        data={
            "document_type": "payslip",
            "file": (io.BytesIO(b"%PDF-1.7 test"), "pay slip.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    assert intake.document_args[3] == "pay_slip.pdf"
    assert intake.document_args[4] == "application/pdf"


def test_upload_document_rejects_fake_pdf():
    client, _ = make_client()
    response = client.post(
        "/api/v1/submissions/123e4567-e89b-12d3-a456-426614174000/documents",
        headers={"Authorization": "Bearer token"},
        data={
            "document_type": "payslip",
            "file": (io.BytesIO(b"not really a pdf"), "fake.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_file_content"
