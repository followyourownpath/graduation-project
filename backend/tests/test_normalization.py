from app.normalization.bank_statement import extract_bank_statement_fields
from app.normalization.id_100 import extract_id_fields
from app.normalization.payslip import extract_payslip_fields
from app.normalization.values import australian_date, digits, money, phone, parse_full_address


def test_value_normalizers():
    assert money("$8,735.25") == "8735.25"
    assert money("-$2,027.61") == "-2027.61"
    assert money("($25.00)") == "-25.00"
    assert australian_date("02/06/2026") == "2026-06-02"
    assert digits("66 396 710 463") == "66396710463"
    assert phone("0412 345 678") == "+61412345678"
    assert parse_full_address("150 Todman Ave, Kensington NSW 2033") == {
        "street_number": "150",
        "street_name": "Todman",
        "street_type": "Ave",
        "city": "Kensington",
        "state": "NSW",
        "postcode": "2033",
    }


def test_extract_payslip_fields_from_layout_tables():
    result = {"analyzeResult": {
        "content": "Wolf Ltd Pty Ltd ABN: 66 396 710 463 PAY SLIP Pay Date: 02/06/2026 Pay Period: 03/05/2026 - 01/06/2026",
        "tables": [
            {"rowCount": 1, "columnCount": 4, "cells": [
                {"rowIndex": 0, "columnIndex": 0, "content": "Employee Name:"},
                {"rowIndex": 0, "columnIndex": 1, "content": "April Kidd"},
                {"rowIndex": 0, "columnIndex": 2, "content": "Job Title:"},
                {"rowIndex": 0, "columnIndex": 3, "content": "Accountant"},
            ]},
            {"rowCount": 2, "columnCount": 4, "cells": [
                {"rowIndex": 0, "columnIndex": 0, "content": "Description"},
                {"rowIndex": 0, "columnIndex": 2, "content": "Current Amount"},
                {"rowIndex": 1, "columnIndex": 0, "content": "Ordinary Earnings"},
                {"rowIndex": 1, "columnIndex": 2, "content": "$8,735.25"},
                {"rowIndex": 1, "columnIndex": 3, "content": "$113,558.25"},
            ]},
        ],
    }}
    fields = {field["field_key"]: field for field in extract_payslip_fields(result)}
    assert fields["employer_name"]["normalised_value"] == "Wolf Ltd Pty Ltd"
    assert fields["employer_abn"]["normalised_value"] == "66396710463"
    assert fields["pay_date"]["normalised_value"] == "2026-06-02"
    assert fields["employee_name"]["normalised_value"] == "April Kidd"
    assert fields["gross_income"]["normalised_value"] == "8735.25"
    assert fields["ytd_gross_income"]["normalised_value"] == "113558.25"


def test_extract_id_fields_nsw_licence():
    result = {"analyzeResult": {
        "content": (
            "Driver Licence\n"
            "New South Wales, Australia\n"
            "Junhong ZHONG\n"
            "150 TODMAN AVE\n"
            "KENSINGTON NSW 2033\n"
            "Licence No.\n"
            "11208313\n"
            "Licence Class\n"
            "C\n"
            "Date of Birth\n"
            "08 JAN 1992\n"
            "2 042 604 436\n"
            "Expiry Date\n"
            "12 DEC 2023\n"
        ),
    }}
    fields = {field["field_key"]: field for field in extract_id_fields(result)}
    assert fields["document_type"]["normalised_value"] == "Driver Licence"
    assert fields["jurisdiction"]["normalised_value"] == "New South Wales, Australia"
    assert fields["full_legal_name"]["normalised_value"] == "Junhong ZHONG"
    assert fields["residential_address"]["normalised_value"] == "150 TODMAN AVE, KENSINGTON NSW 2033"
    assert fields["licence_number"]["normalised_value"] == "11208313"
    assert fields["licence_class"]["normalised_value"] == "C"
    assert fields["date_of_birth"]["normalised_value"] == "1992-01-08"
    assert fields["card_number"]["normalised_value"] == "2042604436"
    assert fields["expiry_date"]["normalised_value"] == "2023-12-12"


def test_extract_bank_statement_fields():
    result = {"analyzeResult": {
        "content": "STATEMENT Account Holder Name: April Kidd BSB: 343-347 Account Number: 3807 2897 Statement Period: 01/04/2026 - 30/06/2026 Opening Balance: $14,296.97 Closing Balance: $21,766.91",
    }}
    fields = {field["field_key"]: field for field in extract_bank_statement_fields(result)}
    assert fields["account_holder_name"]["normalised_value"] == "April Kidd"
    assert fields["bsb"]["normalised_value"] == "343-347"
    assert fields["account_number"]["normalised_value"] == "38072897"
    assert fields["statement_period_start"]["normalised_value"] == "2026-04-01"
    assert fields["statement_period_end"]["normalised_value"] == "2026-06-30"
    assert fields["opening_balance"]["normalised_value"] == "14296.97"
    assert fields["closing_balance"]["normalised_value"] == "21766.91"


