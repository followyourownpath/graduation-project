from __future__ import annotations

from app.rules.models import FieldValue
from app.rules.resolvers import resolve_applicants
from app.services.intake import IntakeError

PHASE1_DOCUMENT_TYPES = (
    "fact_find",
    "id_100",
    "payslip",
    "bank_statement_3m",
    "ato_notice",
)

REQUIRED_FIELDS = {
    "fact_find": ("cover_form_date",),
    "id_100": ("full_legal_name", "residential_address", "expiry_date"),
    "payslip": ("employee_name", "employer_name", "pay_period_end"),
    "bank_statement_3m": (
        "account_holder_name",
        "bsb",
        "account_number",
        "closing_balance",
    ),
    "ato_notice": ("taxpayer_name",),
}

DOCUMENT_DISPLAY = {
    "fact_find": "Fact Find",
    "id_100": "ID",
    "payslip": "Payslip",
    "bank_statement_3m": "Bank Statement",
    "ato_notice": "NOA",
}


def _nonempty(value: str | None) -> bool:
    return value is not None and str(value).strip() != ""


def _field_map(fields: list[FieldValue]) -> dict[str, FieldValue]:
    return {field.field_key: field for field in fields if field.field_key}


def validate_phase1_documents(
    documents: list[dict],
) -> dict[str, dict]:
    """Ensure exactly one document per Phase 1 type. Returns map type -> document."""
    by_type: dict[str, list[dict]] = {doc_type: [] for doc_type in PHASE1_DOCUMENT_TYPES}
    for document in documents:
        doc_type = document.get("document_type")
        if doc_type in by_type:
            by_type[doc_type].append(document)

    missing = [
        doc_type for doc_type in PHASE1_DOCUMENT_TYPES if len(by_type[doc_type]) == 0
    ]
    duplicates = [
        doc_type for doc_type in PHASE1_DOCUMENT_TYPES if len(by_type[doc_type]) > 1
    ]
    if missing:
        raise IntakeError(
            "phase1_documents_missing",
            "The submission is missing documents required by Phase 1.",
            409,
            details={"missing_document_types": missing},
        )
    if duplicates:
        raise IntakeError(
            "phase1_duplicate_document_type",
            "Phase 1 requires exactly one document of each required type.",
            409,
            details={"duplicate_document_types": duplicates},
        )
    return {doc_type: rows[0] for doc_type, rows in by_type.items()}


def validate_phase1_extractions(
    documents_by_type: dict[str, dict],
    jobs_by_document_id: dict[str, dict | None],
) -> None:
    incomplete = []
    for doc_type, document in documents_by_type.items():
        job = jobs_by_document_id.get(document["id"])
        if not job:
            incomplete.append(doc_type)
    if incomplete:
        raise IntakeError(
            "phase1_extraction_incomplete",
            "One or more Phase 1 documents do not have a completed OCR job.",
            409,
            details={"incomplete_document_types": incomplete},
        )


def validate_phase1_required_fields(
    fields_by_type: dict[str, list[FieldValue]],
) -> None:
    missing: dict[str, list[str]] = {}

    fact_find_fields = fields_by_type.get("fact_find", [])
    applicants = resolve_applicants(fact_find_fields)
    if not any(applicant.applicant_number == 1 for applicant in applicants):
        missing.setdefault("fact_find", []).append("applicant_1_full_name")

    for doc_type, required_keys in REQUIRED_FIELDS.items():
        field_map = _field_map(fields_by_type.get(doc_type, []))
        for key in required_keys:
            field = field_map.get(key)
            if field is None or not _nonempty(field.comparison_value):
                missing.setdefault(doc_type, []).append(key)

    if missing:
        raise IntakeError(
            "phase1_required_fields_missing",
            "The approved submission is missing fields required by Phase 1.",
            409,
            details=missing,
        )


def validate_phase1_readiness(
    *,
    documents: list[dict],
    jobs_by_document_id: dict[str, dict | None],
    fields_by_type: dict[str, list[FieldValue]],
) -> dict[str, dict]:
    """Shared Approval / Rules Engine readiness gate.

    Returns the validated documents_by_type mapping.
    """
    documents_by_type = validate_phase1_documents(documents)
    validate_phase1_extractions(documents_by_type, jobs_by_document_id)
    validate_phase1_required_fields(fields_by_type)
    return documents_by_type
