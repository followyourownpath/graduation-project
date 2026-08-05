import re

from app.normalization.values import australian_date, digits, money, text
from app.normalization.confidence_mapper import get_span_confidence


def _tables(analysis):
    matrices = []
    for table in analysis.get("tables") or []:
        matrix = [["" for _ in range(table.get("columnCount", 0))] for _ in range(table.get("rowCount", 0))]
        for cell in table.get("cells") or []:
            row, column = cell.get("rowIndex"), cell.get("columnIndex")
            if row is not None and column is not None and row < len(matrix) and column < len(matrix[row]):
                matrix[row][column] = text(cell.get("content"))
        matrices.append(matrix)
    return matrices


def _cell_confidence(analysis, table_idx, row, col):
    tables = analysis.get("tables") or []
    if table_idx < len(tables):
        for cell in tables[table_idx].get("cells") or []:
            if cell.get("rowIndex") == row and cell.get("columnIndex") == col:
                return cell.get("confidence")
    return None


def _field(key, label, raw, normalised, data_type, mapped_table=None, mapped_column=None, confidence=None):
    if not text(raw):
        return None
    return {
        "section_name": "payslip",
        "applicant_number": 1,
        "field_key": key,
        "field_label": label,
        "raw_value": text(raw),
        "normalised_value": normalised,
        "data_type": data_type,
        "mapped_table": mapped_table,
        "mapped_column": mapped_column,
        "review_status": "pending",
        "confidence": confidence,
    }


def extract_payslip_fields(result):
    analysis = result.get("analyzeResult") or {}
    content = text(analysis.get("content"))
    fields = []

    abn_match = re.search(r"\bABN\s*:\s*([\d ]{11,16})", content, re.I)
    pay_date_match = re.search(r"Pay Date\s*:\s*(\d{2}/\d{2}/\d{4})", content, re.I)
    pay_period_match = re.search(
        r"Pay Period\s*:\s*(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})", content, re.I
    )
    employer_match = re.match(r"(.+?)\s+ABN\s*:", content, re.I)

    abn_conf = get_span_confidence(result, *abn_match.span(1)) if abn_match else None
    pay_date_conf = get_span_confidence(result, *pay_date_match.span(1)) if pay_date_match else None
    pay_period_start_conf = get_span_confidence(result, *pay_period_match.span(1)) if pay_period_match else None
    pay_period_end_conf = get_span_confidence(result, *pay_period_match.span(2)) if pay_period_match else None
    employer_conf = get_span_confidence(result, *employer_match.span(1)) if employer_match else None

    fields.extend([
        _field("employer_name", "Employer Name", employer_match.group(1) if employer_match else None,
               text(employer_match.group(1)) if employer_match else None, "text", "applicant_employment", "employer_name", confidence=employer_conf),
        _field("employer_abn", "Employer ABN", abn_match.group(1) if abn_match else None,
               digits(abn_match.group(1)) if abn_match else None, "identifier", confidence=abn_conf),
        _field("pay_date", "Pay Date", pay_date_match.group(1) if pay_date_match else None,
               australian_date(pay_date_match.group(1)) if pay_date_match else None, "date", confidence=pay_date_conf),
        _field("pay_period_start", "Pay Period Start", pay_period_match.group(1) if pay_period_match else None,
               australian_date(pay_period_match.group(1)) if pay_period_match else None, "date", confidence=pay_period_start_conf),
        _field("pay_period_end", "Pay Period End", pay_period_match.group(2) if pay_period_match else None,
               australian_date(pay_period_match.group(2)) if pay_period_match else None, "date", confidence=pay_period_end_conf),
    ])

    label_map = {
        "employee name": ("employee_name", "Employee Name", "text", "applicant", "full_name"),
        "job title": ("job_title", "Job Title", "text", "applicant_employment", "position_title"),
        "employment type": ("employment_type", "Employment Type", "text", "applicant_employment", "employment_basis"),
        "super fund": ("super_fund", "Super Fund", "text", None, None),
        "super member id": ("super_member_id", "Super Member ID", "identifier", None, None),
        "bank account": ("bank_account", "Bank Account", "text", None, None),
    }
    earning_map = {
        "ordinary earnings": ("gross_income", "Gross Income"),
        "payg tax withheld": ("tax_withheld", "PAYG Tax Withheld"),
        "super guarantee (11.5%)": ("superannuation", "Superannuation"),
        "net pay (take home)": ("net_income", "Net Income"),
    }

    for table_idx, matrix in enumerate(_tables(analysis)):
        for row_idx, row in enumerate(matrix):
            for index in range(0, len(row) - 1, 2):
                label = row[index].rstrip(":").lower()
                if label in label_map:
                    key, display, data_type, table, column = label_map[label]
                    conf = _cell_confidence(analysis, table_idx, row_idx, index + 1)
                    fields.append(_field(key, display, row[index + 1], text(row[index + 1]), data_type, table, column, confidence=conf))
            if row and row[0].lower() in earning_map and len(row) >= 3:
                key, display = earning_map[row[0].lower()]
                conf_val = _cell_confidence(analysis, table_idx, row_idx, 2)
                fields.append(_field(key, display, row[2], money(row[2]), "money", confidence=conf_val))
                if len(row) >= 4 and row[3]:
                    conf_ytd = _cell_confidence(analysis, table_idx, row_idx, 3)
                    fields.append(_field(f"ytd_{key}", f"YTD {display}", row[3], money(row[3]), "money", confidence=conf_ytd))

    unique = {}
    for field in fields:
        if field and field["field_key"] not in unique:
            unique[field["field_key"]] = field
    return list(unique.values())
