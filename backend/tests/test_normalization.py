from app.normalization.bank_statement import extract_bank_statement_fields
from app.normalization.id_100 import extract_id_fields
from app.normalization.payslip import extract_payslip_fields
from app.normalization.values import australian_date, digits, money, phone


def test_value_normalizers():
    assert money("$8,735.25") == "8735.25"
    assert money("-$2,027.61") == "-2027.61"
    assert money("($25.00)") == "-25.00"
    assert australian_date("02/06/2026") == "2026-06-02"
    assert digits("66 396 710 463") == "66396710463"
    assert phone("0412 345 678") == "+61412345678"


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


def test_extract_id_fields():
    result = {"analyzeResult": {
        "content": "DRIVER LICENCE Full Name: April Kidd DOB: 13/09/1966 Licence No: PA4953156 Expiry: 20/08/2030 Residential Address: Unit 69, 86 Travis Tarn Lower, Richmond VIC 3121",
    }}
    fields = {field["field_key"]: field for field in extract_id_fields(result)}
    assert fields["full_legal_name"]["normalised_value"] == "April Kidd"
    assert fields["date_of_birth"]["normalised_value"] == "1966-09-13"
    assert fields["document_number"]["normalised_value"] == "PA4953156"
    assert fields["expiry_date"]["normalised_value"] == "2030-08-20"
    assert fields["residential_address"]["normalised_value"] == "Unit 69, 86 Travis Tarn Lower, Richmond VIC 3121"


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


def test_extract_id_fields_with_table():
    """Test id_100 parser against a 2-column table (the actual PDF layout)."""
    result = {"analyzeResult": {
        "content": "AUSTRALIAN PASSPORT / IDENTITY DOCUMENT VERIFICATION",
        "tables": [
            {
                "rowCount": 7,
                "columnCount": 2,
                "cells": [
                    {"rowIndex": 0, "columnIndex": 0, "content": "Document Type:"},
                    {"rowIndex": 0, "columnIndex": 1, "content": "Passport"},
                    {"rowIndex": 1, "columnIndex": 0, "content": "Full Legal Name:"},
                    {"rowIndex": 1, "columnIndex": 1, "content": "April Kidd"},
                    {"rowIndex": 2, "columnIndex": 0, "content": "Date of Birth:"},
                    {"rowIndex": 2, "columnIndex": 1, "content": "13/09/1966"},
                    {"rowIndex": 3, "columnIndex": 0, "content": "Document Number:"},
                    {"rowIndex": 3, "columnIndex": 1, "content": "PA4953156"},
                    {"rowIndex": 4, "columnIndex": 0, "content": "Expiry Date:"},
                    {"rowIndex": 4, "columnIndex": 1, "content": "20/08/2030"},
                    {"rowIndex": 5, "columnIndex": 0, "content": "Residential Address:"},
                    {"rowIndex": 5, "columnIndex": 1, "content": "Unit 69, 86 Travis Tarn Lower, Richmond VIC 3121"},
                    {"rowIndex": 6, "columnIndex": 0, "content": "Driver Licence Link:"},
                    {"rowIndex": 6, "columnIndex": 1, "content": "Licence No: DL123456 (Expiry: 31/12/2028)"},
                ]
            }
        ]
    }}
    fields = {field["field_key"]: field for field in extract_id_fields(result)}
    assert fields["document_type"]["normalised_value"] == "Passport"
    assert fields["full_legal_name"]["normalised_value"] == "April Kidd"
    assert fields["date_of_birth"]["normalised_value"] == "1966-09-13"
    assert fields["document_number"]["normalised_value"] == "PA4953156"
    assert fields["expiry_date"]["normalised_value"] == "2030-08-20"
    assert fields["driver_licence_link"]["normalised_value"] == "Licence No: DL123456 (Expiry: 31/12/2028)"
    assert fields["driver_licence_number"]["normalised_value"] == "DL123456"
    assert fields["driver_licence_expiry"]["normalised_value"] == "2028-12-31"


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
