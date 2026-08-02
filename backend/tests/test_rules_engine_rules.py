from decimal import Decimal

from app.rules.models import FieldValue
from app.rules.normalizers import (
    normalize_address,
    normalize_entity,
    normalize_identifier,
    normalize_name,
    parse_iso_date,
    parse_money,
    similarity,
)
from app.rules.phase1 import PHASE1_RULE_IDS, evaluate_phase1
from app.rules.scoring import risk_level_for_score, score_assessment, score_document
from app.rules.models import RuleResult


def _field(key, value, *, normalised=None, applicant_number=None, doc_id="doc"):
    return FieldValue(
        field_id=f"id-{key}",
        source_document_id=doc_id,
        field_key=key,
        raw_value=value,
        normalised_value=normalised if normalised is not None else value,
        applicant_number=applicant_number,
    )


def test_phase1_registry_has_exactly_thirteen_rules():
    assert len(PHASE1_RULE_IDS) == 13
    assert len(set(PHASE1_RULE_IDS)) == 13


def test_normalize_name_strips_title_punctuation_and_spaces():
    assert normalize_name("MR Alice J. Smith") == "ALICE J SMITH"
    assert normalize_name("Alice-Jane  Smith") == "ALICE JANE SMITH"


def test_normalize_name_keeps_distinct_surnames():
    assert normalize_name("Alice Smith") != normalize_name("Alice Jones")


def test_normalize_entity_strips_company_suffixes():
    assert normalize_entity("Example Pty. Ltd.") == "EXAMPLE"
    assert normalize_entity("Acme & Sons Limited") == "ACME AND SONS"


def test_normalize_address_street_type_and_components():
    address = normalize_address("12 Example St, Sydney NSW 2000")
    assert address.street_number == "12"
    assert address.postcode == "2000"
    assert "STREET" in address.normalised_text


def test_normalize_identifier_keeps_leading_zeros():
    assert normalize_identifier("012-345") == "012345"


def test_parse_money_and_zero_baseline():
    assert parse_money("$1,234.50") == Decimal("1234.50")
    assert parse_money("(10.00)") == Decimal("-10.00")


def test_parse_iso_date_failure():
    assert parse_iso_date("not-a-date") is None
    assert parse_iso_date("2024-01-15").isoformat() == "2024-01-15"


def test_similarity_is_deterministic():
    assert similarity("ALICE SMITH", "ALICE SMITH") == Decimal("1.00")
    assert similarity("ALICE", "BOB") < Decimal("0.50")


def _base_fact_find():
    return [
        _field("cover_form_date", "2024-01-15", applicant_number=None),
        _field("applicant_1_full_name", "Alice Smith", applicant_number=1),
        _field("applicant_2_full_name", "Bob Jones", applicant_number=2),
        _field("applicant_1_current_address_street", "12 Example Street", applicant_number=1),
        _field("applicant_1_current_address_suburb", "Sydney", applicant_number=1),
        _field("applicant_1_current_address_state", "NSW", applicant_number=1),
        _field("applicant_1_current_address_postcode", "2000", applicant_number=1),
        _field("applicant_2_current_address_street", "44 Other Road", applicant_number=2),
        _field("applicant_2_current_address_suburb", "Melbourne", applicant_number=2),
        _field("applicant_2_current_address_state", "VIC", applicant_number=2),
        _field("applicant_2_current_address_postcode", "3000", applicant_number=2),
        _field("applicant_1_current_employment_employer_name", "Example Pty Ltd", applicant_number=1),
        _field("applicant_1_current_employment_start_date", "2020-01-01", applicant_number=1),
        _field("applicant_2_current_employment_employer_name", "Other Co", applicant_number=2),
        _field("applicant_2_current_employment_start_date", "2019-06-01", applicant_number=2),
        _field("repayment_account_name", "Alice Smith"),
        _field("repayment_account_bsb", "012-345"),
        _field("repayment_account_number", "00012345"),
        _field("savings_term_deposit_1_asset_type", "Savings"),
        _field("savings_term_deposit_1_value", "1000.00"),
    ]


