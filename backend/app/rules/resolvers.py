from __future__ import annotations

import re
from decimal import Decimal

from app.rules.models import (
    AddressRecord,
    ApplicantBinding,
    ApplicantRecord,
    EmploymentRecord,
    FieldValue,
    RepaymentAccount,
    SavingsAsset,
)
from app.rules.normalizers import normalize_name, similarity

DOCUMENT_SUBJECT_FIELDS = {
    "id_100": "full_legal_name",
    "payslip": "employee_name",
    "bank_statement_3m": "account_holder_name",
    "ato_notice": "taxpayer_name",
}

NAME_MATCH_THRESHOLD = Decimal("0.95")


def _fields_by_key(fields: list[FieldValue]) -> dict[str, FieldValue]:
    return {field.field_key: field for field in fields if field.field_key}


def _nonempty(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def resolve_applicants(fact_find_fields: list[FieldValue]) -> list[ApplicantRecord]:
    by_key = _fields_by_key(fact_find_fields)
    applicants: list[ApplicantRecord] = []
    for number in (1, 2):
        key = f"applicant_{number}_full_name"
        field = by_key.get(key)
        name = _nonempty(field.comparison_value) if field else None
        if name is None:
            continue
        applicants.append(
            ApplicantRecord(
                applicant_number=number,
                full_name=name,
                name_field_key=key,
                name_field=field,
            )
        )
    return applicants


def resolve_addresses(
    fact_find_fields: list[FieldValue], applicant_number: int
) -> list[AddressRecord]:
    by_key = _fields_by_key(fact_find_fields)
    addresses: list[AddressRecord] = []

    def _component(prefix: str, part: str) -> tuple[str, str | None]:
        key = f"{prefix}_{part}"
        field = by_key.get(key)
        return key, _nonempty(field.comparison_value) if field else None

    current_prefix = f"applicant_{applicant_number}_current_address"
    street_key, street = _component(current_prefix, "street")
    suburb_key, suburb = _component(current_prefix, "suburb")
    state_key, state = _component(current_prefix, "state")
    postcode_key, postcode = _component(current_prefix, "postcode")
    assembled = _assemble_address(street, suburb, state, postcode)
    if assembled:
        addresses.append(
            AddressRecord(
                applicant_number=applicant_number,
                kind="current",
                sequence=None,
                street=street,
                suburb=suburb,
                state=state,
                postcode=postcode,
                field_keys=(street_key, suburb_key, state_key, postcode_key),
                assembled_raw=assembled,
            )
        )

    previous_pattern = re.compile(
        rf"^applicant_{applicant_number}_previous_address_(\d+)_street$"
    )
    sequences = sorted(
        {
            int(match.group(1))
            for key in by_key
            for match in [previous_pattern.match(key)]
            if match
        }
    )
    for sequence in sequences:
        prefix = f"applicant_{applicant_number}_previous_address_{sequence}"
        street_key, street = _component(prefix, "street")
        suburb_key, suburb = _component(prefix, "suburb")
        state_key, state = _component(prefix, "state")
        postcode_key, postcode = _component(prefix, "postcode")
        assembled = _assemble_address(street, suburb, state, postcode)
        if not assembled:
            continue
        addresses.append(
            AddressRecord(
                applicant_number=applicant_number,
                kind="previous",
                sequence=sequence,
                street=street,
                suburb=suburb,
                state=state,
                postcode=postcode,
                field_keys=(street_key, suburb_key, state_key, postcode_key),
                assembled_raw=assembled,
            )
        )
    return addresses


def _assemble_address(
    street: str | None,
    suburb: str | None,
    state: str | None,
    postcode: str | None,
) -> str | None:
    parts = [part for part in (street, suburb, state, postcode) if part]
    return ", ".join(parts) if parts else None


def resolve_employments(
    fact_find_fields: list[FieldValue], applicant_number: int
) -> list[EmploymentRecord]:
    by_key = _fields_by_key(fact_find_fields)
    records: list[EmploymentRecord] = []
    for kind in ("current_employment", "secondary_employment"):
        name_key = f"applicant_{applicant_number}_{kind}_employer_name"
        start_key = f"applicant_{applicant_number}_{kind}_start_date"
        name_field = by_key.get(name_key)
        start_field = by_key.get(start_key)
        employer_name = _nonempty(name_field.comparison_value) if name_field else None
        start_date = _nonempty(start_field.comparison_value) if start_field else None
        if employer_name is None and start_date is None:
            continue
        records.append(
            EmploymentRecord(
                applicant_number=applicant_number,
                kind=kind,
                employer_name=employer_name,
                employer_name_field_key=name_key if name_field else None,
                start_date=start_date,
                start_date_field_key=start_key if start_field else None,
            )
        )
    return records


def resolve_repayment_account(fact_find_fields: list[FieldValue]) -> RepaymentAccount:
    by_key = _fields_by_key(fact_find_fields)

    def _value(key: str) -> tuple[str | None, str | None]:
        field = by_key.get(key)
        if not field:
            return None, None
        return _nonempty(field.comparison_value), key

    name, name_key = _value("repayment_account_name")
    bsb, bsb_key = _value("repayment_account_bsb")
    number, number_key = _value("repayment_account_number")
    return RepaymentAccount(
        account_name=name,
        account_name_field_key=name_key,
        bsb=bsb,
        bsb_field_key=bsb_key,
        account_number=number,
        account_number_field_key=number_key,
    )


def resolve_savings_assets(fact_find_fields: list[FieldValue]) -> list[SavingsAsset]:
    by_key = _fields_by_key(fact_find_fields)
    pattern = re.compile(r"^savings_term_deposit_(\d+)_value$")
    assets: list[SavingsAsset] = []
    sequences = sorted(
        {
            int(match.group(1))
            for key in by_key
            for match in [pattern.match(key)]
            if match
        }
    )
    for sequence in sequences:
        value_key = f"savings_term_deposit_{sequence}_value"
        type_key = f"savings_term_deposit_{sequence}_asset_type"
        value_field = by_key.get(value_key)
        type_field = by_key.get(type_key)
        value = _nonempty(value_field.comparison_value) if value_field else None
        asset_type = _nonempty(type_field.comparison_value) if type_field else None
        if value is None and asset_type is None:
            continue
        if value is None:
            continue
        assets.append(
            SavingsAsset(
                sequence=sequence,
                asset_type=asset_type,
                asset_type_field_key=type_key if type_field else None,
                value=value,
                value_field_key=value_key,
            )
        )
    return assets


def field_lookup(fields: list[FieldValue], key: str) -> FieldValue | None:
    for field in fields:
        if field.field_key == key:
            return field
    return None


def bind_document_to_applicant(
    document_type: str,
    fields: list[FieldValue],
    applicants: list[ApplicantRecord],
) -> ApplicantBinding:
    subject_key = DOCUMENT_SUBJECT_FIELDS[document_type]
    subject_field = field_lookup(fields, subject_key)
    subject_value = _nonempty(subject_field.comparison_value) if subject_field else None
    normalised_subject = normalize_name(subject_value)

    similarities: dict[int, Decimal] = {}
    for applicant in applicants:
        applicant_norm = normalize_name(applicant.full_name)
        if document_type == "bank_statement_3m":
            score = _bank_holder_similarity(normalised_subject, applicant_norm)
        else:
            score = similarity(applicant_norm, normalised_subject)
        similarities[applicant.applicant_number] = score

    matched = [
        number
        for number, score in similarities.items()
        if score >= NAME_MATCH_THRESHOLD
    ]
    matched.sort()

    if not matched:
        status = "fail"
    else:
        status = "pass"

    return ApplicantBinding(
        matched_applicant_numbers=tuple(matched),
        subject_field_key=subject_key,
        subject_value=subject_value,
        normalised_subject=normalised_subject,
        name_rule_status=status,
        similarities=similarities,
    )


def _bank_holder_similarity(
    holder_norm: str | None, applicant_norm: str | None
) -> Decimal:
    if holder_norm is None or applicant_norm is None:
        return Decimal("0.00")
    direct = similarity(holder_norm, applicant_norm)
    if direct >= NAME_MATCH_THRESHOLD:
        return direct
    if applicant_norm in holder_norm:
        return Decimal("1.00")
    # Allow joint holders separated by common joiners.
    parts = re.split(r"\s+(?:AND|&|/)\s+", holder_norm)
    best = direct
    for part in parts:
        best = max(best, similarity(part.strip(), applicant_norm))
    return best


def best_matching_applicant_number(binding: ApplicantBinding) -> int | None:
    if not binding.matched_applicant_numbers:
        return None
    if len(binding.matched_applicant_numbers) == 1:
        return binding.matched_applicant_numbers[0]
    return None
