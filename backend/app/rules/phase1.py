from __future__ import annotations

import re
from decimal import Decimal

from app.rules.models import (
    AddressRecord,
    ApplicantBinding,
    ApplicantRecord,
    DocumentRuleBundle,
    EmploymentRecord,
    FieldValue,
    RuleResult,
    SavingsAsset,
)
from app.rules.normalizers import (
    format_money,
    normalize_address,
    normalize_entity,
    normalize_identifier,
    normalize_name,
    parse_iso_date,
    parse_money,
    relative_difference,
    similarity,
)
from app.rules.resolvers import (
    bind_document_to_applicant,
    field_lookup,
    resolve_addresses,
    resolve_applicants,
    resolve_employments,
    resolve_repayment_account,
    resolve_savings_assets,
)

PHASE1_RULE_IDS = (
    "FF-ID-001",
    "FF-ID-002",
    "FF-ID-003",
    "FF-PS-001",
    "FF-PS-002",
    "FF-PS-003",
    "FF-BS-001",
    "FF-BS-002",
    "FF-BS-003",
    "FF-BS-004",
    "FF-BS-006",
    "FF-NOA-001",
    "FF-NOA-002",
)

RULE_LABELS = {
    "FF-ID-001": "Applicant name matches ID",
    "FF-ID-002": "Applicant address matches ID",
    "FF-ID-003": "ID is valid on Fact Find cover date",
    "FF-PS-001": "Applicant name matches payslip",
    "FF-PS-002": "Employer name matches payslip",
    "FF-PS-003": "Payslip pay period is after employment start",
    "FF-BS-001": "Account holder matches an applicant",
    "FF-BS-002": "Repayment account name matches bank holder",
    "FF-BS-003": "Repayment BSB matches bank statement",
    "FF-BS-004": "Repayment account number matches bank statement",
    "FF-BS-006": "Declared savings balance matches bank closing balance",
    "FF-NOA-001": "Applicant name matches NOA",
    "FF-NOA-002": "Applicant address matches NOA",
}

DOCUMENT_DISPLAY = {
    "id_100": "ID",
    "payslip": "Payslip",
    "bank_statement_3m": "Bank Statement",
    "ato_notice": "NOA",
}

NAME_THRESHOLD = Decimal("0.95")
ENTITY_THRESHOLD = Decimal("0.90")
ADDRESS_THRESHOLD = Decimal("0.90")
SAVINGS_RELATIVE_THRESHOLD = Decimal("0.10")
TERM_DEPOSIT_ABSOLUTE_THRESHOLD = Decimal("1.00")


class RulesEvaluationError(Exception):
    """Raised when approved inputs cannot be evaluated deterministically."""


