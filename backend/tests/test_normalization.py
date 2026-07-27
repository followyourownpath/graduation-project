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

