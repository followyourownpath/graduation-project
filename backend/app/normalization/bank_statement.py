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


def _field(key, label, raw, normalised, data_type, result, mapped_table=None, mapped_column=None, confidence=None):
    raw_str = text(raw) if raw is not None else ""
    if not raw_str:
        return None
    if confidence is None:
        content = text(result.get("analyzeResult", {}).get("content", ""))
        start = content.find(raw_str)
        if start != -1:
            confidence = get_span_confidence(result, start, start + len(raw_str))
    return {
        "section_name": "bank_statement",
        "applicant_number": 1,
        "field_key": key,
        "field_label": label,
        "raw_value": raw_str,
        "normalised_value": normalised,
        "data_type": data_type,
        "mapped_table": mapped_table,
        "mapped_column": mapped_column,
        "review_status": "pending",
        "confidence": confidence,
    }


def _is_transaction_table(matrix):
    """Return True if this matrix looks like the Date/Description/Debit/Credit/Balance table."""
    if len(matrix) < 2 or len(matrix[0]) < 4:
        return False
    header = [col.lower() for col in matrix[0]]
    return any("date" in h for h in header) and any("desc" in h for h in header)


def _extract_transactions(matrices, result):
    """Find the 5-column transactions table and return a flat list of extracted_field dicts."""
    analysis = result.get("analyzeResult") or {}
    fields = []
    for table_idx, matrix in enumerate(matrices):
        if not _is_transaction_table(matrix):
            continue

        header = [col.lower() for col in matrix[0]]

        # Locate column indices
        date_col  = next((i for i, h in enumerate(header) if "date"   in h), 0)
        desc_col  = next((i for i, h in enumerate(header) if "desc"   in h), 1)
        debit_col = next((i for i, h in enumerate(header) if "debit"  in h), 2)
        credit_col= next((i for i, h in enumerate(header) if "credit" in h), 3)
        bal_col   = next((i for i, h in enumerate(header) if "balance"in h), 4)
        max_col   = max(date_col, desc_col, debit_col, credit_col, bal_col)

        n = 0
        for row_idx, row in enumerate(matrix[1:], start=1):          # skip header row
            if len(row) <= max_col:
                continue
            date_val = row[date_col].strip()
            # Only process rows that start with a valid date
            if not re.match(r"\d{2}/\d{2}/\d{4}", date_val):
                continue

            n += 1
            prefix = f"transaction_{n}"
            desc_val   = row[desc_col].strip()
            debit_val  = row[debit_col].strip()
            credit_val = row[credit_col].strip()
            bal_val    = row[bal_col].strip()

            date_conf = _cell_confidence(analysis, table_idx, row_idx, date_col)
            desc_conf = _cell_confidence(analysis, table_idx, row_idx, desc_col)
            debit_conf = _cell_confidence(analysis, table_idx, row_idx, debit_col) if debit_val else None
            credit_conf = _cell_confidence(analysis, table_idx, row_idx, credit_col) if credit_val else None
            bal_conf = _cell_confidence(analysis, table_idx, row_idx, bal_col) if bal_val else None

            fields.append(_field(f"{prefix}_date",
                                 f"Transaction {n} Date",
                                 date_val, australian_date(date_val), "date", result, confidence=date_conf))
            fields.append(_field(f"{prefix}_description",
                                 f"Transaction {n} Description",
                                 desc_val, text(desc_val), "text", result, confidence=desc_conf))
            if debit_val:
                fields.append(_field(f"{prefix}_debit",
                                     f"Transaction {n} Debit",
                                     debit_val, money(debit_val), "money", result, confidence=debit_conf))
            if credit_val:
                fields.append(_field(f"{prefix}_credit",
                                     f"Transaction {n} Credit",
                                     credit_val, money(credit_val), "money", result, confidence=credit_conf))
            if bal_val:
                fields.append(_field(f"{prefix}_balance",
                                     f"Transaction {n} Balance",
                                     bal_val, money(bal_val), "money", result, confidence=bal_conf))

        if n > 0:
            break  # stop after processing the first transaction table

    return [f for f in fields if f]