def _docs():
    return {
        "id_100": {"id": "id-doc", "original_file_name": "id.jpg"},
        "payslip": {"id": "ps-doc", "original_file_name": "payslip.pdf"},
        "bank_statement_3m": {"id": "bs-doc", "original_file_name": "bank.pdf"},
        "ato_notice": {"id": "noa-doc", "original_file_name": "noa.pdf"},
    }


def _passing_fields():
    return {
        "fact_find": _base_fact_find(),
        "id_100": [
            _field("full_legal_name", "Alice Smith", doc_id="id-doc"),
            _field("residential_address", "12 Example Street, Sydney NSW 2000", doc_id="id-doc"),
            _field("expiry_date", "2026-01-01", doc_id="id-doc"),
        ],
        "payslip": [
            _field("employee_name", "Alice Smith", doc_id="ps-doc"),
            _field("employer_name", "Example", doc_id="ps-doc"),
            _field("pay_period_end", "2024-01-31", doc_id="ps-doc"),
        ],
        "bank_statement_3m": [
            _field("account_holder_name", "Alice Smith", doc_id="bs-doc"),
            _field("bsb", "012345", doc_id="bs-doc"),
            _field("account_number", "00012345", doc_id="bs-doc"),
            _field("closing_balance", "1000.00", doc_id="bs-doc"),
        ],
        "ato_notice": [
            _field("taxpayer_name", "Alice Smith", doc_id="noa-doc"),
            _field("taxpayer_address", "12 Example Street, Sydney NSW 2000", doc_id="noa-doc"),
        ],
    }


def _rule_map(bundles):
    return {
        rule.rule_id: rule
        for bundle in bundles
        for rule in bundle.rules
    }


def test_all_rules_pass():
    fields = _passing_fields()
    bundles = evaluate_phase1(
        fact_find_fields=fields["fact_find"],
        documents=_docs(),
        fields_by_type=fields,
    )
    rules = _rule_map(bundles)
    assert set(rules) == set(PHASE1_RULE_IDS)
    assert all(rule.status == "pass" for rule in rules.values())


def test_ff_id_001_fail():
    fields = _passing_fields()
    fields["id_100"][0] = _field("full_legal_name", "Alicia Smith", doc_id="id-doc")
    rules = _rule_map(
        evaluate_phase1(
            fact_find_fields=fields["fact_find"],
            documents=_docs(),
            fields_by_type=fields,
        )
    )
    assert rules["FF-ID-001"].status == "fail"


def test_ff_id_002_fail_different_street_number():
    fields = _passing_fields()
    fields["id_100"][1] = _field(
        "residential_address", "99 Example Street, Sydney NSW 2000", doc_id="id-doc"
    )
    rules = _rule_map(
        evaluate_phase1(
            fact_find_fields=fields["fact_find"],
            documents=_docs(),
            fields_by_type=fields,
        )
    )
    assert rules["FF-ID-002"].status == "fail"


def test_ff_id_003_fail_expired():
    fields = _passing_fields()
    fields["id_100"][2] = _field("expiry_date", "2020-01-01", doc_id="id-doc")
    rules = _rule_map(
        evaluate_phase1(
            fact_find_fields=fields["fact_find"],
            documents=_docs(),
            fields_by_type=fields,
        )
    )
    assert rules["FF-ID-003"].status == "fail"


def test_ff_ps_applicant_2_binding():
    fields = _passing_fields()
    fields["payslip"] = [
        _field("employee_name", "Bob Jones", doc_id="ps-doc"),
        _field("employer_name", "Other Co", doc_id="ps-doc"),
        _field("pay_period_end", "2024-01-31", doc_id="ps-doc"),
    ]
    bundles = evaluate_phase1(
        fact_find_fields=fields["fact_find"],
        documents=_docs(),
        fields_by_type=fields,
    )
    payslip = next(bundle for bundle in bundles if bundle.document_type == "payslip")
    assert payslip.matched_applicant_numbers == [2]
    rules = _rule_map(bundles)
    assert rules["FF-PS-001"].status == "pass"
    assert rules["FF-PS-002"].status == "pass"


