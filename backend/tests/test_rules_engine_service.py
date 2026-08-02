from copy import deepcopy

from app.rules.models import FieldValue
from app.services.intake import IntakeError
from app.services.rules_engine import RulesEngineService


SUBMISSION_ID = "123e4567-e89b-12d3-a456-426614174000"
APP_ID = "123e4567-e89b-12d3-a456-426614174001"


def _field(key, value, doc_id="doc", applicant_number=None):
    return FieldValue(
        field_id=f"f-{key}",
        source_document_id=doc_id,
        field_key=key,
        raw_value=value,
        normalised_value=value,
        applicant_number=applicant_number,
    )


def _ready_fields():
    return {
        "fact_find": [
            _field("cover_form_date", "2024-01-15", doc_id="ff"),
            _field("applicant_1_full_name", "Alice Smith", doc_id="ff", applicant_number=1),
            _field("applicant_1_current_address_street", "12 Example Street", doc_id="ff", applicant_number=1),
            _field("applicant_1_current_address_suburb", "Sydney", doc_id="ff", applicant_number=1),
            _field("applicant_1_current_address_state", "NSW", doc_id="ff", applicant_number=1),
            _field("applicant_1_current_address_postcode", "2000", doc_id="ff", applicant_number=1),
            _field("applicant_1_current_employment_employer_name", "Example Pty Ltd", doc_id="ff", applicant_number=1),
            _field("applicant_1_current_employment_start_date", "2020-01-01", doc_id="ff", applicant_number=1),
            _field("repayment_account_name", "Alice Smith", doc_id="ff"),
            _field("repayment_account_bsb", "012345", doc_id="ff"),
            _field("repayment_account_number", "00012345", doc_id="ff"),
        ],
        "id_100": [
            _field("full_legal_name", "Alice Smith", doc_id="id"),
            _field("residential_address", "12 Example Street, Sydney NSW 2000", doc_id="id"),
            _field("expiry_date", "2026-01-01", doc_id="id"),
        ],
        "payslip": [
            _field("employee_name", "Alice Smith", doc_id="ps"),
            _field("employer_name", "Example", doc_id="ps"),
            _field("pay_period_end", "2024-01-31", doc_id="ps"),
        ],
        "bank_statement_3m": [
            _field("account_holder_name", "Alice Smith", doc_id="bs"),
            _field("bsb", "012345", doc_id="bs"),
            _field("account_number", "00012345", doc_id="bs"),
            _field("closing_balance", "100.00", doc_id="bs"),
        ],
        "ato_notice": [
            _field("taxpayer_name", "Alice Smith", doc_id="noa"),
        ],
    }


class FakeRepo:
    def __init__(self, status="approved", fields=None, duplicate_id=False, missing_job=False):
        self.status = status
        self.fields = fields or _ready_fields()
        self.duplicate_id = duplicate_id
        self.missing_job = missing_job
        self.assessments = {}
        self.upserts = []
        self.assessment_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    def get_submission(self, _token, submission_id):
        if submission_id != SUBMISSION_ID:
            return None
        return {
            "id": SUBMISSION_ID,
            "crm_application_id": APP_ID,
            "customer_name": "Alice Smith",
            "submission_status": self.status,
        }

    def get_application(self, _token, application_id):
        return {"id": application_id, "crm_application_id": "CRM-1", "loan_type": "purchase"}

    def get_documents(self, _token, _submission_id):
        docs = [
            {"id": "ff", "document_type": "fact_find", "original_file_name": "ff.pdf"},
            {"id": "id", "document_type": "id_100", "original_file_name": "id.jpg"},
            {"id": "ps", "document_type": "payslip", "original_file_name": "ps.pdf"},
            {"id": "bs", "document_type": "bank_statement_3m", "original_file_name": "bs.pdf"},
            {"id": "noa", "document_type": "ato_notice", "original_file_name": "noa.pdf"},
        ]
        if self.duplicate_id:
            docs.append({"id": "id-2", "document_type": "id_100", "original_file_name": "id2.jpg"})
        return docs

    def get_latest_completed_job(self, _token, document_id):
        if self.missing_job and document_id == "bs":
            return None
        return {"id": f"job-{document_id}", "source_document_id": document_id, "job_status": "completed"}

    def get_fields_for_job(self, _token, job_id):
        doc_id = job_id.replace("job-", "")
        mapping = {
            "ff": "fact_find",
            "id": "id_100",
            "ps": "payslip",
            "bs": "bank_statement_3m",
            "noa": "ato_notice",
        }
        return list(self.fields[mapping[doc_id]])

    def get_assessment(self, _token, submission_id):
        return self.assessments.get(submission_id)

    def get_assessments_by_submission_ids(self, _token, submission_ids):
        return {
            key: value
            for key, value in self.assessments.items()
            if key in submission_ids
        }

    def upsert_processing_assessment(self, _token, submission_id, assessed_by):
        row = {
            "id": self.assessment_id,
            "fact_find_submission_id": submission_id,
            "assessment_status": "processing",
            "assessed_by": assessed_by,
        }
        self.assessments[submission_id] = row
        self.upserts.append(("processing", deepcopy(row)))
        return row

    def complete_assessment(self, _token, submission_id, payload):
        row = {
            "id": self.assessment_id,
            "fact_find_submission_id": submission_id,
            "assessment_status": "completed",
            **payload,
        }
        self.assessments[submission_id] = row
        self.upserts.append(("completed", deepcopy(row)))
        return row

    def fail_assessment(self, _token, submission_id, error_message, assessed_by):
        row = {
            "id": self.assessment_id,
            "fact_find_submission_id": submission_id,
            "assessment_status": "failed",
            "error_message": error_message,
            "assessed_by": assessed_by,
        }
        self.assessments[submission_id] = row
        self.upserts.append(("failed", deepcopy(row)))
        return row