def extract_bank_statement_fields(result):
    analysis = result.get("analyzeResult") or {}
    content = text(analysis.get("content"))
    fields = []

    # ------------------------------------------------------------------
    # 1. Regex extraction from the plain-text content
    # ------------------------------------------------------------------
    holder_match = re.search(
        r"(?:Account\s*Holder\s*Name|Account\s*Holder|Account\s*Name)\s*:\s*([A-Za-z\s'-]+?)(?=\s+(?:BSB|Account|Statement|Opening|Closing|\b[A-Z][a-z]+:)|$)",
        content, re.I
    )
    if not holder_match:
        # Fallback: name placed at top before address keywords
        holder_match = re.search(
            r"\b([A-Z][a-z]+(?:\s+(?:(?!Unit|BSB|Account|Statement|Bank|Suite|PO|Box|Licence|Credit|Mutual|LTD|Ltd|ABN|ACN|AFSL)[A-Z][a-z]+))+)\b"
            r"(?=\s+(?:Unit|\d+|BSB:|[A-Z][a-z]+\s+(?:Street|St|Road|Rd|Way|Lane|Ln|Drive|Dr|Ring|Steps|Tarn|Foreshore|Strand)))",
            content
        )

    bsb_match = re.search(r"\bBSB\s*:\s*([\d-]{6,7})", content, re.I)
    acc_match = re.search(
        r"(?:Account\s*Number|Acc|Account\s*No\.?)\s*:\s*([\d ]{6,12}?)(?=\s+(?:Statement|Opening|Closing|\b[A-Z][a-z]+:)|$)",
        content, re.I
    )
    period_match = re.search(
        r"(?:Statement\s*Period|Period)\s*:\s*(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})",
        content, re.I
    )
    opening_match = re.search(r"Opening\s*Balance\s*:\s*(\(?[$]?[\d,.]+\)?)", content, re.I)
    closing_match = re.search(r"Closing\s*Balance\s*:\s*(\(?[$]?[\d,.]+\)?)", content, re.I)

    period_raw = (f"{period_match.group(1)} - {period_match.group(2)}" if period_match else None)

    fields.extend([
        _field("account_holder_name", "Account Holder Name",
               holder_match.group(1).strip() if holder_match else None,
               text(holder_match.group(1).strip()) if holder_match else None,
               "text", result, "applicant", "full_name"),
        _field("bsb", "BSB",
               bsb_match.group(1) if bsb_match else None,
               text(bsb_match.group(1)) if bsb_match else None, "identifier", result),
        _field("account_number", "Account Number",
               acc_match.group(1) if acc_match else None,
               digits(acc_match.group(1)) if acc_match else None, "identifier", result),
        _field("statement_period", "Statement Period", period_raw, period_raw, "text", result),
        _field("statement_period_start", "Statement Period Start",
               period_match.group(1) if period_match else None,
               australian_date(period_match.group(1)) if period_match else None, "date", result),
        _field("statement_period_end", "Statement Period End",
               period_match.group(2) if period_match else None,
               australian_date(period_match.group(2)) if period_match else None, "date", result),
        _field("opening_balance", "Opening Balance",
               opening_match.group(1) if opening_match else None,
               money(opening_match.group(1)) if opening_match else None, "money", result),
        _field("closing_balance", "Closing Balance",
               closing_match.group(1) if closing_match else None,
               money(closing_match.group(1)) if closing_match else None, "money", result),
    ])

    # ------------------------------------------------------------------
    # 2. Table extraction
    # ------------------------------------------------------------------
    summary_label_map = {
        "account holder name": ("account_holder_name", "Account Holder Name", "text", "applicant", "full_name"),
        "account holder":      ("account_holder_name", "Account Holder Name", "text", "applicant", "full_name"),
        "account name":        ("account_holder_name", "Account Holder Name", "text", "applicant", "full_name"),
        "bsb":                 ("bsb",            "BSB",            "identifier", None, None),
        "account number":      ("account_number", "Account Number", "identifier", None, None),
        "acc":                 ("account_number", "Account Number", "identifier", None, None),
        "opening balance":     ("opening_balance", "Opening Balance", "money", None, None),
        "closing balance":     ("closing_balance", "Closing Balance", "money", None, None),
        "total credits":       ("total_credits",  "Total Credits",  "money", None, None),
        "total debits":        ("total_debits",   "Total Debits",   "money", None, None),
    }

    matrices = _tables(analysis)
    for table_idx, matrix in enumerate(matrices):
        if _is_transaction_table(matrix):
            # Handled separately below
            continue

        if len(matrix) >= 2:
            row0_labels = [col.rstrip(":").lower() for col in matrix[0]]
            # Header-row / value-row summary table (e.g. Opening Balance | Total Credits | ...)
            if any(lbl in summary_label_map for lbl in row0_labels):
                for col_idx, label in enumerate(row0_labels):
                    if label in summary_label_map and col_idx < len(matrix[1]):
                        key, display, data_type, table, column = summary_label_map[label]
                        val = matrix[1][col_idx]
                        norm = money(val) if data_type == "money" else text(val)
                        conf = _cell_confidence(analysis, table_idx, 1, col_idx)
                        fields.append(_field(key, display, val, norm, data_type, result, table, column, confidence=conf))
                continue

        # Side-by-side key-value table (label in col 0, value in col 1)
        for row_idx, row in enumerate(matrix):
            if len(row) < 2:
                continue
            label = row[0].rstrip(":").lower()
            if label in summary_label_map:
                key, display, data_type, table, column = summary_label_map[label]
                val = row[1]
                norm = money(val) if data_type == "money" else (digits(val) if data_type == "identifier" else text(val))
                conf = _cell_confidence(analysis, table_idx, row_idx, 1)
                fields.append(_field(key, display, val, norm, data_type, result, table, column, confidence=conf))

    # 2b. Extract individual transaction rows
    fields.extend(_extract_transactions(matrices, result))

    # ------------------------------------------------------------------
    # 3. Deduplicate: first occurrence wins for summary fields
    # ------------------------------------------------------------------
    unique = {}
    for field in fields:
        if field and field["field_key"] not in unique:
            unique[field["field_key"]] = field
    return list(unique.values())
