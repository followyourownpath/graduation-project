import re

from app.normalization.values import australian_date, text


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
    raw_str = text(raw)
    norm_str = normalised
    if key == "residential_address":
        if raw_str:
            raw_str = re.sub(r'\s+(?:Driver|Licence|Document|Expiry|Full|Name|Type|Date|Passport)\b.*$', '', raw_str, flags=re.I).strip()
        if norm_str:
            norm_str = re.sub(r'\s+(?:Driver|Licence|Document|Expiry|Full|Name|Type|Date|Passport)\b.*$', '', str(norm_str), flags=re.I).strip()
    if not raw_str:
        return None
    return {
        "section_name": "id_100",
        "applicant_number": 1,
        "field_key": key,
        "field_label": label,
        "raw_value": raw_str,
        "normalised_value": norm_str,
        "data_type": data_type,
        "mapped_table": mapped_table,
        "mapped_column": mapped_column,
        "review_status": "pending",
    }



def extract_id_fields(result):
    analysis = result.get("analyzeResult") or {}
    content = text(analysis.get("content"))
    fields = []

    # Text / Regex extraction with lookahead for next label or end of string
    name_match = re.search(r"(?:Full\s*Legal\s*Name|Full\s*Name|Name)\s*:\s*([A-Za-z\s'-]+?)(?=\s+(?:DOB|Date|Licence|Passport|Expiry|Address|Document|\b[A-Z][a-z]+:)|$)", content, re.I)
    dob_match = re.search(r"(?:Date\s*of\s*Birth|DOB|Birth\s*Date)\s*:\s*(\d{2}/\d{2}/\d{4})", content, re.I)
    doc_no_match = re.search(r"(?:Document\s*Number|Licence\s*No|Licence\s*Number|Passport\s*No|ID\s*Number)\s*:\s*([A-Z0-9 ]+?)(?=\s+(?:Expiry|Address|\b[A-Z][a-z]+:)|$)", content, re.I)
    expiry_match = re.search(r"(?:Expiry\s*Date|Expires|Expiry)\s*:\s*(\d{2}/\d{2}/\d{4})", content, re.I)
    address_match = re.search(r"(?:Residential\s*Address|Address)\s*:\s*(.+?)(?=\s+(?:Driver|\b[A-Z][a-z]+:)|$)", content, re.I)
    doc_type_match = re.search(r"Document\s*Type\s*:\s*([A-Za-z\s]+?)(?=\s+(?:Full|Date|Document|Licence|Expiry|Address|\b[A-Z][a-z]+:)|$)", content, re.I)

    fields.extend([
        _field("document_type", "Document Type", doc_type_match.group(1).strip() if doc_type_match else None,
               text(doc_type_match.group(1).strip()) if doc_type_match else None, "text"),
        _field("full_legal_name", "Full Legal Name", name_match.group(1).strip() if name_match else None,
               text(name_match.group(1).strip()) if name_match else None, "text", "applicant", "full_name"),
        _field("date_of_birth", "Date of Birth", dob_match.group(1) if dob_match else None,
               australian_date(dob_match.group(1)) if dob_match else None, "date", "applicant", "date_of_birth"),
        _field("document_number", "Document Number", doc_no_match.group(1).strip() if doc_no_match else None,
               text(doc_no_match.group(1).strip()) if doc_no_match else None, "identifier"),
        _field("expiry_date", "Expiry Date", expiry_match.group(1) if expiry_match else None,
               australian_date(expiry_match.group(1)) if expiry_match else None, "date"),
        _field("residential_address", "Residential Address", address_match.group(1).strip() if address_match else None,
               text(address_match.group(1).strip()) if address_match else None, "text", "applicant", "residential_address"),
    ])

    # Table layout key-value extraction (2-column: label | value)
    label_map = {
        "document type": ("document_type", "Document Type", "text", None, None),
        "full name": ("full_legal_name", "Full Legal Name", "text", "applicant", "full_name"),
        "full legal name": ("full_legal_name", "Full Legal Name", "text", "applicant", "full_name"),
        "name": ("full_legal_name", "Full Legal Name", "text", "applicant", "full_name"),
        "date of birth": ("date_of_birth", "Date of Birth", "date", "applicant", "date_of_birth"),
        "dob": ("date_of_birth", "Date of Birth", "date", "applicant", "date_of_birth"),
        "document number": ("document_number", "Document Number", "identifier", None, None),
        "licence no": ("document_number", "Document Number", "identifier", None, None),
        "expiry date": ("expiry_date", "Expiry Date", "date", None, None),
        "expiry": ("expiry_date", "Expiry Date", "date", None, None),
        "residential address": ("residential_address", "Residential Address", "text", "applicant", "residential_address"),
        "address": ("residential_address", "Residential Address", "text", "applicant", "residential_address"),
        # Driver Licence Link is handled specially below
        "driver licence link": None,
    }

    for matrix in _tables(analysis):
        for row in matrix:
            if len(row) < 2:
                continue
            label = row[0].rstrip(":").lower()

            # Special handling: Driver Licence Link value format is
            # "Licence No: XXXXX (Expiry: DD/MM/YYYY)"
            if label == "driver licence link":
                raw_val = row[1]
                fields.append(_field("driver_licence_link", "Driver Licence Link", raw_val, text(raw_val), "text"))
                # Extract licence number sub-field
                lic_match = re.search(r"Licence\s*No[.:]?\s*(\S+)", raw_val, re.I)
                if lic_match:
                    fields.append(_field("driver_licence_number", "Driver Licence Number",
                                         lic_match.group(1), text(lic_match.group(1)), "identifier"))
                # Extract licence expiry sub-field
                lic_exp_match = re.search(r"Expiry[.:]?\s*(\d{2}/\d{2}/\d{4})", raw_val, re.I)
                if lic_exp_match:
                    fields.append(_field("driver_licence_expiry", "Driver Licence Expiry",
                                         lic_exp_match.group(1), australian_date(lic_exp_match.group(1)), "date"))
                continue

            if label not in label_map or label_map[label] is None:
                continue

            key, display, data_type, table, column = label_map[label]
            val = row[1]
            # Address cells sometimes bleed the first word of the next row's label
            # (e.g. "...Richmond VIC 3121 Driver") — strip those artefacts.
            if key == "residential_address":
                val = re.sub(
                    r'\s+(?:Driver|Licence|Document|Expiry|Full|Name|Type|Date|Passport)\b.*$',
                    '', val, flags=re.I
                ).strip()
            norm = australian_date(val) if data_type == "date" else text(val)
            fields.append(_field(key, display, val, norm, data_type, table, column))


    # Split into regex-sourced (first batch) and table-sourced (appended later)
    # Table fields are more reliable (structured cells), so they take priority.
    regex_end = 6  # first 6 entries come from regex extraction above
    regex_fields = fields[:regex_end]
    table_fields = fields[regex_end:]

    unique = {}
    # Add regex results first (lower priority)
    for field in regex_fields:
        if field:
            unique[field["field_key"]] = field
    # Table results explicitly OVERWRITE regex results for the same key (higher priority)
    for field in table_fields:
        if field:
            unique[field["field_key"]] = field
    return list(unique.values())

