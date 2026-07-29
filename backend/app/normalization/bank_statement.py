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


def _is_transaction_table(matrix):
    """Return True if this matrix looks like the Date/Description/Debit/Credit/Balance table."""
    if len(matrix) < 2 or len(matrix[0]) < 4:
        return False
    header = [col.lower() for col in matrix[0]]
    return any("date" in h for h in header) and any("desc" in h for h in header)


def _extract_transactions(matrices):
    """Find the 5-column transactions table and return a flat list of extracted_field dicts."""
    fields = []
    for matrix in matrices:
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
        for row in matrix[1:]:          # skip header row
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

            fields.append(_field(f"{prefix}_date",
                                 f"Transaction {n} Date",
                                 date_val, australian_date(date_val), "date"))
            fields.append(_field(f"{prefix}_description",
                                 f"Transaction {n} Description",
                                 desc_val, text(desc_val), "text"))
            if debit_val:
                fields.append(_field(f"{prefix}_debit",
                                     f"Transaction {n} Debit",
                                     debit_val, money(debit_val), "money"))
            if credit_val:
                fields.append(_field(f"{prefix}_credit",
                                     f"Transaction {n} Credit",
                                     credit_val, money(credit_val), "money"))
            if bal_val:
                fields.append(_field(f"{prefix}_balance",
                                     f"Transaction {n} Balance",
                                     bal_val, money(bal_val), "money"))

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
            r"\b([A-Z][a-z]+(?:\s+(?:(?!Unit|BSB|Account|Statement|Bank|Suite|PO|Box)[A-Z][a-z]+))+)\b"
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
               "text", "applicant", "full_name"),
        _field("bsb", "BSB",
               bsb_match.group(1) if bsb_match else None,
               text(bsb_match.group(1)) if bsb_match else None, "identifier"),
        _field("account_number", "Account Number",
               acc_match.group(1) if acc_match else None,
               digits(acc_match.group(1)) if acc_match else None, "identifier"),
        _field("statement_period", "Statement Period", period_raw, period_raw, "text"),
        _field("statement_period_start", "Statement Period Start",
               period_match.group(1) if period_match else None,
               australian_date(period_match.group(1)) if period_match else None, "date"),
        _field("statement_period_end", "Statement Period End",
               period_match.group(2) if period_match else None,
               australian_date(period_match.group(2)) if period_match else None, "date"),
        _field("opening_balance", "Opening Balance",
               opening_match.group(1) if opening_match else None,
               money(opening_match.group(1)) if opening_match else None, "money"),
        _field("closing_balance", "Closing Balance",
               closing_match.group(1) if closing_match else None,
               money(closing_match.group(1)) if closing_match else None, "money"),
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
    for matrix in matrices:
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
                        fields.append(_field(key, display, val, norm, data_type, table, column))
                continue

        # Side-by-side key-value table (label in col 0, value in col 1)
        for row in matrix:
            if len(row) < 2:
                continue
            label = row[0].rstrip(":").lower()
            if label in summary_label_map:
                key, display, data_type, table, column = summary_label_map[label]
                val = row[1]
                norm = money(val) if data_type == "money" else (digits(val) if data_type == "identifier" else text(val))
                fields.append(_field(key, display, val, norm, data_type, table, column))

    # 2b. Extract individual transaction rows
    fields.extend(_extract_transactions(matrices))

    # ------------------------------------------------------------------
    # 3. Deduplicate: first occurrence wins for summary fields
    # ------------------------------------------------------------------
    unique = {}
    for field in fields:
        if field and field["field_key"] not in unique:
            unique[field["field_key"]] = field
    return list(unique.values())