def evaluate_phase1(
    *,
    fact_find_fields: list[FieldValue],
    documents: dict[str, dict],
    fields_by_type: dict[str, list[FieldValue]],
) -> list[DocumentRuleBundle]:
    applicants = resolve_applicants(fact_find_fields)
    cover_date_field = field_lookup(fact_find_fields, "cover_form_date")
    repayment = resolve_repayment_account(fact_find_fields)
    savings = resolve_savings_assets(fact_find_fields)

    bundles: list[DocumentRuleBundle] = []

    id_doc = documents["id_100"]
    id_fields = fields_by_type["id_100"]
    id_binding = bind_document_to_applicant("id_100", id_fields, applicants)
    bundles.append(
        DocumentRuleBundle(
            document_type="id_100",
            display_name=DOCUMENT_DISPLAY["id_100"],
            source_document_id=id_doc["id"],
            original_file_name=id_doc.get("original_file_name"),
            matched_applicant_numbers=list(id_binding.matched_applicant_numbers),
            rules=_evaluate_id_rules(
                applicants=applicants,
                binding=id_binding,
                fact_find_fields=fact_find_fields,
                id_fields=id_fields,
                cover_date_field=cover_date_field,
            ),
        )
    )

    payslip_doc = documents["payslip"]
    payslip_fields = fields_by_type["payslip"]
    payslip_binding = bind_document_to_applicant("payslip", payslip_fields, applicants)
    bundles.append(
        DocumentRuleBundle(
            document_type="payslip",
            display_name=DOCUMENT_DISPLAY["payslip"],
            source_document_id=payslip_doc["id"],
            original_file_name=payslip_doc.get("original_file_name"),
            matched_applicant_numbers=list(payslip_binding.matched_applicant_numbers),
            rules=_evaluate_payslip_rules(
                applicants=applicants,
                binding=payslip_binding,
                fact_find_fields=fact_find_fields,
                payslip_fields=payslip_fields,
            ),
        )
    )

    bank_doc = documents["bank_statement_3m"]
    bank_fields = fields_by_type["bank_statement_3m"]
    bank_binding = bind_document_to_applicant(
        "bank_statement_3m", bank_fields, applicants
    )
    bundles.append(
        DocumentRuleBundle(
            document_type="bank_statement_3m",
            display_name=DOCUMENT_DISPLAY["bank_statement_3m"],
            source_document_id=bank_doc["id"],
            original_file_name=bank_doc.get("original_file_name"),
            matched_applicant_numbers=list(bank_binding.matched_applicant_numbers),
            rules=_evaluate_bank_rules(
                applicants=applicants,
                binding=bank_binding,
                repayment=repayment,
                savings=savings,
                bank_fields=bank_fields,
            ),
        )
    )

    noa_doc = documents["ato_notice"]
    noa_fields = fields_by_type["ato_notice"]
    noa_binding = bind_document_to_applicant("ato_notice", noa_fields, applicants)
    bundles.append(
        DocumentRuleBundle(
            document_type="ato_notice",
            display_name=DOCUMENT_DISPLAY["ato_notice"],
            source_document_id=noa_doc["id"],
            original_file_name=noa_doc.get("original_file_name"),
            matched_applicant_numbers=list(noa_binding.matched_applicant_numbers),
            rules=_evaluate_noa_rules(
                applicants=applicants,
                binding=noa_binding,
                fact_find_fields=fact_find_fields,
                noa_fields=noa_fields,
            ),
        )
    )
    return bundles


def _rule(
    rule_id: str,
    status: str,
    *,
    fact_find_field_keys: list[str] | None = None,
    document_field_keys: list[str] | None = None,
    fact_find_value: str | None = None,
    document_value: str | None = None,
    normalised_fact_find_value: str | None = None,
    normalised_document_value: str | None = None,
    comparison: dict | None = None,
    message: str,
) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        label=RULE_LABELS[rule_id],
        status=status,
        fact_find_field_keys=fact_find_field_keys or [],
        document_field_keys=document_field_keys or [],
        fact_find_value=fact_find_value,
        document_value=document_value,
        normalised_fact_find_value=normalised_fact_find_value,
        normalised_document_value=normalised_document_value,
        comparison=comparison or {},
        message=message,
    )


def _incomplete(rule_id: str, message: str, **kwargs) -> RuleResult:
    return _rule(rule_id, "incomplete", message=message, **kwargs)


def _name_rule(
    rule_id: str,
    *,
    applicants: list[ApplicantRecord],
    binding: ApplicantBinding,
    fail_message: str,
    pass_message: str,
) -> RuleResult:
    best_number = None
    best_score = Decimal("0.00")
    for number, score in binding.similarities.items():
        if score >= best_score:
            best_score = score
            best_number = number
    applicant = next(
        (item for item in applicants if item.applicant_number == best_number),
        applicants[0] if applicants else None,
    )
    fact_keys = [applicant.name_field_key] if applicant and applicant.name_field_key else []
    fact_value = applicant.full_name if applicant else None
    fact_norm = normalize_name(fact_value)
    status = binding.name_rule_status
    return _rule(
        rule_id,
        status,
        fact_find_field_keys=fact_keys,
        document_field_keys=[binding.subject_field_key],
        fact_find_value=fact_value,
        document_value=binding.subject_value,
        normalised_fact_find_value=fact_norm,
        normalised_document_value=binding.normalised_subject,
        comparison={
            "operator": "name_similarity",
            "similarity": float(best_score),
            "threshold": float(NAME_THRESHOLD),
            "matched_applicant_numbers": list(binding.matched_applicant_numbers),
        },
        message=pass_message if status == "pass" else fail_message,
    )


