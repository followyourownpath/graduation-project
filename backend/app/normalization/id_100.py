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
    if not text(raw):
        return None
    return {
        "section_name": "id_100",
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


def extract_id_fields(result):
    analysis = result.get("analyzeResult") or {}
    content = text(analysis.get("content"))
    fields = []

    # Text / Regex extraction with lookahead for next label or end of string
    name_match = re.search(r"(?:Full\s*Legal\s*Name|Full\s*Name|Name)\s*:\s*([A-Za-z\s'-]+?)(?=\s+(?:DOB|Date|Licence|Passport|Expiry|Address|\b[A-Z][a-z]+:)|$)", content, re.I)
    dob_match = re.search(r"(?:Date\s*of\s*Birth|DOB|Birth\s*Date)\s*:\s*(\d{2}/\d{2}/\d{4})", content, re.I)
    doc_no_match = re.search(r"(?:Document\s*Number|Licence\s*No|Licence\s*Number|Passport\s*No|ID\s*Number)\s*:\s*([A-Z0-9 ]+?)(?=\s+(?:Expiry|Address|\b[A-Z][a-z]+:)|$)", content, re.I)
    expiry_match = re.search(r"(?:Expiry\s*Date|Expires|Expiry)\s*:\s*(\d{2}/\d{2}/\d{4})", content, re.I)
    address_match = re.search(r"(?:Residential\s*Address|Address)\s*:\s*(.+?)(?=\s+\b[A-Z][a-z]+:|$)", content, re.I)

    fields.extend([
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

    # Table layout key-value extraction fallback
    label_map = {
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
    }

    for matrix in _tables(analysis):
        for row in matrix:
            for index in range(0, len(row) - 1, 2):
                label = row[index].rstrip(":").lower()
                if label in label_map:
                    key, display, data_type, table, column = label_map[label]
                    val = row[index + 1]
                    norm = australian_date(val) if data_type == "date" else text(val)
                    fields.append(_field(key, display, val, norm, data_type, table, column))

    unique = {}
    for field in fields:
        if field and field["field_key"] not in unique:
            unique[field["field_key"]] = field
    return list(unique.values())
