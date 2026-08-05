"""NSW Driver Licence field extraction from Azure Document Intelligence layout."""

from __future__ import annotations

import re

from app.normalization.values import australian_date, digits, text
from app.normalization.confidence_mapper import get_span_confidence


_DATE = r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|\d{2}/\d{2}/\d{4}"


def _field(key, label, raw, normalised, data_type, result, mapped_table=None, mapped_column=None):
    raw_str = text(raw) if raw is not None else ""
    if not raw_str:
        return None
    content = text(result.get("analyzeResult", {}).get("content", ""))
    start = content.find(raw_str)
    if start != -1:
        confidence = get_span_confidence(result, start, start + len(raw_str))
    else:
        confidence = None
    return {
        "section_name": "id_100",
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


def _after_label(content: str, labels: tuple[str, ...], value_pattern: str) -> str | None:
    for label in labels:
        match = re.search(
            rf"(?:{label})\s*[:.]?\s*({value_pattern})",
            content,
            re.I,
        )
        if match:
            return text(match.group(1))
    return None


def _line_after_label(content: str, labels: tuple[str, ...]) -> str | None:
    """Return the next non-empty line after a label line (card-style layout)."""
    lines = [text(line) for line in content.splitlines()]
    lines = [line for line in lines if line]
    label_re = re.compile(rf"^(?:{'|'.join(labels)})\s*[:.]?$", re.I)
    for index, line in enumerate(lines[:-1]):
        if label_re.match(line):
            candidate = lines[index + 1]
            if candidate and not label_re.match(candidate):
                return candidate
    return None


def extract_id_fields(result):
    """Extract NSW Driver Licence fields from Azure layout JSON."""
    analysis = result.get("analyzeResult") or {}
    content = text(analysis.get("content"))
    # Keep newlines for line-after-label heuristics.
    raw_content = str(analysis.get("content") or "")

    document_type = "Driver Licence" if re.search(r"Driver\s*Licence|Driver\s*License", content, re.I) else None

    jurisdiction = None
    jur_match = re.search(
        r"(New\s+South\s+Wales(?:\s*,\s*Australia)?|NSW(?:\s*,\s*Australia)?)",
        content,
        re.I,
    )
    if jur_match:
        jurisdiction = text(jur_match.group(1))
        if re.search(r"New\s+South\s+Wales", jurisdiction, re.I) and "australia" not in jurisdiction.lower():
            jurisdiction = "New South Wales, Australia"

    licence_number = (
        _after_label(content, (r"Licence\s*No\.?", r"License\s*No\.?", r"Licence\s*Number"), r"[A-Z0-9]{5,15}")
        or _line_after_label(raw_content, (r"Licence\s*No\.?", r"License\s*No\.?", r"Licence\s*Number"))
    )

    licence_class = (
        _after_label(content, (r"Licence\s*Class", r"License\s*Class", r"Class"), r"[A-Z0-9]{1,4}\b")
        or _line_after_label(raw_content, (r"Licence\s*Class", r"License\s*Class"))
    )
    if licence_class:
        licence_class = text(re.match(r"[A-Z0-9]{1,4}", licence_class, re.I).group(0)) if re.match(r"[A-Z0-9]{1,4}", licence_class, re.I) else text(licence_class)

    dob = (
        _after_label(content, (r"Date\s*of\s*Birth", r"DOB"), _DATE)
        or _line_after_label(raw_content, (r"Date\s*of\s*Birth", r"DOB"))
    )
    expiry = (
        _after_label(content, (r"Expiry\s*Date", r"Expiry", r"Expires"), _DATE)
        or _line_after_label(raw_content, (r"Expiry\s*Date", r"Expiry"))
    )

    card_number = (
        _after_label(content, (r"Card\s*Number",), r"\d(?:[\s\d]{8,20})")
        or _line_after_label(raw_content, (r"Card\s*Number",))
    )
    if not card_number:
        for match in re.finditer(r"\b(\d(?:\s+\d{3}){2,4}|\d{9,12})\b", content):
            candidate = text(match.group(1))
            if licence_number and digits(candidate) == digits(licence_number):
                continue
            if len(digits(candidate) or "") >= 9:
                card_number = candidate
                break
    if card_number and licence_number and digits(card_number) == digits(licence_number):
        card_number = None

    # Name: usually a dedicated line "Given SURNAME" (e.g. "Junhong ZHONG").
    full_name = None
    name_match = re.search(
        r"(?:Full\s*(?:Legal\s*)?Name)\s*[:.]?\s*([A-Z][A-Za-z' -]+)",
        content,
        re.I,
    )
    if name_match:
        full_name = text(name_match.group(1))
    else:
        noise = re.compile(
            r"South|Wales|Australia|Driver|Licence|License|Kensington|Todman|"
            r"Avenue|Street|Road|Expiry|Birth|Class|Number|New",
            re.I,
        )
        for line in (text(line) for line in raw_content.splitlines() if text(line)):
            match = re.fullmatch(
                r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+[A-Z]{2,})",
                line,
            )
            if match and not noise.search(match.group(1)):
                full_name = match.group(1)
                break
        if not full_name:
            # Collapsed OCR fallback: Givenname SURNAME not adjacent to address words.
            for match in re.finditer(
                r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+([A-Z]{2,})\b",
                content,
            ):
                candidate = text(f"{match.group(1)} {match.group(2)}")
                if noise.search(candidate):
                    continue
                full_name = candidate
                break

    address = None
    addr_match = re.search(
        r"(?:Residential\s*Address|Address)\s*[:.]?\s*(.+?)(?=\s+(?:Licence|License|Date|Expiry|Card|Class)\b|$)",
        content,
        re.I,
    )
    if addr_match:
        address = text(addr_match.group(1))
    else:
        # Typical AU street + suburb STATE postcode, possibly multi-line in raw content.
        addr_block = re.search(
            r"(\d+\s+[A-Z][A-Za-z0-9' /\-]*(?:AVE|AVENUE|ST|STREET|RD|ROAD|DR|DRIVE|CT|COURT|PL|PLACE|CRES|CRESCENT|HWY|PARADE|PDE|WAY|TCE|TERRACE)\.?)"
            r"[\s,]+([A-Z][A-Za-z' \-]+)\s+(NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s+(\d{4})",
            content,
            re.I,
        )
        if addr_block:
            address = text(
                f"{addr_block.group(1)}, {addr_block.group(2)} {addr_block.group(3).upper()} {addr_block.group(4)}"
            )
        else:
            # Multi-line: street / suburb STATE postcode on consecutive lines
            lines = [text(line) for line in raw_content.splitlines() if text(line)]
            for index, line in enumerate(lines[:-1]):
                if re.search(r"\b(?:AVE|AVENUE|ST|STREET|RD|ROAD|DR|DRIVE|CT|PL|CRES|CRESCENT|HWY|PDE|WAY|TCE)\b", line, re.I):
                    nxt = lines[index + 1]
                    suburb = re.search(r"^([A-Z][A-Za-z' \-]+)\s+(NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s+(\d{4})$", nxt, re.I)
                    if suburb:
                        address = text(f"{line}, {suburb.group(1)} {suburb.group(2).upper()} {suburb.group(3)}")
                        break

    fields = [
        _field("document_type", "Document Type", document_type, text(document_type) if document_type else None, "text", result),
        _field("jurisdiction", "Jurisdiction", jurisdiction, text(jurisdiction) if jurisdiction else None, "text", result),
        _field(
            "full_legal_name", "Full Legal Name", full_name, text(full_name) if full_name else None,
            "text", result, "applicant", "full_name",
        ),
        _field(
            "residential_address", "Residential Address", address, text(address) if address else None,
            "text", result, "applicant", "residential_address",
        ),
        _field(
            "licence_number", "Licence Number", licence_number,
            digits(licence_number) or text(licence_number) if licence_number else None, "identifier", result,
        ),
        _field("licence_class", "Licence Class", licence_class, text(licence_class).upper() if licence_class else None, "text", result),
        _field(
            "date_of_birth", "Date of Birth", dob, australian_date(dob) if dob else None,
            "date", result, "applicant", "date_of_birth",
        ),
        _field(
            "card_number", "Card Number", card_number,
            digits(card_number) if card_number else None, "identifier", result,
        ),
        _field("expiry_date", "Expiry Date", expiry, australian_date(expiry) if expiry else None, "date", result),
    ]
    return [field for field in fields if field]