def test_ff_ps_does_not_borrow_other_applicant_employer():
    fields = _passing_fields()
    fields["payslip"] = [
        _field("employee_name", "Alice Smith", doc_id="ps-doc"),
        _field("employer_name", "Other Co", doc_id="ps-doc"),
        _field("pay_period_end", "2024-01-31", doc_id="ps-doc"),
    ]
    rules = _rule_map(
        evaluate_phase1(
            fact_find_fields=fields["fact_find"],
            documents=_docs(),
            fields_by_type=fields,
        )
    )
    assert rules["FF-PS-001"].status == "pass"
    assert rules["FF-PS-002"].status == "fail"
    assert rules["FF-PS-003"].status == "incomplete"


def test_ff_ps_003_fail():
    fields = _passing_fields()
    fields["payslip"][2] = _field("pay_period_end", "2019-01-01", doc_id="ps-doc")
    rules = _rule_map(
        evaluate_phase1(
            fact_find_fields=fields["fact_find"],
            documents=_docs(),
            fields_by_type=fields,
        )
    )
    assert rules["FF-PS-003"].status == "fail"


def test_ff_bs_001_joint_holders():
    fields = _passing_fields()
    fields["bank_statement_3m"][0] = _field(
        "account_holder_name", "Alice Smith AND Bob Jones", doc_id="bs-doc"
    )
    bundles = evaluate_phase1(
        fact_find_fields=fields["fact_find"],
        documents=_docs(),
        fields_by_type=fields,
    )
    bank = next(bundle for bundle in bundles if bundle.document_type == "bank_statement_3m")
    assert bank.matched_applicant_numbers == [1, 2]
    assert _rule_map(bundles)["FF-BS-001"].status == "pass"


def test_ff_bs_002_003_004_pass_and_fail():
    fields = _passing_fields()
    rules = _rule_map(
        evaluate_phase1(
            fact_find_fields=fields["fact_find"],
            documents=_docs(),
            fields_by_type=fields,
        )
    )
    assert rules["FF-BS-002"].status == "pass"
    assert rules["FF-BS-003"].status == "pass"
    assert rules["FF-BS-004"].status == "pass"

    fields["bank_statement_3m"][1] = _field("bsb", "999999", doc_id="bs-doc")
    rules = _rule_map(
        evaluate_phase1(
            fact_find_fields=fields["fact_find"],
            documents=_docs(),
            fields_by_type=fields,
        )
    )
    assert rules["FF-BS-003"].status == "fail"


def test_masked_account_requires_name_and_bsb_pass():
    fields = _passing_fields()
    fields["bank_statement_3m"][2] = _field("account_number", "******2345", doc_id="bs-doc")
    rules = _rule_map(
        evaluate_phase1(
            fact_find_fields=fields["fact_find"],
            documents=_docs(),
            fields_by_type=fields,
        )
    )
    assert rules["FF-BS-004"].status == "pass"

    fields["bank_statement_3m"][0] = _field("account_holder_name", "Someone Else", doc_id="bs-doc")
    fields["bank_statement_3m"][2] = _field("account_number", "******2345", doc_id="bs-doc")
    # Keep repayment name mismatch so FF-BS-002 fails.
    rules = _rule_map(
        evaluate_phase1(
            fact_find_fields=fields["fact_find"],
            documents=_docs(),
            fields_by_type=fields,
        )
    )
    assert rules["FF-BS-002"].status == "fail"
    assert rules["FF-BS-004"].status == "fail"


