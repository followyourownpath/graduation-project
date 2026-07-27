import re

from app.normalization.values import australian_date, digits, money, text


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


def _field(key, label, raw, normalised, data_type, mapped_table=None, mapped_column=None):
    if not text(raw):
        return None
    return {
        "section_name": "bank_statement",
        "applicant_number": 1,
        "field_key": key,
        "field_label": label,
        "raw_value": text(raw),
        "normalised_value": normalised,
        "data_type": data_type,
        "mapped_table": mapped_table,
        "mapped_column": mapped_column,
        "review_status": "pending",
    }


def extract_bank_statement_fields(result):
    analysis = result.get("analyzeResult") or {}
    content = text(analysis.get("content"))
    fields = []

    # Text / Regex extraction
    holder_match = re.search(r"(?:Account\s*Holder\s*Name|Account\s*Holder|Account\s*Name)\s*:\s*([A-Za-z\s'-]+?)(?=\s+(?:BSB|Account|Statement|Opening|Closing|\b[A-Z][a-z]+:)|$)", content, re.I)
    bsb_match = re.search(r"\bBSB\s*:\s*([\d-]{6,7})", content, re.I)
    acc_match = re.search(
        r"(?:Account\s*Number|Acc|Account\s*No\.?)\s*:\s*([\d ]{6,12}?)(?=\s+(?:Statement|Opening|Closing|\b[A-Z][a-z]+:)|$)",
        content, re.I
    )
    period_match = re.search(
        r"(?:Statement\s*Period|Period)\s*:\s*(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})", content, re.I
    )
    opening_match = re.search(r"Opening\s*Balance\s*:\s*(\(?[$]?[\d,.]+\)?)", content, re.I)
    closing_match = re.search(r"Closing\s*Balance\s*:\s*(\(?[$]?[\d,.]+\)?)", content, re.I)

    period_raw = None
    if period_match:
        period_raw = f"{period_match.group(1)} - {period_match.group(2)}"

    fields.extend([
        _field("account_holder_name", "Account Holder Name", holder_match.group(1).strip() if holder_match else None,
               text(holder_match.group(1).strip()) if holder_match else None, "text", "applicant", "full_name"),
        _field("bsb", "BSB", bsb_match.group(1) if bsb_match else None,
               text(bsb_match.group(1)) if bsb_match else None, "identifier"),
        _field("account_number", "Account Number", acc_match.group(1) if acc_match else None,
               digits(acc_match.group(1)) if acc_match else None, "identifier"),
        _field("statement_period", "Statement Period", period_raw,
               period_raw, "text"),
        _field("statement_period_start", "Statement Period Start", period_match.group(1) if period_match else None,
               australian_date(period_match.group(1)) if period_match else None, "date"),
        _field("statement_period_end", "Statement Period End", period_match.group(2) if period_match else None,
               australian_date(period_match.group(2)) if period_match else None, "date"),
        _field("opening_balance", "Opening Balance", opening_match.group(1) if opening_match else None,
               money(opening_match.group(1)) if opening_match else None, "money"),
        _field("closing_balance", "Closing Balance", closing_match.group(1) if closing_match else None,
               money(closing_match.group(1)) if closing_match else None, "money"),
    ])

    # Table layout key-value extraction fallback
    label_map = {
        "account holder name": ("account_holder_name", "Account Holder Name", "text", "applicant", "full_name"),
        "account holder": ("account_holder_name", "Account Holder Name", "text", "applicant", "full_name"),
        "account name": ("account_holder_name", "Account Holder Name", "text", "applicant", "full_name"),
        "bsb": ("bsb", "BSB", "identifier", None, None),
        "account number": ("account_number", "Account Number", "identifier", None, None),
        "acc": ("account_number", "Account Number", "identifier", None, None),
        "opening balance": ("opening_balance", "Opening Balance", "money", None, None),
        "closing balance": ("closing_balance", "Closing Balance", "money", None, None),
    }

    for matrix in _tables(analysis):
        for row in matrix:
            for index in range(0, len(row) - 1, 2):
                label = row[index].rstrip(":").lower()
                if label in label_map:
                    key, display, data_type, table, column = label_map[label]
                    val = row[index + 1]
                    if data_type == "money":
                        norm = money(val)
                    elif data_type == "identifier":
                        norm = digits(val) if key == "account_number" else text(val)
                    else:
                        norm = text(val)
                    fields.append(_field(key, display, val, norm, data_type, table, column))

    unique = {}
    for field in fields:
        if field and field["field_key"] not in unique:
            unique[field["field_key"]] = field
    return list(unique.values())