def test_extract_bank_statement_fields_header_table():
    result = {"analyzeResult": {
        "content": "SMARTFINN MUTUAL BANK Jessica Nicole Ramirez Unit 72, 442 Williams Ring Steps, Glenelg SA 5045 BSB: 866-259 Account No: 1073 6022 Statement Period: 01/04/2026 - 30/06/2026",
        "tables": [
            {
                "rowCount": 2,
                "columnCount": 4,
                "cells": [
                    {"rowIndex": 0, "columnIndex": 0, "content": "Opening Balance"},
                    {"rowIndex": 0, "columnIndex": 1, "content": "Total Credits"},
                    {"rowIndex": 0, "columnIndex": 2, "content": "Total Debits"},
                    {"rowIndex": 0, "columnIndex": 3, "content": "Closing Balance"},
                    {"rowIndex": 1, "columnIndex": 0, "content": "$13,170.81"},
                    {"rowIndex": 1, "columnIndex": 1, "content": "+$7,414.53"},
                    {"rowIndex": 1, "columnIndex": 2, "content": "-$13,572.03"},
                    {"rowIndex": 1, "columnIndex": 3, "content": "$7,013.31"},
                ]
            }
        ]
    }}
    fields = {field["field_key"]: field for field in extract_bank_statement_fields(result)}
    assert fields["account_holder_name"]["normalised_value"] == "Jessica Nicole Ramirez"
    assert fields["bsb"]["normalised_value"] == "866-259"
    assert fields["account_number"]["normalised_value"] == "10736022"
    assert fields["opening_balance"]["normalised_value"] == "13170.81"
    assert fields["closing_balance"]["normalised_value"] == "7013.31"


def test_extract_ato_notice_fields():
    from app.normalization.ato_notice import REQUIRED_KEYS, extract_ato_notice_fields

    result = {"analyzeResult": {
        "content": (
            "Australian Taxation Office\n"
            "MR DAVID R THOMPSON\n"
            "45 WATTLE CRESCENT\n"
            "PARRAMATTA NSW 2150\n"
            "Tax File Number 748 219 356\n"
            "Date of issue 3 October 2022\n"
            "Our reference 417 936 205 8871\n"
            "Notice of assessment - year ended 30 June 2022\n"
            "Your taxable income is $85,321\n"
            "Tax on your taxable income or net income 18,742.15\n"
            "Assessed tax payable $18,742.15 DR\n"
            "Medicare levy 1,706.42\n"
            "Less tax offset refunds 0.00\n"
            "PAYG withholding (eg tax deducted by your employer or bank) 21,500.00\n"
            "Result of this notice 1,051.43 CR\n"
            "Outcome of this notice $1,051.43 CR\n"
            "1,051.43 CR has been forwarded to your nominated financial institution\n"
            "Transaction Reference Number ATO0007744921038562\n"
        ),
        "tables": [
            {
                "rowCount": 6,
                "columnCount": 3,
                "cells": [
                    {"rowIndex": 0, "columnIndex": 0, "content": "Description"},
                    {"rowIndex": 0, "columnIndex": 1, "content": "Debits $"},
                    {"rowIndex": 0, "columnIndex": 2, "content": "Credits $"},
                    {"rowIndex": 1, "columnIndex": 0, "content": "Tax on your taxable income or net income"},
                    {"rowIndex": 1, "columnIndex": 1, "content": "18,742.15"},
                    {"rowIndex": 1, "columnIndex": 2, "content": ""},
                    {"rowIndex": 2, "columnIndex": 0, "content": "Medicare levy"},
                    {"rowIndex": 2, "columnIndex": 1, "content": "1,706.42"},
                    {"rowIndex": 2, "columnIndex": 2, "content": ""},
                    {"rowIndex": 3, "columnIndex": 0, "content": "Less tax offset refunds"},
                    {"rowIndex": 3, "columnIndex": 1, "content": "0.00"},
                    {"rowIndex": 3, "columnIndex": 2, "content": ""},
                    {"rowIndex": 4, "columnIndex": 0, "content": "PAYG withholding (eg tax deducted by your employer or bank)"},
                    {"rowIndex": 4, "columnIndex": 1, "content": ""},
                    {"rowIndex": 4, "columnIndex": 2, "content": "21,500.00"},
                    {"rowIndex": 5, "columnIndex": 0, "content": "Result of this notice"},
                    {"rowIndex": 5, "columnIndex": 1, "content": ""},
                    {"rowIndex": 5, "columnIndex": 2, "content": "1,051.43"},
                ],
            }
        ],
    }}
    fields = {field["field_key"]: field for field in extract_ato_notice_fields(result)}
    assert list(fields) == list(REQUIRED_KEYS) or set(fields) == set(REQUIRED_KEYS)
    assert len(fields) == len(REQUIRED_KEYS)
    assert fields["taxpayer_name"]["normalised_value"] == "MR DAVID R THOMPSON"
    assert fields["taxpayer_address"]["normalised_value"] == "45 WATTLE CRESCENT, PARRAMATTA NSW 2150"
    assert fields["tfn"]["normalised_value"] == "748219356"
    assert fields["ato_reference"]["normalised_value"] == "4179362058871"
    assert fields["year_ended"]["normalised_value"] == "2022-06-30"
    assert fields["income_year"]["normalised_value"] == "2021–2022"
    assert fields["date_of_issue"]["normalised_value"] == "2022-10-03"
    assert fields["taxable_income"]["normalised_value"] == "85321.00"
    assert fields["tax_on_taxable_income"]["normalised_value"] == "18742.15"
    assert fields["low_income_tax_offset"]["normalised_value"] is None
    assert fields["non_refundable_tax_offsets"]["normalised_value"] is None
    assert fields["other_liabilities"]["normalised_value"] is None
    assert fields["payg_credits_and_entitlements"]["normalised_value"] is None
    assert fields["assessed_tax_payable"]["normalised_value"] == "18742.15"
    assert fields["medicare_levy"]["normalised_value"] == "1706.42"
    assert fields["tax_offset_refunds"]["normalised_value"] == "0.00"
    assert fields["payg_withholding_credits"]["normalised_value"] == "21500.00"
    assert fields["result_of_notice_amount"]["normalised_value"] == "1051.43"
    assert fields["result_of_notice_direction"]["normalised_value"] == "CR"
    assert fields["outcome_amount"]["normalised_value"] == "1051.43"
    assert fields["outcome_direction"]["normalised_value"] == "CR"
    assert fields["refund_amount"]["normalised_value"] == "1051.43"
    assert "nominated financial institution" in fields["refund_status"]["normalised_value"].lower()
    assert fields["refund_reference"]["normalised_value"] == "ATO0007744921038562"


