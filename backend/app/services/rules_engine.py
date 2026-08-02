from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import requests

from app.rules.models import FieldValue
from app.rules.phase1 import PHASE1_RULE_IDS, RulesEvaluationError, evaluate_phase1
from app.rules.readiness import (
    validate_phase1_documents,
    validate_phase1_extractions,
    validate_phase1_required_fields,
)
from app.rules.scoring import (
    document_status_for_score,
    risk_level_for_score,
    score_assessment,
    score_document,
)
from app.services.intake import IntakeError

RULESET_VERSION = "phase1-v1"
FIELD_SELECT = (
    "id,source_document_id,section_name,applicant_number,field_key,field_label,"
    "raw_value,normalised_value,data_type,confidence,mapped_table,mapped_column,"
    "review_status"
)
SCORED_DOCUMENT_TYPES = (
    "id_100",
    "payslip",
    "bank_statement_3m",
    "ato_notice",
)


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_uuid(value: str) -> None:
    try:
        UUID(str(value))
    except (ValueError, TypeError) as error:
        raise IntakeError(
            "invalid_submission_id",
            "submission_id must be a UUID.",
            400,
        ) from error


class SupabaseRulesEngineRepository:
    def __init__(self, supabase_url, publishable_key, timeout_seconds=20.0):
        self._url = supabase_url.rstrip("/")
        self._key = publishable_key
        self._timeout = timeout_seconds

    def get_submission(self, token, submission_id):
        response = self._request(
            "get",
            "/rest/v1/fact_find_submission",
            token,
            params={
                "select": (
                    "id,crm_application_id,customer_name,submission_status,"
                    "extraction_status,created_at,source_channel,intake_source"
                ),
                "id": f"eq.{submission_id}",
                "limit": "1",
            },
        )
        self._require_ok(response, "risk_assessment_storage_failed")
        rows = response.json()
        return rows[0] if rows else None

    def get_application(self, token, application_id):
        if not application_id:
            return {}
        response = self._request(
            "get",
            "/rest/v1/crm_application",
            token,
            params={
                "select": "id,loan_type,crm_application_id",
                "id": f"eq.{application_id}",
                "limit": "1",
            },
        )
        self._require_ok(response, "risk_assessment_storage_failed")
        rows = response.json()
        return rows[0] if rows else {}

    def get_documents(self, token, submission_id):
        response = self._request(
            "get",
            "/rest/v1/source_document",
            token,
            params={
                "select": "id,original_file_name,document_type,processing_status,created_at",
                "fact_find_submission_id": f"eq.{submission_id}",
                "order": "created_at.asc",
            },
        )
        self._require_ok(response, "risk_assessment_storage_failed")
        return response.json()

    def get_latest_completed_job(self, token, document_id):
        response = self._request(
            "get",
            "/rest/v1/ocr_extraction_job",
            token,
            params={
                "select": "id,source_document_id,job_status,completed_at",
                "source_document_id": f"eq.{document_id}",
                "job_status": "eq.completed",
                "order": "completed_at.desc",
                "limit": "1",
            },
        )
        self._require_ok(response, "risk_assessment_storage_failed")
        rows = response.json()
        return rows[0] if rows else None

    def get_fields_for_job(self, token, job_id):
        response = self._request(
            "get",
            "/rest/v1/extracted_field",
            token,
            params={
                "select": FIELD_SELECT,
                "ocr_extraction_job_id": f"eq.{job_id}",
                "order": "created_at.asc",
            },
        )
        self._require_ok(response, "risk_assessment_storage_failed")
        return [self._to_field_value(row) for row in response.json()]

    def get_assessment(self, token, submission_id):
        response = self._request(
            "get",
            "/rest/v1/risk_assessment",
            token,
            params={
                "select": "*",
                "fact_find_submission_id": f"eq.{submission_id}",
                "limit": "1",
            },
        )
        self._require_ok(response, "risk_assessment_storage_failed")
        rows = response.json()
        return rows[0] if rows else None

    def get_assessments_by_submission_ids(self, token, submission_ids):
        ids = [value for value in dict.fromkeys(submission_ids) if value]
        if not ids:
            return {}
        response = self._request(
            "get",
            "/rest/v1/risk_assessment",
            token,
            params={
                "select": (
                    "id,fact_find_submission_id,assessment_status,overall_risk_score,"
                    "risk_level,assessed_at"
                ),
                "fact_find_submission_id": f"in.({','.join(ids)})",
            },
        )
        self._require_ok(response, "risk_assessment_storage_failed")
        return {row["fact_find_submission_id"]: row for row in response.json()}

    def upsert_processing_assessment(self, token, submission_id, assessed_by):
        payload = {
            "fact_find_submission_id": submission_id,
            "assessment_status": "processing",
            "overall_risk_score": None,
            "risk_level": None,
            "id_score": None,
            "payslip_score": None,
            "bank_statement_score": None,
            "noa_score": None,
            "ruleset_version": RULESET_VERSION,
            "report_json": {},
            "assessed_by": assessed_by,
            "assessed_at": None,
            "error_message": None,
        }
        return self._upsert_assessment(token, payload)

    def complete_assessment(self, token, submission_id, payload):
        body = {
            "fact_find_submission_id": submission_id,
            "assessment_status": "completed",
            "error_message": None,
            **payload,
        }
        return self._upsert_assessment(token, body)

    def fail_assessment(self, token, submission_id, error_message, assessed_by):
        payload = {
            "fact_find_submission_id": submission_id,
            "assessment_status": "failed",
            "overall_risk_score": None,
            "risk_level": None,
            "id_score": None,
            "payslip_score": None,
            "bank_statement_score": None,
            "noa_score": None,
            "ruleset_version": RULESET_VERSION,
            "report_json": {},
            "assessed_by": assessed_by,
            "assessed_at": None,
            "error_message": error_message,
        }
        return self._upsert_assessment(token, payload)

    def _upsert_assessment(self, token, payload):
        response = self._request(
            "post",
            "/rest/v1/risk_assessment",
            token,
            params={"on_conflict": "fact_find_submission_id"},
            extra_headers={
                "Prefer": "resolution=merge-duplicates,return=representation",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        self._require_ok(response, "risk_assessment_storage_failed")
        rows = response.json()
        if not rows:
            raise IntakeError(
                "risk_assessment_storage_failed",
                "Supabase could not complete this operation.",
                502,
            )
        return rows[0]

    @staticmethod
    def _to_field_value(row: dict) -> FieldValue:
        return FieldValue(
            field_id=row["id"],
            source_document_id=row.get("source_document_id") or "",
            field_key=row.get("field_key") or "",
            raw_value=row.get("raw_value"),
            normalised_value=row.get("normalised_value"),
            applicant_number=row.get("applicant_number"),
            mapped_table=row.get("mapped_table"),
            mapped_column=row.get("mapped_column"),
            section_name=row.get("section_name"),
            field_label=row.get("field_label"),
            data_type=row.get("data_type"),
        )

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
                "supabase_unavailable",
                "Supabase is unavailable.",
                503,
            ) from error

    @staticmethod
    def _require_ok(response, code):
        if response.status_code in (401, 403):
            raise IntakeError(code, "Supabase denied this operation.", 403)
        if not response.ok:
            raise IntakeError(code, "Supabase could not complete this operation.", 502)


class RulesEngineService:
    def __init__(self, repository):
        self._repo = repository

    def validate_readiness(self, token, submission_id):
        _require_uuid(submission_id)
        submission = self._repo.get_submission(token, submission_id)
        if not submission:
            raise IntakeError("submission_not_found", "Submission not found.", 404)
        return self._load_ready_context(token, submission)

    def assess(self, token, submission_id, assessed_by):
        _require_uuid(submission_id)
        submission = self._repo.get_submission(token, submission_id)
        if not submission:
            raise IntakeError("submission_not_found", "Submission not found.", 404)
        if submission.get("submission_status") != "approved":
            raise IntakeError(
                "submission_not_approved",
                "Only approved submissions can be assessed.",
                409,
            )

        context = self._load_ready_context(token, submission)
        existing = self._repo.get_assessment(token, submission_id)
        created = existing is None

        processing_row = self._repo.upsert_processing_assessment(
            token, submission_id, assessed_by
        )
        try:
            bundles = evaluate_phase1(
                fact_find_fields=context["fields_by_type"]["fact_find"],
                documents=context["documents_by_type"],
                fields_by_type=context["fields_by_type"],
            )
            document_scores = {
                bundle.document_type: score_document(bundle.rules) for bundle in bundles
            }
            overall = score_assessment(document_scores)
            risk_level = risk_level_for_score(overall)
            assessed_at = _now()
            report = self._build_report(
                assessment_id=processing_row["id"],
                submission=submission,
                application=context["application"],
                bundles=bundles,
                document_scores=document_scores,
                overall=overall,
                risk_level=risk_level,
                assessed_at=assessed_at,
                assessment_status="completed",
            )
            row = self._repo.complete_assessment(
                token,
                submission_id,
                {
                    "overall_risk_score": overall,
                    "risk_level": risk_level,
                    "id_score": document_scores["id_100"],
                    "payslip_score": document_scores["payslip"],
                    "bank_statement_score": document_scores["bank_statement_3m"],
                    "noa_score": document_scores["ato_notice"],
                    "ruleset_version": RULESET_VERSION,
                    "report_json": report,
                    "assessed_by": assessed_by,
                    "assessed_at": assessed_at,
                },
            )
            report["assessment_id"] = row["id"]
            return report, created
        except RulesEvaluationError as error:
            self._safe_fail(token, submission_id, str(error), assessed_by)
            raise IntakeError(
                "risk_assessment_failed",
                "Risk assessment could not be completed.",
                500,
            ) from error
        except IntakeError:
            raise
        except Exception as error:
            self._safe_fail(
                token,
                submission_id,
                "Unexpected rules engine failure.",
                assessed_by,
            )
            raise IntakeError(
                "risk_assessment_failed",
                "Risk assessment could not be completed.",
                500,
            ) from error

    def get_assessment(self, token, submission_id):
        _require_uuid(submission_id)
        submission = self._repo.get_submission(token, submission_id)
        if not submission:
            raise IntakeError("submission_not_found", "Submission not found.", 404)
        row = self._repo.get_assessment(token, submission_id)
        if not row or row.get("assessment_status") != "completed":
            raise IntakeError(
                "risk_assessment_not_found",
                "Risk assessment not found.",
                404,
            )
        report = dict(row.get("report_json") or {})
        report["assessment_id"] = row["id"]
        report["assessment_status"] = "completed"
        return report

    def _load_ready_context(self, token, submission):
        documents = self._repo.get_documents(token, submission["id"])
        jobs_by_document_id = {
            document["id"]: self._repo.get_latest_completed_job(token, document["id"])
            for document in documents
        }
        documents_by_type = validate_phase1_documents(documents)
        validate_phase1_extractions(documents_by_type, jobs_by_document_id)

        fields_by_type: dict[str, list[FieldValue]] = {}
        for doc_type, document in documents_by_type.items():
            job = jobs_by_document_id[document["id"]]
            fields_by_type[doc_type] = self._repo.get_fields_for_job(token, job["id"])

        validate_phase1_required_fields(fields_by_type)
        application = self._repo.get_application(
            token, submission.get("crm_application_id")
        )
        return {
            "submission": submission,
            "application": application,
            "documents_by_type": documents_by_type,
            "fields_by_type": fields_by_type,
        }

    def _safe_fail(self, token, submission_id, error_message, assessed_by):
        try:
            self._repo.fail_assessment(token, submission_id, error_message, assessed_by)
        except IntakeError:
            pass

    @staticmethod
    def _build_report(
        *,
        assessment_id,
        submission,
        application,
        bundles,
        document_scores,
        overall,
        risk_level,
        assessed_at,
        assessment_status,
    ):
        document_results = []
        for bundle in bundles:
            score = document_scores[bundle.document_type]
            document_results.append(
                bundle.to_api_dict(score, document_status_for_score(score))
            )

        failed_document_count = sum(
            1 for score in document_scores.values() if score > 0
        )
        application_reference = (
            application.get("crm_application_id")
            or application.get("id")
            or submission.get("crm_application_id")
            or submission["id"]
        )
        rule_count = sum(len(bundle.rules) for bundle in bundles)
        if rule_count != len(PHASE1_RULE_IDS):
            raise RulesEvaluationError(
                f"Expected {len(PHASE1_RULE_IDS)} rules, got {rule_count}."
            )

        return {
            "assessment_id": assessment_id,
            "submission_id": submission["id"],
            "application_reference": application_reference,
            "customer_name": submission.get("customer_name"),
            "assessment_status": assessment_status,
            "ruleset_version": RULESET_VERSION,
            "overall_risk_score": overall,
            "risk_level": risk_level,
            "failed_document_count": failed_document_count,
            "total_scored_documents": len(SCORED_DOCUMENT_TYPES),
            "assessed_at": assessed_at,
            "document_results": document_results,
        }