def _applicant_numbers_for_rules(binding: ApplicantBinding) -> list[int]:
    return list(binding.matched_applicant_numbers)


def _evaluate_id_rules(
    *,
    applicants: list[ApplicantRecord],
    binding: ApplicantBinding,
    fact_find_fields: list[FieldValue],
    id_fields: list[FieldValue],
    cover_date_field: FieldValue | None,
) -> list[RuleResult]:
    name_result = _name_rule(
        "FF-ID-001",
        applicants=applicants,
        binding=binding,
        fail_message="Applicant name does not match ID.",
        pass_message="Applicant name matches ID.",
    )
    results = [name_result]
    matched = _applicant_numbers_for_rules(binding)
    if not matched:
        results.append(
            _incomplete(
                "FF-ID-002",
                "Address comparison skipped because the ID could not be bound to an applicant.",
                document_field_keys=["residential_address"],
            )
        )
        results.append(
            _incomplete(
                "FF-ID-003",
                "Expiry comparison skipped because the ID could not be bound to an applicant.",
                document_field_keys=["expiry_date"],
            )
        )
        return results

    results.append(
        _compare_addresses(
            "FF-ID-002",
            applicants=applicants,
            matched_numbers=matched,
            fact_find_fields=fact_find_fields,
            document_field=field_lookup(id_fields, "residential_address"),
            document_field_key="residential_address",
            fail_message="Applicant address does not match ID.",
            pass_message="Applicant address matches ID.",
            allow_missing_document_address=False,
        )
    )
    results.append(
        _compare_id_expiry(
            cover_date_field=cover_date_field,
            expiry_field=field_lookup(id_fields, "expiry_date"),
        )
    )
    return results


def _evaluate_payslip_rules(
    *,
    applicants: list[ApplicantRecord],
    binding: ApplicantBinding,
    fact_find_fields: list[FieldValue],
    payslip_fields: list[FieldValue],
) -> list[RuleResult]:
    name_result = _name_rule(
        "FF-PS-001",
        applicants=applicants,
        binding=binding,
        fail_message="Applicant name does not match payslip.",
        pass_message="Applicant name matches payslip.",
    )
    results = [name_result]
    matched = _applicant_numbers_for_rules(binding)
    if not matched:
        results.append(
            _incomplete(
                "FF-PS-002",
                "Employer comparison skipped because the payslip could not be bound to an applicant.",
                document_field_keys=["employer_name"],
            )
        )
        results.append(
            _incomplete(
                "FF-PS-003",
                "Employment start comparison skipped because the payslip could not be bound to an applicant.",
                document_field_keys=["pay_period_end"],
            )
        )
        return results

    employer_field = field_lookup(payslip_fields, "employer_name")
    pay_period_field = field_lookup(payslip_fields, "pay_period_end")
    employer_result, selected_employment = _compare_employer(
        matched_numbers=matched,
        fact_find_fields=fact_find_fields,
        employer_field=employer_field,
    )
    results.append(employer_result)
    results.append(
        _compare_employment_start(
            selected_employment=selected_employment,
            pay_period_field=pay_period_field,
            employer_status=employer_result.status,
        )
    )
    return results


def _evaluate_bank_rules(
    *,
    applicants: list[ApplicantRecord],
    binding: ApplicantBinding,
    repayment,
    savings: list[SavingsAsset],
    bank_fields: list[FieldValue],
) -> list[RuleResult]:
    name_result = _name_rule(
        "FF-BS-001",
        applicants=applicants,
        binding=binding,
        fail_message="Account holder name does not match a Fact Find applicant.",
        pass_message="Account holder name matches a Fact Find applicant.",
    )
    holder_field = field_lookup(bank_fields, "account_holder_name")
    bsb_field = field_lookup(bank_fields, "bsb")
    account_field = field_lookup(bank_fields, "account_number")
    closing_field = field_lookup(bank_fields, "closing_balance")

    name_match = _compare_repayment_name(repayment=repayment, holder_field=holder_field)
    bsb_match = _compare_bsb(repayment=repayment, bsb_field=bsb_field)
    account_match = _compare_account_number(
        repayment=repayment,
        account_field=account_field,
        name_passed=name_match.status == "pass",
        bsb_passed=bsb_match.status == "pass",
    )
    savings_match = _compare_savings(
        savings=savings,
        closing_field=closing_field,
    )
    return [name_result, name_match, bsb_match, account_match, savings_match]