def test_ff_bs_006_not_applicable_and_fail():
    fields = _passing_fields()
    fields["fact_find"] = [
        field
        for field in fields["fact_find"]
        if not field.field_key.startswith("savings_term_deposit_")
    ]
    rules = _rule_map(
        evaluate_phase1(
            fact_find_fields=fields["fact_find"],
            documents=_docs(),
            fields_by_type=fields,
        )
    )
    assert rules["FF-BS-006"].status == "not_applicable"

    fields = _passing_fields()
    fields["bank_statement_3m"][3] = _field("closing_balance", "5000.00", doc_id="bs-doc")
    rules = _rule_map(
        evaluate_phase1(
            fact_find_fields=fields["fact_find"],
            documents=_docs(),
            fields_by_type=fields,
        )
    )
    assert rules["FF-BS-006"].status == "fail"


def test_ff_noa_002_not_applicable_without_address():
    fields = _passing_fields()
    fields["ato_notice"] = [_field("taxpayer_name", "Alice Smith", doc_id="noa-doc")]
    rules = _rule_map(
        evaluate_phase1(
            fact_find_fields=fields["fact_find"],
            documents=_docs(),
            fields_by_type=fields,
        )
    )
    assert rules["FF-NOA-001"].status == "pass"
    assert rules["FF-NOA-002"].status == "not_applicable"


def test_ff_noa_001_fail():
    fields = _passing_fields()
    fields["ato_notice"][0] = _field("taxpayer_name", "Charlie Brown", doc_id="noa-doc")
    rules = _rule_map(
        evaluate_phase1(
            fact_find_fields=fields["fact_find"],
            documents=_docs(),
            fields_by_type=fields,
        )
    )
    assert rules["FF-NOA-001"].status == "fail"
    assert rules["FF-NOA-002"].status == "incomplete"


def test_scoring_aggregation():
    all_pass = [RuleResult(
        rule_id="x", label="x", status="pass",
        fact_find_field_keys=[], document_field_keys=[],
        fact_find_value=None, document_value=None,
        normalised_fact_find_value=None, normalised_document_value=None,
        comparison={}, message="",
    )]
    assert score_document(all_pass) == 0
    two_fail = [
        RuleResult(
            rule_id="a", label="a", status="fail",
            fact_find_field_keys=[], document_field_keys=[],
            fact_find_value=None, document_value=None,
            normalised_fact_find_value=None, normalised_document_value=None,
            comparison={}, message="",
        ),
        RuleResult(
            rule_id="b", label="b", status="fail",
            fact_find_field_keys=[], document_field_keys=[],
            fact_find_value=None, document_value=None,
            normalised_fact_find_value=None, normalised_document_value=None,
            comparison={}, message="",
        ),
        RuleResult(
            rule_id="c", label="c", status="not_applicable",
            fact_find_field_keys=[], document_field_keys=[],
            fact_find_value=None, document_value=None,
            normalised_fact_find_value=None, normalised_document_value=None,
            comparison={}, message="",
        ),
    ]
    assert score_document(two_fail) == 25

    assert score_assessment({
        "id_100": 0, "payslip": 0, "bank_statement_3m": 0, "ato_notice": 0
    }) == 0
    assert risk_level_for_score(0) == "low"
    assert risk_level_for_score(25) == "lower"
    assert risk_level_for_score(50) == "medium"
    assert risk_level_for_score(75) == "higher"
    assert risk_level_for_score(100) == "high"

    assert score_assessment({
        "id_100": 25, "payslip": 0, "bank_statement_3m": 0, "ato_notice": 0
    }) == 25
    assert score_assessment({
        "id_100": 25, "payslip": 25, "bank_statement_3m": 0, "ato_notice": 0
    }) == 50
    assert score_assessment({
        "id_100": 25, "payslip": 25, "bank_statement_3m": 25, "ato_notice": 0
    }) == 75
    assert score_assessment({
        "id_100": 25, "payslip": 25, "bank_statement_3m": 25, "ato_notice": 25
    }) == 100