def test_extract_bank_statement_transactions():
    """Test bank_statement transaction row extraction from a 5-column table."""
    result = {"analyzeResult": {
        "content": "BSB: 343-347 Account No: 3807 2897 Statement Period: 01/04/2026 - 30/06/2026",
        "tables": [
            {
                "rowCount": 4,
                "columnCount": 5,
                "cells": [
                    {"rowIndex": 0, "columnIndex": 0, "content": "Date"},
                    {"rowIndex": 0, "columnIndex": 1, "content": "Description"},
                    {"rowIndex": 0, "columnIndex": 2, "content": "Debit (-)"},
                    {"rowIndex": 0, "columnIndex": 3, "content": "Credit (+)"},
                    {"rowIndex": 0, "columnIndex": 4, "content": "Balance"},
                    {"rowIndex": 1, "columnIndex": 0, "content": "01/04/2026"},
                    {"rowIndex": 1, "columnIndex": 1, "content": "RENT DEBIT REAL ESTATE MGT"},
                    {"rowIndex": 1, "columnIndex": 2, "content": "-$2,341.87"},
                    {"rowIndex": 1, "columnIndex": 3, "content": ""},
                    {"rowIndex": 1, "columnIndex": 4, "content": "$10,828.94"},
                    {"rowIndex": 2, "columnIndex": 0, "content": "03/04/2026"},
                    {"rowIndex": 2, "columnIndex": 1, "content": "DIRECT DEP WOLF LTD PTY LT PAYROLL"},
                    {"rowIndex": 2, "columnIndex": 2, "content": ""},
                    {"rowIndex": 2, "columnIndex": 3, "content": "+$6,707.64"},
                    {"rowIndex": 2, "columnIndex": 4, "content": "$17,536.58"},
                    {"rowIndex": 3, "columnIndex": 0, "content": "05/04/2026"},
                    {"rowIndex": 3, "columnIndex": 1, "content": "DEBIT CARD COLES SUPERMARKETS"},
                    {"rowIndex": 3, "columnIndex": 2, "content": "-$62.95"},
                    {"rowIndex": 3, "columnIndex": 3, "content": ""},
                    {"rowIndex": 3, "columnIndex": 4, "content": "$17,473.63"},
                ]
            }
        ]
    }}
    fields_list = extract_bank_statement_fields(result)
    fmap = {f["field_key"]: f for f in fields_list}
    assert "transaction_1_date" in fmap
    assert "transaction_1_debit" in fmap
    assert "transaction_2_credit" in fmap
    assert "transaction_3_debit" in fmap
    assert fmap["transaction_1_date"]["normalised_value"] == "2026-04-01"
    assert fmap["transaction_1_description"]["normalised_value"] == "RENT DEBIT REAL ESTATE MGT"
    assert fmap["transaction_1_debit"]["normalised_value"] == "-2341.87"
    assert fmap["transaction_2_credit"]["normalised_value"] == "6707.64"
    assert fmap["transaction_3_date"]["normalised_value"] == "2026-04-05"