def _evaluate_noa_rules(
    *,
    applicants: list[ApplicantRecord],
    binding: ApplicantBinding,
    fact_find_fields: list[FieldValue],
    noa_fields: list[FieldValue],
) -> list[RuleResult]:
    name_result = _name_rule(
        "FF-NOA-001",
        applicants=applicants,
        binding=binding,
        fail_message="Applicant name does not match NOA.",
        pass_message="Applicant name matches NOA.",
    )
    results = [name_result]
    matched = _applicant_numbers_for_rules(binding)
    if not matched:
        results.append(
            _incomplete(
                "FF-NOA-002",
                "Address comparison skipped because the NOA could not be bound to an applicant.",
                document_field_keys=["taxpayer_address"],
            )
        )
        return results

    address_field = field_lookup(noa_fields, "taxpayer_address")
    results.append(
        _compare_addresses(
            "FF-NOA-002",
            applicants=applicants,
            matched_numbers=matched,
            fact_find_fields=fact_find_fields,
            document_field=address_field,
            document_field_key="taxpayer_address",
            fail_message="Applicant address does not match NOA.",
            pass_message="Applicant address matches NOA.",
            allow_missing_document_address=True,
        )
    )
    return results


def _compare_addresses(
    rule_id: str,
    *,
    applicants: list[ApplicantRecord],
    matched_numbers: list[int],
    fact_find_fields: list[FieldValue],
    document_field: FieldValue | None,
    document_field_key: str,
    fail_message: str,
    pass_message: str,
    allow_missing_document_address: bool,
) -> RuleResult:
    document_raw = document_field.comparison_value if document_field else None
    if not document_raw or not str(document_raw).strip():
        if allow_missing_document_address:
            return _rule(
                rule_id,
                "not_applicable",
                document_field_keys=[document_field_key],
                message="NOA address is not present.",
            )
        return _incomplete(
            rule_id,
            "Document address is missing.",
            document_field_keys=[document_field_key],
        )

    document_norm = normalize_address(document_raw)
    best = None
    for number in matched_numbers:
        for address in resolve_addresses(fact_find_fields, number):
            candidate = _address_similarity(address, document_norm)
            if best is None or candidate["similarity"] > best["similarity"]:
                best = candidate
                best["applicant_number"] = number
                best["address"] = address

    if best is None:
        return _incomplete(
            rule_id,
            "No Fact Find address is available for the matched applicant.",
            document_field_keys=[document_field_key],
            document_value=document_raw,
            normalised_document_value=document_norm.normalised_text if document_norm else None,
        )

    address: AddressRecord = best["address"]
    status = "pass" if best["passed"] else "fail"
    return _rule(
        rule_id,
        status,
        fact_find_field_keys=list(address.field_keys),
        document_field_keys=[document_field_key],
        fact_find_value=address.assembled_raw,
        document_value=document_raw,
        normalised_fact_find_value=best["fact_find_normalised"],
        normalised_document_value=document_norm.normalised_text if document_norm else None,
        comparison={
            "operator": "address_similarity",
            "similarity": float(best["similarity"]),
            "threshold": float(ADDRESS_THRESHOLD),
            "street_number_match": best["street_number_match"],
            "postcode_match": best["postcode_match"],
            "matched_applicant_number": best["applicant_number"],
        },
        message=pass_message if status == "pass" else fail_message,
    )


def _address_similarity(address: AddressRecord, document_norm) -> dict:
    fact_norm = normalize_address(address.assembled_raw)
    if fact_norm is None or document_norm is None:
        return {
            "similarity": Decimal("0.00"),
            "passed": False,
            "street_number_match": False,
            "postcode_match": False,
            "fact_find_normalised": None,
        }
    street_ok = True
    if fact_norm.street_number and document_norm.street_number:
        street_ok = fact_norm.street_number == document_norm.street_number
    postcode_ok = True
    if fact_norm.postcode and document_norm.postcode:
        postcode_ok = fact_norm.postcode == document_norm.postcode
    score = similarity(fact_norm.normalised_text, document_norm.normalised_text)
    passed = street_ok and postcode_ok and score >= ADDRESS_THRESHOLD
    return {
        "similarity": score,
        "passed": passed,
        "street_number_match": street_ok,
        "postcode_match": postcode_ok,
        "fact_find_normalised": fact_norm.normalised_text,
    }


