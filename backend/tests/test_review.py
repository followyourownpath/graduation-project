from app import create_app
from app.config import TestConfig
from app.services.intake import IntakeError


IDENTITY = {
    "user": {"id": "user-id", "email": "staff@example.test"},
    "staff_profile": {"user_id": "user-id", "role": "analyst", "is_active": True},
}
UUID = "123e4567-e89b-12d3-a456-426614174000"


class Auth:
    def authenticate_staff(self, _token):
        return IDENTITY


class Review:
    def __init__(self):
        self.call = None

    def list_submissions(self, *args):
        self.call = ("list", args)
        return {"total_count": 1, "data": [{"id": UUID}]}

    def get_submission(self, *args):
        self.call = ("detail", args)
        return {"id": UUID, "documents": []}

    def get_extracted_data(self, *args):
        self.call = ("fields", args)
        return {"doc_id": UUID, "document_type": "payslip", "fields": []}

    def review_field(self, *args):
        self.call = ("review", args)
        return {"message": "Updated successfully"}


def make_client(review=None):
    review = review or Review()
    app = create_app(TestConfig, auth_service=Auth(), review_service=review)
    return app.test_client(), review


def headers():
    return {"Authorization": "Bearer token"}


def test_list_submissions_matches_frontend_shape():
    client, review = make_client()
    response = client.get("/api/v1/submissions?page=2&limit=10&status=in_review", headers=headers())
    assert response.status_code == 200
    assert response.get_json() == {"total_count": 1, "data": [{"id": UUID}]}
    assert review.call == ("list", ("token", 2, 10, "in_review"))


def test_list_submissions_validates_pagination():
    client, _ = make_client()
    response = client.get("/api/v1/submissions?limit=101", headers=headers())
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_pagination"


def test_get_submission():
    client, review = make_client()
    response = client.get(f"/api/v1/submissions/{UUID}", headers=headers())
    assert response.status_code == 200
    assert review.call == ("detail", ("token", UUID))


def test_get_submission_rejects_non_uuid():
    client, _ = make_client()
    response = client.get("/api/v1/submissions/not-an-id", headers=headers())
    assert response.status_code == 400


def test_get_extracted_data():
    client, review = make_client()
    response = client.get(f"/api/v1/documents/{UUID}/extracted-data", headers=headers())
    assert response.status_code == 200
    assert response.get_json()["fields"] == []
    assert review.call == ("fields", ("token", UUID))


def test_review_field():
    client, review = make_client()
    response = client.put(
        f"/api/v1/fields/{UUID}/review",
        headers=headers(),
        json={
            "corrected_value": "$7,500.00",
            "review_status": "corrected",
            "review_notes": "Manual correction",
        },
    )
    assert response.status_code == 200
    assert review.call[0] == "review"
    assert review.call[1][0:2] == ("token", UUID)
    assert review.call[1][3] == "user-id"


def test_review_field_validates_payload():
    client, _ = make_client()
    response = client.put(
        f"/api/v1/fields/{UUID}/review",
        headers=headers(),
        json={"review_status": "corrected"},
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "corrected_value_required"


def test_service_errors_preserve_status_and_code():
    class Missing(Review):
        def get_submission(self, *_args):
            raise IntakeError("submission_not_found", "Submission not found.", 404)

    client, _ = make_client(Missing())
    response = client.get(f"/api/v1/submissions/{UUID}", headers=headers())
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "submission_not_found"


def test_routes_require_bearer_token():
    client, _ = make_client()
    response = client.get("/api/v1/submissions")
    assert response.status_code == 401
