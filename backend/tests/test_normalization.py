from app.normalization.payslip import extract_payslip_fields
from app.normalization.values import australian_date, digits, money


def test_value_normalizers():
    assert money("$8,735.25") == "8735.25"
    assert money("-$2,027.61") == "-2027.61"
    assert money("($25.00)") == "-25.00"
    assert australian_date("02/06/2026") == "2026-06-02"
    assert digits("66 396 710 463") == "66396710463"


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