def _compare_id_expiry(
    *,
    cover_date_field: FieldValue | None,
    expiry_field: FieldValue | None,
) -> RuleResult:
    cover_raw = cover_date_field.comparison_value if cover_date_field else None
    expiry_raw = expiry_field.comparison_value if expiry_field else None
    cover_date = parse_iso_date(cover_raw)
    expiry_date = parse_iso_date(expiry_raw)
    if cover_date is None or expiry_date is None:
        raise RulesEvaluationError(
            "ID expiry or Fact Find cover date could not be parsed."
        )
    status = "pass" if expiry_date >= cover_date else "fail"
    return _rule(
        "FF-ID-003",
        status,
        fact_find_field_keys=["cover_form_date"],
        document_field_keys=["expiry_date"],
        fact_find_value=cover_raw,
        document_value=expiry_raw,
        normalised_fact_find_value=cover_date.isoformat(),
        normalised_document_value=expiry_date.isoformat(),
        comparison={
            "operator": "date_gte",
            "cover_form_date": cover_date.isoformat(),
            "expiry_date": expiry_date.isoformat(),
        },
        message=(
            "ID is valid on the Fact Find cover date."
            if status == "pass"
            else "ID expired before the Fact Find cover date."
        ),
    )


def _compare_employer(
    *,
    matched_numbers: list[int],
    fact_find_fields: list[FieldValue],
    employer_field: FieldValue | None,
) -> tuple[RuleResult, EmploymentRecord | None]:
    document_raw = employer_field.comparison_value if employer_field else None
    document_norm = normalize_entity(document_raw)
    best_score = Decimal("0.00")
    best_employment: EmploymentRecord | None = None
    for number in matched_numbers:
        for employment in resolve_employments(fact_find_fields, number):
            score = similarity(normalize_entity(employment.employer_name), document_norm)
            if best_employment is None or score > best_score:
                best_score = score
                best_employment = employment

    if best_employment is None:
        result = _incomplete(
            "FF-PS-002",
            "No Fact Find employer is available for the matched applicant.",
            document_field_keys=["employer_name"],
            document_value=document_raw,
            normalised_document_value=document_norm,
        )
        return result, None

    status = "pass" if best_score >= ENTITY_THRESHOLD else "fail"
    result = _rule(
        "FF-PS-002",
        status,
        fact_find_field_keys=[
            key
            for key in (
                best_employment.employer_name_field_key,
                best_employment.start_date_field_key,
            )
            if key
        ],
        document_field_keys=["employer_name"],
        fact_find_value=best_employment.employer_name,
        document_value=document_raw,
        normalised_fact_find_value=normalize_entity(best_employment.employer_name),
        normalised_document_value=document_norm,
        comparison={
            "operator": "entity_similarity",
            "similarity": float(best_score),
            "threshold": float(ENTITY_THRESHOLD),
            "selected_employment_kind": best_employment.kind,
            "matched_applicant_number": best_employment.applicant_number,
        },
        message=(
            "Employer name matches payslip."
            if status == "pass"
            else "Employer name does not match payslip."
        ),
    )
    return result, best_employment