def test_assess_rejects_unapproved_without_writing():
    repo = FakeRepo(status="in_review")
    service = RulesEngineService(repo)
    try:
        service.assess("token", SUBMISSION_ID, "user-1")
        assert False, "expected IntakeError"
    except IntakeError as error:
        assert error.code == "submission_not_approved"
        assert error.status == 409
    assert repo.upserts == []


def test_assess_rejects_duplicate_document():
    repo = FakeRepo(duplicate_id=True)
    service = RulesEngineService(repo)
    try:
        service.assess("token", SUBMISSION_ID, "user-1")
        assert False
    except IntakeError as error:
        assert error.code == "phase1_duplicate_document_type"
        assert error.status == 409
    assert repo.upserts == []


def test_assess_rejects_incomplete_extraction():
    repo = FakeRepo(missing_job=True)
    service = RulesEngineService(repo)
    try:
        service.assess("token", SUBMISSION_ID, "user-1")
        assert False
    except IntakeError as error:
        assert error.code == "phase1_extraction_incomplete"
    assert repo.upserts == []


def test_assess_rejects_missing_required_fields():
    fields = _ready_fields()
    fields["bank_statement_3m"] = [
        field for field in fields["bank_statement_3m"] if field.field_key != "account_number"
    ]
    repo = FakeRepo(fields=fields)
    service = RulesEngineService(repo)
    try:
        service.assess("token", SUBMISSION_ID, "user-1")
        assert False
    except IntakeError as error:
        assert error.code == "phase1_required_fields_missing"
        assert "account_number" in error.details["bank_statement_3m"]
    assert repo.upserts == []


def test_assess_creates_and_overwrites_single_row():
    repo = FakeRepo()
    service = RulesEngineService(repo)
    first, created = service.assess("token", SUBMISSION_ID, "user-1")
    assert created is True
    assert first["overall_risk_score"] == 0
    assert first["risk_level"] == "low"
    assert len(first["document_results"]) == 4
    assert sum(len(doc["rules"]) for doc in first["document_results"]) == 13

    second, created_again = service.assess("token", SUBMISSION_ID, "user-1")
    assert created_again is False
    assert second["assessment_id"] == first["assessment_id"]
    completed = [item for item in repo.upserts if item[0] == "completed"]
    assert len(repo.assessments) == 1
    assert len(completed) >= 2


def test_get_assessment_not_found():
    repo = FakeRepo()
    service = RulesEngineService(repo)
    try:
        service.get_assessment("token", SUBMISSION_ID)
        assert False
    except IntakeError as error:
        assert error.code == "risk_assessment_not_found"
        assert error.status == 404


def test_rule_exception_marks_failed_without_leaking():
    fields = _ready_fields()
    fields["id_100"][2] = _field("expiry_date", "not-a-date", doc_id="id")
    repo = FakeRepo(fields=fields)
    service = RulesEngineService(repo)
    try:
        service.assess("token", SUBMISSION_ID, "user-1")
        assert False
    except IntakeError as error:
        assert error.code == "risk_assessment_failed"
        assert error.status == 500
        assert "not-a-date" not in error.message
    assert repo.assessments[SUBMISSION_ID]["assessment_status"] == "failed"
