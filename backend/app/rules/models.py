from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class FieldValue:
    field_id: str
    source_document_id: str
    field_key: str
    raw_value: str | None
    normalised_value: str | None
    applicant_number: int | None = None
    mapped_table: str | None = None
    mapped_column: str | None = None
    section_name: str | None = None
    field_label: str | None = None
    data_type: str | None = None

    @property
    def comparison_value(self) -> str | None:
        if self.normalised_value is not None:
            return self.normalised_value
        return self.raw_value


@dataclass(frozen=True)
class NormalizedAddress:
    normalised_text: str
    street_number: str | None
    postcode: str | None
    display_text: str


@dataclass(frozen=True)
class ApplicantRecord:
    applicant_number: int
    full_name: str | None
    name_field_key: str | None
    name_field: FieldValue | None = None


@dataclass(frozen=True)
class AddressRecord:
    applicant_number: int
    kind: str
    sequence: int | None
    street: str | None
    suburb: str | None
    state: str | None
    postcode: str | None
    field_keys: tuple[str, ...]
    assembled_raw: str | None


@dataclass(frozen=True)
class EmploymentRecord:
    applicant_number: int
    kind: str
    employer_name: str | None
    employer_name_field_key: str | None
    start_date: str | None
    start_date_field_key: str | None


@dataclass(frozen=True)
class RepaymentAccount:
    account_name: str | None
    account_name_field_key: str | None
    bsb: str | None
    bsb_field_key: str | None
    account_number: str | None
    account_number_field_key: str | None


@dataclass(frozen=True)
class SavingsAsset:
    sequence: int
    asset_type: str | None
    asset_type_field_key: str | None
    value: str | None
    value_field_key: str | None


@dataclass(frozen=True)
class ApplicantBinding:
    matched_applicant_numbers: tuple[int, ...]
    subject_field_key: str
    subject_value: str | None
    normalised_subject: str | None
    name_rule_status: str
    similarities: dict[int, Decimal] = field(default_factory=dict)


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    label: str
    status: str
    fact_find_field_keys: list[str]
    document_field_keys: list[str]
    fact_find_value: str | None
    document_value: str | None
    normalised_fact_find_value: str | None
    normalised_document_value: str | None
    comparison: dict[str, Any]
    message: str

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "label": self.label,
            "status": self.status,
            "fact_find_field_keys": list(self.fact_find_field_keys),
            "document_field_keys": list(self.document_field_keys),
            "fact_find_value": self.fact_find_value,
            "document_value": self.document_value,
            "normalised_fact_find_value": self.normalised_fact_find_value,
            "normalised_document_value": self.normalised_document_value,
            "comparison": dict(self.comparison),
            "message": self.message,
        }


@dataclass
class DocumentRuleBundle:
    document_type: str
    display_name: str
    source_document_id: str
    original_file_name: str | None
    matched_applicant_numbers: list[int]
    rules: list[RuleResult]

    def to_api_dict(self, score: int, status: str) -> dict[str, Any]:
        return {
            "document_type": self.document_type,
            "display_name": self.display_name,
            "source_document_id": self.source_document_id,
            "original_file_name": self.original_file_name,
            "matched_applicant_numbers": list(self.matched_applicant_numbers),
            "status": status,
            "score": score,
            "rules": [rule.to_api_dict() for rule in self.rules],
        }