def _compare_employment_start(
    *,
    selected_employment: EmploymentRecord | None,
    pay_period_field: FieldValue | None,
    employer_status: str,
) -> RuleResult:
    if selected_employment is None:
        return _incomplete(
            "FF-PS-003",
            "Employment start comparison skipped because no employer record was selected.",
            document_field_keys=["pay_period_end"],
        )
    if employer_status == "fail":
        return _incomplete(
            "FF-PS-003",
            "Employment start comparison skipped because employer name did not match.",
            fact_find_field_keys=[
                key
                for key in (
                    selected_employment.employer_name_field_key,
                    selected_employment.start_date_field_key,
                )
                if key
            ],
            document_field_keys=["pay_period_end"],
            fact_find_value=selected_employment.start_date,
        )

    pay_raw = pay_period_field.comparison_value if pay_period_field else None
    start_raw = selected_employment.start_date
    pay_date = parse_iso_date(pay_raw)
    start_date = parse_iso_date(start_raw)
    if pay_date is None or start_date is None:
        raise RulesEvaluationError(
            "Payslip pay period end or employment start date could not be parsed."
        )
    status = "pass" if pay_date >= start_date else "fail"
    return _rule(
        "FF-PS-003",
        status,
        fact_find_field_keys=[
            key
            for key in (
                selected_employment.employer_name_field_key,
                selected_employment.start_date_field_key,
            )
            if key
        ],
        document_field_keys=["pay_period_end"],
        fact_find_value=start_raw,
        document_value=pay_raw,
        normalised_fact_find_value=start_date.isoformat(),
        normalised_document_value=pay_date.isoformat(),
        comparison={
            "operator": "date_gte",
            "employment_start_date": start_date.isoformat(),
            "pay_period_end": pay_date.isoformat(),
            "selected_employment_kind": selected_employment.kind,
        },
        message=(
            "Payslip pay period is on or after employment start."
            if status == "pass"
            else "Payslip pay period ends before employment start."
        ),
    )


def _compare_repayment_name(*, repayment, holder_field: FieldValue | None) -> RuleResult:
    fact_raw = repayment.account_name
    doc_raw = holder_field.comparison_value if holder_field else None
    fact_norm = normalize_name(fact_raw)
    doc_norm = normalize_name(doc_raw)
    score = similarity(fact_norm, doc_norm)
    if fact_norm and doc_norm and fact_norm in doc_norm:
        score = max(score, Decimal("1.00"))
    status = "pass" if score >= NAME_THRESHOLD else "fail"
    return _rule(
        "FF-BS-002",
        status,
        fact_find_field_keys=[repayment.account_name_field_key]
        if repayment.account_name_field_key
        else [],
        document_field_keys=["account_holder_name"],
        fact_find_value=fact_raw,
        document_value=doc_raw,
        normalised_fact_find_value=fact_norm,
        normalised_document_value=doc_norm,
        comparison={
            "operator": "name_similarity",
            "similarity": float(score),
            "threshold": float(NAME_THRESHOLD),
        },
        message=(
            "Repayment account name matches bank account holder."
            if status == "pass"
            else "Repayment account name does not match bank account holder."
        ),
    )


def _compare_bsb(*, repayment, bsb_field: FieldValue | None) -> RuleResult:
    fact_raw = repayment.bsb
    doc_raw = bsb_field.comparison_value if bsb_field else None
    fact_norm = normalize_identifier(fact_raw)
    doc_norm = normalize_identifier(doc_raw)
    fact_digits = re.sub(r"\D", "", fact_norm or "")
    doc_digits = re.sub(r"\D", "", doc_norm or "")
    status = (
        "pass"
        if len(fact_digits) == 6 and len(doc_digits) == 6 and fact_digits == doc_digits
        else "fail"
    )
    return _rule(
        "FF-BS-003",
        status,
        fact_find_field_keys=[repayment.bsb_field_key] if repayment.bsb_field_key else [],
        document_field_keys=["bsb"],
        fact_find_value=fact_raw,
        document_value=doc_raw,
        normalised_fact_find_value=fact_digits or None,
        normalised_document_value=doc_digits or None,
        comparison={"operator": "exact_identifier"},
        message=(
            "Repayment BSB matches bank statement."
            if status == "pass"
            else "Repayment BSB does not match bank statement."
        ),
    )


def _is_masked_account(value: str | None) -> bool:
    if value is None:
        return False
    text = str(value)
    if re.search(r"[*Xx#•·]", text):
        return True
    digits = re.sub(r"\D", "", text)
    return len(digits) == 4


