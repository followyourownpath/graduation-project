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


class RulesEngine:
    def __init__(self):
        self.calls = []

    def assess(self, token, submission_id, assessed_by):
        self.calls.append(("assess", token, submission_id, assessed_by))
        report = {
            "assessment_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "submission_id": submission_id,
            "application_reference": "CRM-1",
            "customer_name": "Alice Smith",
            "assessment_status": "completed",
            "ruleset_version": "phase1-v1",
            "overall_risk_score": 25,
            "risk_level": "lower",
            "failed_document_count": 1,
            "total_scored_documents": 4,
            "assessed_at": "2026-08-02T10:30:00Z",
            "document_results": [
                {
                    "document_type": "id_100",
                    "display_name": "ID",
                    "source_document_id": "id-doc",
                    "original_file_name": "id.jpg",
                    "matched_applicant_numbers": [1],
                    "status": "fail",
                    "score": 25,
                    "rules": [{"rule_id": "FF-ID-001", "status": "fail"}],
                },
                {
                    "document_type": "payslip",
                    "display_name": "Payslip",
                    "source_document_id": "ps-doc",
                    "original_file_name": "ps.pdf",
                    "matched_applicant_numbers": [1],
                    "status": "pass",
                    "score": 0,
                    "rules": [{"rule_id": "FF-PS-001", "status": "pass"}],
                },
                {
                    "document_type": "bank_statement_3m",
                    "display_name": "Bank Statement",
                    "source_document_id": "bs-doc",
                    "original_file_name": "bs.pdf",
                    "matched_applicant_numbers": [1],
                    "status": "pass",
                    "score": 0,
                    "rules": [{"rule_id": "FF-BS-001", "status": "pass"}],
                },
                {
                    "document_type": "ato_notice",
                    "display_name": "NOA",
                    "source_document_id": "noa-doc",
                    "original_file_name": "noa.pdf",
                    "matched_applicant_numbers": [1],
                    "status": "pass",
                    "score": 0,
                    "rules": [{"rule_id": "FF-NOA-001", "status": "pass"}],
                },
            ],
        }
        return report, True

    def get_assessment(self, token, submission_id):
        self.calls.append(("get", token, submission_id))
        report, _ = self.assess(token, submission_id, "user-id")
        return report

    def validate_readiness(self, token, submission_id):
        self.calls.append(("ready", token, submission_id))
        return {}


def make_client(rules=None):
    rules = rules or RulesEngine()
    app = create_app(
        TestConfig,
        auth_service=Auth(),
        rules_engine_service=rules,
    )
    return app.test_client(), rules


def headers():
    return {"Authorization": "Bearer token"}


def test_risk_assessment_requires_bearer_token():
    client, _ = make_client()
    response = client.post(f"/api/v1/submissions/{UUID}/risk-assessment")
    assert response.status_code == 401


def test_risk_assessment_rejects_non_uuid():
    client, _ = make_client()
    response = client.post("/api/v1/submissions/not-an-id/risk-assessment", headers=headers())
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_submission_id"


def test_post_risk_assessment_shape():
    client, rules = make_client()
    response = client.post(f"/api/v1/submissions/{UUID}/risk-assessment", headers=headers())
    assert response.status_code == 201
    body = response.get_json()
    assert body["overall_risk_score"] == 25
    assert body["risk_level"] == "lower"
    assert body["ruleset_version"] == "phase1-v1"
    assert len(body["document_results"]) == 4
    assert rules.calls[0][0] == "assess"
    assert rules.calls[0][3] == "user-id"


def test_get_risk_assessment_shape():
    client, _ = make_client()
    response = client.get(f"/api/v1/submissions/{UUID}/risk-assessment", headers=headers())
    assert response.status_code == 200
    body = response.get_json()
    assert body["submission_id"] == UUID
    assert body["total_scored_documents"] == 4


def test_get_risk_assessment_not_found():
    class Missing(RulesEngine):
        def get_assessment(self, *_args):
            raise IntakeError("risk_assessment_not_found", "Risk assessment not found.", 404)

    client, _ = make_client(Missing())
    response = client.get(f"/api/v1/submissions/{UUID}/risk-assessment", headers=headers())
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "risk_assessment_not_found"


def test_post_readiness_conflict_includes_details():
    class Conflict(RulesEngine):
        def assess(self, *_args):
            raise IntakeError(
                "phase1_required_fields_missing",
                "The approved submission is missing fields required by Phase 1.",
                409,
                details={"bank_statement_3m": ["account_number"]},
            )

    client, _ = make_client(Conflict())
    response = client.post(f"/api/v1/submissions/{UUID}/risk-assessment", headers=headers())
    assert response.status_code == 409
    body = response.get_json()
    assert body["error"]["code"] == "phase1_required_fields_missing"
    assert body["error"]["details"]["bank_statement_3m"] == ["account_number"]


def test_approve_calls_readiness_validator():
    class Review:
        def update_submission_status(self, *args):
            return {"message": "Status updated successfully"}

    rules = RulesEngine()
    app = create_app(
        TestConfig,
        auth_service=Auth(),
        review_service=Review(),
        rules_engine_service=rules,
    )
    client = app.test_client()
    response = client.put(
        f"/api/v1/submissions/{UUID}/status",
        headers=headers(),
        json={"status": "approved"},
    )
    assert response.status_code == 200
    assert rules.calls[0][0] == "ready"
