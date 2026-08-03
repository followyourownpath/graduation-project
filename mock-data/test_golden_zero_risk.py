import os
import sys

# Add backend to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.rules.models import FieldValue
from app.rules.phase1 import evaluate_phase1
from app.rules.scoring import score_document, score_assessment, risk_level_for_score
from app.normalization.fact_find import extract_fact_find_acroform


def parse_fact_find_pdf(pdf_path):
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    result = extract_fact_find_acroform(pdf_bytes)
    field_values = []
    for item in result["fields"]:
        field_values.append(
            FieldValue(
                field_id=f"ff-{item['field_key']}",
                source_document_id="doc-ffs-1",
                field_key=item["field_key"],
                raw_value=item["raw_value"],
                normalised_value=item["normalised_value"],
                data_type=item["data_type"],
                applicant_number=item.get("applicant_number"),
                mapped_table=item.get("mapped_table"),
                mapped_column=item.get("mapped_column"),
                section_name=item.get("section_name"),
                field_label=item.get("field_label"),
            )
        )
    return field_values


def create_direct_fields():
    """Build exact FieldValues corresponding to OCR outputs for testing."""
    # ID fields
    id_fields = [
        FieldValue(field_id="id-1", source_document_id="doc-id-1", field_key="full_legal_name", raw_value="Junhong ZHONG", normalised_value="Junhong ZHONG", data_type="text"),
        FieldValue(field_id="id-2", source_document_id="doc-id-1", field_key="residential_address", raw_value="150 TODMAN AVE, KENSINGTON NSW 2033", normalised_value="150 TODMAN AVE, KENSINGTON NSW 2033", data_type="text"),
        FieldValue(field_id="id-3", source_document_id="doc-id-1", field_key="expiry_date", raw_value="12 DEC 2023", normalised_value="2023-12-12", data_type="date"),
    ]

    # Payslip fields
    payslip_fields = [
        FieldValue(field_id="ps-1", source_document_id="doc-ps-1", field_key="employee_name", raw_value="Junhong Zhong", normalised_value="Junhong Zhong", data_type="text"),
        FieldValue(field_id="ps-2", source_document_id="doc-ps-1", field_key="employer_name", raw_value="Tech Solutions Pty Ltd", normalised_value="Tech Solutions Pty Ltd", data_type="text"),
        FieldValue(field_id="ps-3", source_document_id="doc-ps-1", field_key="pay_period_end", raw_value="17/06/2026", normalised_value="2026-06-17", data_type="date"),
    ]

    # Bank statement fields
    bank_fields = [
        FieldValue(field_id="bs-1", source_document_id="doc-bs-1", field_key="account_holder_name", raw_value="Junhong Zhong", normalised_value="Junhong Zhong", data_type="text"),
        FieldValue(field_id="bs-2", source_document_id="doc-bs-1", field_key="bsb", raw_value="062-235", normalised_value="062235", data_type="identifier"),
        FieldValue(field_id="bs-3", source_document_id="doc-bs-1", field_key="account_number", raw_value="10473829", normalised_value="10473829", data_type="identifier"),
        FieldValue(field_id="bs-4", source_document_id="doc-bs-1", field_key="closing_balance", raw_value="$15,420.00", normalised_value="15420.00", data_type="money"),
    ]

    # NOA fields
    noa_fields = [
        FieldValue(field_id="noa-1", source_document_id="doc-noa-1", field_key="taxpayer_name", raw_value="MR JUNHONG ZHONG", normalised_value="MR JUNHONG ZHONG", data_type="text"),
        FieldValue(field_id="noa-2", source_document_id="doc-noa-1", field_key="taxpayer_address", raw_value="150 TODMAN AVE, KENSINGTON NSW 2033", normalised_value="150 TODMAN AVE, KENSINGTON NSW 2033", data_type="text"),
    ]

    return id_fields, payslip_fields, bank_fields, noa_fields


def main():
    golden_dir = os.path.join(os.path.dirname(__file__), "goldenData_zero_risk")
    ffs_pdf = os.path.join(golden_dir, "FFS zero risk.pdf")

    print(f"Reading AcroForm fields from: {ffs_pdf}")
    fact_find_fields = parse_fact_find_pdf(ffs_pdf)
    print(f"Extracted {len(fact_find_fields)} Fact Find fields.")

    id_fields, payslip_fields, bank_fields, noa_fields = create_direct_fields()

    documents = {
        "id_100": {"id": "doc-id-1", "original_file_name": "id.jpg"},
        "payslip": {"id": "doc-ps-1", "original_file_name": "payslip.pdf"},
        "bank_statement_3m": {"id": "doc-bs-1", "original_file_name": "bank_statement.pdf"},
        "ato_notice": {"id": "doc-noa-1", "original_file_name": "Mock_Notice_of_Assessment.pdf"},
    }

    fields_by_type = {
        "id_100": id_fields,
        "payslip": payslip_fields,
        "bank_statement_3m": bank_fields,
        "ato_notice": noa_fields,
    }

    bundles = evaluate_phase1(
        fact_find_fields=fact_find_fields,
        documents=documents,
        fields_by_type=fields_by_type,
    )

    doc_scores = {bundle.document_type: score_document(bundle.rules) for bundle in bundles}
    overall_score = score_assessment(doc_scores)
    risk_lvl = risk_level_for_score(overall_score)

    print("\n" + "=" * 60)
    print(f"  Overall Risk Score : {overall_score}")
    print(f"  Risk Level         : {risk_lvl}")
    print("=" * 60 + "\n")

    all_passed = True
    for bundle in bundles:
        doc_type = bundle.document_type
        doc_score = doc_scores[doc_type]
        print(f"Document [{bundle.display_name}] (Score: {doc_score}):")
        for rule in bundle.rules:
            symbol = "PASS" if rule.status == "pass" else rule.status.upper()
            print(f"  - [{rule.rule_id}] {rule.label}: [{symbol}] -- {rule.message}")
            if rule.status != "pass":
                all_passed = False
        print()

    if all_passed and overall_score == 0:
        print("SUCCESS: All 13 rules passed with 0 overall risk score!")
    else:
        print("FAILURE: Not all rules passed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