def _compare_account_number(
    *,
    repayment,
    account_field: FieldValue | None,
    name_passed: bool,
    bsb_passed: bool,
) -> RuleResult:
    fact_raw = repayment.account_number
    doc_raw = account_field.comparison_value if account_field else None
    fact_norm = normalize_identifier(fact_raw) or ""
    doc_norm = normalize_identifier(doc_raw) or ""
    fact_digits = re.sub(r"\D", "", fact_norm)
    doc_digits = re.sub(r"\D", "", doc_norm)

    if fact_digits and doc_digits and fact_digits == doc_digits:
        status = "pass"
        comparison = {"operator": "exact_identifier", "mode": "full"}
        message = "Repayment account number matches bank statement."
    elif (
        _is_masked_account(doc_raw)
        and name_passed
        and bsb_passed
        and len(fact_digits) >= 4
        and len(doc_digits) >= 4
        and fact_digits[-4:] == doc_digits[-4:]
    ):
        status = "pass"
        comparison = {"operator": "exact_identifier", "mode": "masked_last4"}
        message = "Masked bank account number matches repayment account last four digits."
    else:
        status = "fail"
        comparison = {"operator": "exact_identifier", "mode": "full"}
        message = "Repayment account number does not match bank statement."

    return _rule(
        "FF-BS-004",
        status,
        fact_find_field_keys=[repayment.account_number_field_key]
        if repayment.account_number_field_key
        else [],
        document_field_keys=["account_number"],
        fact_find_value=fact_raw,
        document_value=doc_raw,
        normalised_fact_find_value=fact_digits or None,
        normalised_document_value=doc_digits or None,
        comparison=comparison,
        message=message,
    )


def _classify_savings_type(asset_type: str | None) -> str:
    text = (asset_type or "").strip().lower()
    if "term" in text or "deposit" in text:
        return "term_deposit"
    return "savings"


def _compare_savings(
    *,
    savings: list[SavingsAsset],
    closing_field: FieldValue | None,
) -> RuleResult:
    if not savings:
        return _rule(
            "FF-BS-006",
            "not_applicable",
            document_field_keys=["closing_balance"],
            message="No savings or term deposit assets were declared.",
        )

    closing_raw = closing_field.comparison_value if closing_field else None
    closing = parse_money(closing_raw)
    if closing is None:
        raise RulesEvaluationError("Bank statement closing balance could not be parsed.")

    best = None
    for asset in savings:
        declared = parse_money(asset.value)
        if declared is None:
            continue
        asset_kind = _classify_savings_type(asset.asset_type)
        absolute = abs(closing - declared)
        relative = relative_difference(declared, closing)
        if asset_kind == "term_deposit":
            passed = absolute <= TERM_DEPOSIT_ABSOLUTE_THRESHOLD
            threshold = TERM_DEPOSIT_ABSOLUTE_THRESHOLD
            mode = "absolute"
        else:
            if relative is None:
                passed = False
            else:
                passed = relative <= SAVINGS_RELATIVE_THRESHOLD
            threshold = SAVINGS_RELATIVE_THRESHOLD
            mode = "relative"
        ranking = absolute
        candidate = {
            "asset": asset,
            "asset_kind": asset_kind,
            "declared": declared,
            "absolute": absolute,
            "relative": relative,
            "passed": passed,
            "threshold": threshold,
            "mode": mode,
            "ranking": ranking,
        }
        if best is None or candidate["ranking"] < best["ranking"]:
            best = candidate

    if best is None:
        raise RulesEvaluationError("Declared savings values could not be parsed.")

    status = "pass" if best["passed"] else "fail"
    asset: SavingsAsset = best["asset"]
    return _rule(
        "FF-BS-006",
        status,
        fact_find_field_keys=[
            key
            for key in (asset.value_field_key, asset.asset_type_field_key)
            if key
        ],
        document_field_keys=["closing_balance"],
        fact_find_value=asset.value,
        document_value=closing_raw,
        normalised_fact_find_value=format_money(best["declared"]),
        normalised_document_value=format_money(closing),
        comparison={
            "operator": "balance_match",
            "asset_kind": best["asset_kind"],
            "selected_fact_find_field_key": asset.value_field_key,
            "absolute_difference": float(best["absolute"]),
            "relative_difference": (
                float(best["relative"]) if best["relative"] is not None else None
            ),
            "threshold": float(best["threshold"]),
            "threshold_mode": best["mode"],
        },
        message=(
            "Declared savings balance matches bank closing balance."
            if status == "pass"
            else "Declared savings balance does not match bank closing balance."
        ),
    )
