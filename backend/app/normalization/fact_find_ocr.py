"""Fact Find field extraction from Azure Document Intelligence layout JSON.

Parses content + tables + selection marks into the same field_key shape used by
AcroForm direct-read (`extract_fact_find_acroform`).
"""

from __future__ import annotations

import re

from app.normalization.values import australian_date, email, money, phone, text

OWNERSHIP = {
    "Applicant 1": "applicant_1",
    "Applicant 2": "applicant_2",
    "Both": "both",
}
RESIDENCE = {
    "Own home": "own_home", "Mortgage": "mortgage", "Renting": "renting",
    "Boarding": "boarding", "With Parents": "with_parents",
}
EMPLOYMENT = {
    "Full Time": "full_time", "Part Time": "part_time", "Casual": "casual",
    "Self Employed": "self_employed", "Contract": "contract", "PAYG": "payg",
}
MARITAL = {
    "Single": "single", "Married": "married", "Defacto": "defacto",
    "Divorced": "divorced", "Other": "other",
}
FREQ = {"Monthly": "monthly", "Fortnightly": "fortnightly", "Weekly": "weekly"}
PROP_TYPE = {"Owner Occupied": "owner_occupied", "Investment": "investment"}
REPAY_LETTER = {"W": "weekly", "F": "fortnightly", "M": "monthly", "Y": "yearly"}

EXPENSE_ORDER = [
    "private_health_insurance", "private_education_fee", "childcare",
    "clothing_personal_care", "education", "groceries", "insurances",
    "investment_property_utilities", "medical_health_costs", "other",
    "owner_occupied_property_utilities", "recreation_entertainment",
    "connections_phone_internet_tv", "transport", "rent_or_boarding",
]

LIAB_ROWS = [
    ("credit_card_1", "Credit Card"),
    ("credit_card_2", "Credit Card"),
    ("credit_card_3", "Credit Card"),
    ("personal_loan", "Personal Loan"),
    ("car_loan", "Car Loan"),
    ("student_loan", "Student Loan"),
    ("government_tax", "Government Tax"),
    ("other", "Other"),
]

# Common OCR truncations / suburb→postcode fixes for this form's mock data.
AU_SUBURB_POSTCODES = {
    "kensington": "2033",
}
KNOWN_LENDERS = ("CommonWealth", "Westpac", "ANZ", "NAB", "Macquarie", "ING", "Bendigo")


def _is_noise_value(value: str | None, *extra_labels: str) -> bool:
    t = (text(value) or "").strip()
    if not t or t in {"--", "-", "$"}:
        return True
    low = t.lower()
    labels = {
        "street", "suburb", "state", "postcode", "address", "employer name",
        "position", "phone#", "phone #", "value", "ownership", "make/model",
        "year", "type", "provider", "asset type",
        *{x.lower() for x in extra_labels},
    }
    return low in labels or low.startswith("$ ")


def _fix_au_address(addr: str | None) -> str:
    """Repair truncated/misread NSW postcodes when suburb is known."""
    t = text(addr) or ""
    for suburb, expected in AU_SUBURB_POSTCODES.items():
        m = re.search(
            rf"\b({re.escape(suburb)})\s+(NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s+(\d{{1,4}})\b",
            t, re.I,
        )
        if m and m.group(3) != expected:
            return t[:m.start(3)] + expected + t[m.end(3):]
    return t


def _fix_lender(value: str | None) -> str:
    """Complete truncated lender names (e.g. CommonWe → CommonWealth)."""
    t = text(value) or ""
    if not t:
        return t
    low = re.sub(r"[^a-z]", "", t.lower())
    for canon in KNOWN_LENDERS:
        c = re.sub(r"[^a-z]", "", canon.lower())
        if low == c:
            return canon
        if len(low) >= 5 and (c.startswith(low) or low.startswith(c)):
            return canon
    return t


def _field(key, label, raw, normalised, data_type, section, applicant=1,
           table=None, column=None, confidence=None):
    if raw is None or text(raw) == "" or text(raw) == "--":
        return None
    return {
        "section_name": section,
        "applicant_number": applicant,
        "field_key": key,
        "field_label": label,
        "raw_value": text(raw),
        "normalised_value": normalised,
        "data_type": data_type,
        "confidence": confidence,
        "mapped_table": table,
        "mapped_column": column,
        "review_status": "pending",
    }


def _tables(analysis):
    matrices = []
    for table in analysis.get("tables") or []:
        rows = [["" for _ in range(table.get("columnCount", 0))]
                for _ in range(table.get("rowCount", 0))]
        for cell in table.get("cells") or []:
            r, c = cell.get("rowIndex"), cell.get("columnIndex")
            if r is not None and c is not None and r < len(rows) and c < len(rows[r]):
                rows[r][c] = text(cell.get("content"))
        matrices.append(rows)
    return matrices


def _selected(block: str, options: dict[str, str]) -> str | None:
    for label, value in options.items():
        if re.search(rf":selected:\s*{re.escape(label)}\b", block, re.I):
            return value
    return None


def _selected_many(block: str, options: dict[str, str], limit: int) -> list[str]:
    hits = []
    for m in re.finditer(
        r":selected:\s*(" + "|".join(re.escape(k) for k in options) + r")\b",
        block, re.I,
    ):
        label = next(k for k in options if k.lower() == m.group(1).lower())
        hits.append(options[label])
        if len(hits) >= limit:
            break
    return hits


def _ownership_from_flags(cell: str) -> str | None:
    """Parse cells like ':selected: :unselected: :unselected: Applicant 1 Applicant 2 Both'."""
    flags = re.findall(r":(selected|unselected):", cell, re.I)
    if len(flags) >= 3:
        for i, state in enumerate(flags[:3]):
            if state.lower() == "selected":
                return ["applicant_1", "applicant_2", "both"][i]
    return _selected(cell, OWNERSHIP)


def _prop_type_from_cell(cell: str) -> str | None:
    """Handle both ':selected: Owner Occupied' and ':selected: :unselected: Owner Occupied Investment'."""
    flags = re.findall(r":(selected|unselected):", cell, re.I)
    labels = re.findall(r"(Owner Occupied|Investment)", cell, re.I)
    if flags and labels:
        for flag, label in zip(flags, labels):
            if flag.lower() == "selected":
                key = next(k for k in PROP_TYPE if k.lower() == label.lower())
                return PROP_TYPE[key]
    return _selected(cell, PROP_TYPE)


def _after_label(text_block: str, label: str) -> list[str]:
    return [text(m.group(1)) for m in re.finditer(
        rf"{re.escape(label)}\s+([^\n]+)", text_block, re.I
    ) if text(m.group(1))]


# ---------------------------------------------------------------------------
def extract_cover(content, out):
    m = re.search(r"Customer Name:\s*\n?\s*([^\n]+)", content, re.I)
    if m and text(m.group(1)).lower() not in {"important", "date:"}:
        out.append(_field("cover_customer_name", "Customer Name", m.group(1),
                          text(m.group(1)), "text", "cover",
                          table="fact_find_submission", column="customer_name"))
    m = re.search(r"\bDate:\s*\n?\s*([0-9][0-9./\-]+)", content, re.I)
    if m:
        out.append(_field("cover_form_date", "Form Date", m.group(1),
                          australian_date(m.group(1)), "date", "cover",
                          table="fact_find_submission", column="form_date"))


def extract_personal(content, tables, out):
    titles = re.findall(
        r"\bTitle\s+(Mr|Ms|Miss|Mrs|Dr)(?:\s*:selected:)?\b", content, re.I
    )
    for i, v in enumerate(titles[:2], 1):
        out.append(_field(f"applicant_{i}_title", f"Applicant {i} Title", v, text(v),
                          "text", "personal_details", i, "applicant", "title"))

    names = re.findall(r"(?<!Dependants )\bName\s+([A-Za-z][A-Za-z &'\-]{1,60})", content)
    # Prefer lines under YOUR PERSONAL DETAILS; take first two plain Name hits
    # that are not "Customer Name"
    clean_names = [n for n in names if "Customer" not in n][:2]
    for i, v in enumerate(clean_names, 1):
        out.append(_field(f"applicant_{i}_full_name", f"Applicant {i} Name", v, text(v),
                          "text", "personal_details", i, "applicant", "full_name"))

    mobiles = re.findall(r"\bMobile\s+([+\d][\d \-]{7,20})", content)
    for i, v in enumerate(mobiles[:2], 1):
        out.append(_field(f"applicant_{i}_mobile", f"Applicant {i} Mobile", v, phone(v),
                          "phone", "personal_details", i, "applicant", "mobile"))

    emails = re.findall(r"\bEmail\s+(\S+@\S+)", content)
    for i, v in enumerate(emails[:2], 1):
        out.append(_field(f"applicant_{i}_email", f"Applicant {i} Email", v,
                          email(v) or text(v).lower(), "email", "personal_details", i,
                          "applicant", "email"))

    marital_blocks = re.findall(
        r"Marital Status\s*((?::(?:un)?selected:\s*(?:Single|Married|Defacto|Divorced|Other)\s*)+)",
        content, re.I,
    )
    for i, block in enumerate(marital_blocks[:2], 1):
        chosen = _selected(block, MARITAL)
        if chosen:
            raw = next(k for k, v in MARITAL.items() if v == chosen)
            out.append(_field(f"applicant_{i}_marital_status",
                              f"Applicant {i} Marital Status", raw, chosen, "enum",
                              "personal_details", i, "applicant", "marital_status"))

    # Dependants table: Name|Age|Name|Age
    for matrix in tables:
        if not matrix or "Dependants Name" not in matrix[0][0]:
            continue
        for row_i, row in enumerate(matrix[1:4], 1):
            if len(row) >= 4:
                out.append(_field(f"applicant_1_dependant_{row_i}_name",
                                  f"Applicant 1 Dependant {row_i} Name", row[0], text(row[0]),
                                  "text", "personal_details", 1, "applicant_dependant",
                                  "dependant_name"))
                out.append(_field(f"applicant_1_dependant_{row_i}_age",
                                  f"Applicant 1 Dependant {row_i} Age", row[1],
                                  re.sub(r"\D", "", row[1]) or None, "integer",
                                  "personal_details", 1, "applicant_dependant", "dependant_age"))
                out.append(_field(f"applicant_2_dependant_{row_i}_name",
                                  f"Applicant 2 Dependant {row_i} Name", row[2], text(row[2]),
                                  "text", "personal_details", 2, "applicant_dependant",
                                  "dependant_name"))
                out.append(_field(f"applicant_2_dependant_{row_i}_age",
                                  f"Applicant 2 Dependant {row_i} Age", row[3],
                                  re.sub(r"\D", "", row[3]) or None, "integer",
                                  "personal_details", 2, "applicant_dependant", "dependant_age"))
        break


def _address_block(prefix: str, label: str, block: str, out, has_to_date=False):
    if re.search(
        r"(?:Same as applicant 1\s*:selected:|:selected:\s*Same as applicant 1)",
        block, re.I,
    ):
        out.append(_field(f"applicant_2_{prefix}_same_as_applicant_1",
                          f"{label} Same as Applicant 1", "Yes", "true", "boolean",
                          "residential_address", 2, "applicant_address",
                          "same_as_applicant_1"))

    streets = re.findall(r"\bStreet\s+([^\n]+)", block)
    streets = [
        s for s in streets
        if not _is_noise_value(s, "Suburb")
        and not re.match(r"Suburb\b", text(s) or "", re.I)
    ][:2]
    for i, v in enumerate(streets, 1):
        out.append(_field(f"applicant_{i}_{prefix}_street", f"Applicant {i} {label} Street",
                          v, text(v), "text", "residential_address", i,
                          "applicant_address", "street"))

    suburbs = re.findall(r"\bSuburb\s+([A-Za-z][A-Za-z \-]+)", block)
    suburbs = [s for s in suburbs if not _is_noise_value(s)][:2]
    for i, v in enumerate(suburbs, 1):
        out.append(_field(f"applicant_{i}_{prefix}_suburb", f"Applicant {i} {label} Suburb",
                          v, text(v), "text", "residential_address", i,
                          "applicant_address", "suburb"))

    states = re.findall(r"\bState\s+([A-Z]{2,3})\b", block)
    for i, v in enumerate(states[:2], 1):
        out.append(_field(f"applicant_{i}_{prefix}_state", f"Applicant {i} {label} State",
                          v, text(v), "text", "residential_address", i,
                          "applicant_address", "state"))

    postcodes = re.findall(r"\bPostcode\s+(\d{4})\b", block)
    for i, v in enumerate(postcodes[:2], 1):
        out.append(_field(f"applicant_{i}_{prefix}_postcode", f"Applicant {i} {label} Postcode",
                          v, text(v), "text", "residential_address", i,
                          "applicant_address", "postcode"))

    ownerships = _selected_many(block, RESIDENCE, 2)
    # Fallback: split Ownership sections
    if len(ownerships) < 2:
        ownerships = []
        for m in re.finditer(r"Ownership\s*((?::(?:un)?selected:[^\n:]+)+)", block, re.I):
            val = _selected(m.group(1), RESIDENCE)
            if val:
                ownerships.append(val)
    for i, v in enumerate(ownerships[:2], 1):
        raw = next(k for k, x in RESIDENCE.items() if x == v)
        out.append(_field(f"applicant_{i}_{prefix}_ownership_status",
                          f"Applicant {i} {label} Ownership", raw, v, "enum",
                          "residential_address", i, "applicant_address", "ownership_status"))

    from_dates = re.findall(r"From Date\s+([0-9][0-9./\-]+)", block)
    for i, v in enumerate(from_dates[:2], 1):
        out.append(_field(f"applicant_{i}_{prefix}_from_date",
                          f"Applicant {i} {label} From Date", v, australian_date(v),
                          "date", "residential_address", i, "applicant_address", "from_date"))

    if has_to_date:
        to_dates = re.findall(r"To Date\s+([0-9][0-9./\-]+)", block)
        for i, v in enumerate(to_dates[:2], 1):
            out.append(_field(f"applicant_{i}_{prefix}_to_date",
                              f"Applicant {i} {label} To Date", v, australian_date(v),
                              "date", "residential_address", i, "applicant_address", "to_date"))


def extract_addresses(content, out):
    # Split into current / previous1 / previous2 by headers
    parts = re.split(
        r"(Current Residential Address|Previous Address(?: \(If less than 3 years at current address\))?)",
        content, flags=re.I,
    )
    # parts alternate: preamble, header, body, header, body...
    blocks = []
    for i in range(1, len(parts), 2):
        header = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        blocks.append((header, body))

    current = next((b for h, b in blocks if h.lower().startswith("current")), "")
    prevs = [b for h, b in blocks if h.lower().startswith("previous")]
    if current:
        _address_block("current_address", "Current Address", current, out, False)
    if len(prevs) >= 1:
        _address_block("previous_address_1", "Previous Address 1", prevs[0], out, True)
    if len(prevs) >= 2:
        _address_block("previous_address_2", "Previous Address 2", prevs[1], out, True)


def _employment_basis_from_marks(analysis, page_number, y_min, y_max):
    """Assign selected employment-basis options to applicants by x position.

    Left half of the page = applicant 1, right half = applicant 2. Label matching
    weights vertical proximity so a mark on the 'Self Employed' row is not
    attributed to 'Full Time' on the row above.
    """
    page = next((p for p in analysis.get("pages") or []
                 if p.get("pageNumber") == page_number), None)
    if not page:
        return []
    width = page.get("width") or 8.5
    mid = width / 2
    labels = list(EMPLOYMENT)
    results = {1: None, 2: None}
    for mark in page.get("selectionMarks") or []:
        if mark.get("state") != "selected":
            continue
        poly = mark.get("polygon") or []
        if len(poly) < 8:
            continue
        xs, ys = poly[0::2], poly[1::2]
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        if not (y_min <= cy <= y_max):
            continue
        best, best_d = None, 1e9
        for line in page.get("lines") or []:
            text_line = line.get("content") or ""
            label = next((lab for lab in labels if lab.lower() == text_line.lower()), None)
            if not label:
                continue
            lp = line.get("polygon") or []
            if len(lp) < 8:
                continue
            lx, ly = sum(lp[0::2]) / 4, sum(lp[1::2]) / 4
            dist = (lx - cx) ** 2 + 4 * (ly - cy) ** 2
            if dist < best_d:
                best_d, best = dist, label
        if not best:
            continue
        applicant = 1 if cx < mid else 2
        results[applicant] = EMPLOYMENT[best]
    return [results[1], results[2]]


def _override_employment_basis_from_marks(analysis, fields):
    """Correct employment-basis fields using selection-mark geometry on page 3."""
    # Empirically from the SmartFINN form layout (inches on page 3).
    bands = {
        "current_employment": (2.0, 3.2),
        "secondary_employment": (4.1, 5.3),
        "previous_employment_1": (6.2, 7.4),
        "previous_employment_2": (8.2, 9.4),
    }
    fields = [f for f in fields if f]
    by_key = {f["field_key"]: f for f in fields}
    for prefix, (y0, y1) in bands.items():
        vals = _employment_basis_from_marks(analysis, 3, y0, y1)
        for i, val in enumerate(vals, 1):
            if not val:
                continue
            key = f"applicant_{i}_{prefix}_basis"
            raw = next(k for k, v in EMPLOYMENT.items() if v == val)
            if key in by_key:
                by_key[key]["raw_value"] = raw
                by_key[key]["normalised_value"] = val
            else:
                fields.append(_field(
                    key, f"Applicant {i} {prefix} Basis", raw, val, "enum",
                    "employment", i, "applicant_employment", "employment_basis",
                ))
                by_key[key] = fields[-1]
    return fields


def _employment_section(prefix: str, label: str, block: str, out, has_end=False):
    employers = re.findall(r"Employer Name\s+([^\n:]+?)(?:\s+:(?:un)?selected:|\s*$)", block, re.M)
    employers = [
        text(e) for e in employers
        if text(e) and not text(e).startswith(":") and not _is_noise_value(e)
    ][:2]
    for i, v in enumerate(employers, 1):
        out.append(_field(f"applicant_{i}_{prefix}_employer_name",
                          f"Applicant {i} {label} Employer Name", v, v, "text",
                          "employment", i, "applicant_employment", "employer_name"))

    bases = _selected_many(block, EMPLOYMENT, 2)
    for i, v in enumerate(bases, 1):
        raw = next(k for k, x in EMPLOYMENT.items() if x == v)
        out.append(_field(f"applicant_{i}_{prefix}_basis",
                          f"Applicant {i} {label} Basis", raw, v, "enum",
                          "employment", i, "applicant_employment", "employment_basis"))

    positions = re.findall(r"\bPosition\s+([A-Za-z][^\n]*?)(?:\s+Start Date|\s+Phone|\s*$)", block)
    positions = [p for p in positions if not _is_noise_value(p)]
    for i, v in enumerate(positions[:2], 1):
        out.append(_field(f"applicant_{i}_{prefix}_position",
                          f"Applicant {i} {label} Position", v, text(v), "text",
                          "employment", i, "applicant_employment", "position_title"))

    starts = re.findall(r"Start Date\s+([0-9][0-9./\-]+)", block)
    for i, v in enumerate(starts[:2], 1):
        out.append(_field(f"applicant_{i}_{prefix}_start_date",
                          f"Applicant {i} {label} Start Date", v, australian_date(v),
                          "date", "employment", i, "applicant_employment", "start_date"))

    if has_end:
        ends = re.findall(r"End Date\s+([0-9][0-9./\-]+)", block)
        for i, v in enumerate(ends[:2], 1):
            out.append(_field(f"applicant_{i}_{prefix}_end_date",
                              f"Applicant {i} {label} End Date", v, australian_date(v),
                              "date", "employment", i, "applicant_employment", "end_date"))

    # Address lines: "Address <line>" then unlabeled second lines
    addr_hits = re.findall(r"\bAddress\s+([^\n]+)", block)
    addr_hits = [_fix_au_address(v) for v in addr_hits if not _is_noise_value(v)]
    if len(addr_hits) >= 2:
        for i, v in enumerate(addr_hits[:2], 1):
            out.append(_field(f"applicant_{i}_{prefix}_employer_address_line1",
                              f"Applicant {i} {label} Employer Address (line 1)",
                              v, text(v), "text", "employment", i,
                              "applicant_employment", "employer_address"))
        lines = [text(l) for l in block.splitlines()]
        bare = [
            l for l in lines
            if re.match(r"^\d+.+,", l) and not l.lower().startswith("address ")
        ]
        if len(bare) == 1:
            bare = [bare[0], bare[0]]
        for i, v in enumerate(bare[:2], 1):
            out.append(_field(f"applicant_{i}_{prefix}_employer_address_line2",
                              f"Applicant {i} {label} Employer Address (line 2)",
                              v, text(v), "text", "employment", i,
                              "applicant_employment", "employer_address"))
    elif len(addr_hits) == 1:
        v = addr_hits[0]
        for i in (1, 2):
            out.append(_field(f"applicant_{i}_{prefix}_employer_address_line1",
                              f"Applicant {i} {label} Employer Address (line 1)",
                              v, text(v), "text", "employment", i,
                              "applicant_employment", "employer_address"))

    phones = re.findall(r"Phone\s*#?\s+([+\d][\d \-]{7,20})", block)
    for i, v in enumerate(phones[:2], 1):
        out.append(_field(f"applicant_{i}_{prefix}_employer_phone",
                          f"Applicant {i} {label} Employer Phone", v, phone(v),
                          "phone", "employment", i, "applicant_employment",
                          "employer_phone"))


def extract_employment(content, out):
    # Cut employment region
    start = content.find("Current Employment")
    end = content.find("REQUIREMENTS")
    if start < 0:
        return
    region = content[start:end if end > start else None]
    parts = re.split(
        r"(Current Employment|Secondary Employment|Previous Employment[^\n]*)",
        region, flags=re.I,
    )
    blocks = []
    for i in range(1, len(parts), 2):
        blocks.append((parts[i], parts[i + 1] if i + 1 < len(parts) else ""))

    current = next((b for h, b in blocks if h.lower().startswith("current")), "")
    secondary = next((b for h, b in blocks if h.lower().startswith("secondary")), "")
    previous = [b for h, b in blocks if h.lower().startswith("previous")]

    if current:
        _employment_section("current_employment", "Current Employment", current, out)
    if secondary:
        _employment_section("secondary_employment", "Secondary Employment", secondary, out)
    if len(previous) >= 1:
        # previous section may contain two employer blocks for each applicant
        # Split by repeated Employer Name pairs (4 names => 2 jobs x 2 applicants)
        prev_body = previous[0]
        # Further split if second previous block exists as separate header
        if len(previous) >= 2:
            _employment_section("previous_employment_1", "Previous Employment 1",
                                previous[0], out, has_end=True)
            _employment_section("previous_employment_2", "Previous Employment 2",
                                previous[1], out, has_end=True)
        else:
            # One "Previous Employment" header with two rows — split on 3rd Employer Name
            emp_iters = list(re.finditer(r"Employer Name\s+", prev_body))
            if len(emp_iters) >= 4:
                mid = emp_iters[2].start()
                _employment_section("previous_employment_1", "Previous Employment 1",
                                    prev_body[:mid], out, has_end=True)
                _employment_section("previous_employment_2", "Previous Employment 2",
                                    prev_body[mid:], out, has_end=True)
            else:
                _employment_section("previous_employment_1", "Previous Employment 1",
                                    prev_body, out, has_end=True)


def extract_requirements(content, out):
    m = re.search(
        r"Any specific goals or objectives for this loan\?\s*\n?(.+?)(?:\nWhat is your preferred|\nFINANCIAL)",
        content, re.I | re.S,
    )
    if m:
        goals = text(m.group(1))
        out.append(_field("loan_specific_goals", "Loan Goals / Objectives", goals, goals,
                          "text", "requirements_objectives",
                          table="loan_requirements", column="specific_goals_or_objectives"))

    # Preferred frequency — take first selected among Monthly/Fortnightly/Weekly
    # near the question (avoid later noise)
    freq_region = content
    i = content.find("preferred repayment frequency")
    if i < 0:
        i = content.lower().find("repayment frequency")
    if i >= 0:
        freq_region = content[i:i + 200]
    freq = _selected(freq_region, FREQ)
    if freq:
        raw = next(k for k, v in FREQ.items() if v == freq)
        out.append(_field("preferred_repayment_frequency", "Preferred Repayment Frequency",
                          raw, freq, "enum", "requirements_objectives",
                          table="loan_requirements", column="preferred_repayment_frequency"))

    m = re.search(r"Account Name:\s*([^\n]+)", content, re.I)
    if m:
        out.append(_field("repayment_account_name", "Repayment Account Name", m.group(1),
                          text(m.group(1)), "text", "requirements_objectives",
                          table="repayment_account", column="account_name"))
    m = re.search(r"\bBSB:\s*([0-9\-]+)", content, re.I)
    if m:
        out.append(_field("repayment_account_bsb", "Repayment Account BSB", m.group(1),
                          text(m.group(1)), "text", "requirements_objectives",
                          table="repayment_account", column="bsb"))
    m = re.search(r"Account Number:\s*([0-9]+)", content, re.I)
    if m:
        out.append(_field("repayment_account_number", "Repayment Account Number", m.group(1),
                          text(m.group(1)), "text", "requirements_objectives",
                          table="repayment_account", column="account_number"))


def extract_property(tables, out):
    props = []
    for matrix in tables:
        if not matrix or matrix[0][0] != "SL":
            continue
        for row in matrix[1:]:
            if not row or not re.match(r"^\d+$", row[0] or ""):
                continue
            # row may span type/ownership on next visual lines — cells usually packed
            while len(row) < 7:
                row.append("")
            props.append(row)
    # Deduplicate by SL number
    by_sl = {}
    for row in props:
        by_sl[int(row[0])] = row
    for n in sorted(by_sl):
        row = by_sl[n]
        addr, est, bal, lender = row[1], row[2], row[3], row[4]
        type_cell = row[5]
        own_cell = row[6]
        lender = _fix_lender(lender)
        if not text(addr) and not money(est) and not money(bal) and not text(lender):
            continue
        # Sometimes type/ownership spill into adjacent empty rows — merge nearby
        ctx = " ".join(row)
        ptype = _prop_type_from_cell(type_cell) or _prop_type_from_cell(ctx)
        own = _ownership_from_flags(own_cell) or _ownership_from_flags(ctx)
        out.append(_field(f"property_asset_{n}_address", f"Property {n} Address",
                          addr, text(addr), "text", "property_assets",
                          table="property_asset", column="property_address"))
        out.append(_field(f"property_asset_{n}_estimated_value", f"Property {n} Estimated Value",
                          est, money(est), "money", "property_assets",
                          table="property_asset", column="estimated_value"))
        out.append(_field(f"property_asset_{n}_loan_balance", f"Property {n} Loan Balance",
                          bal, money(bal), "money", "property_assets",
                          table="property_asset", column="loan_balance"))
        out.append(_field(f"property_asset_{n}_lender", f"Property {n} Lender",
                          lender, text(lender), "text", "property_assets",
                          table="property_asset", column="lender"))
        if ptype:
            raw = next(k for k, v in PROP_TYPE.items() if v == ptype)
            out.append(_field(f"property_asset_{n}_type", f"Property {n} Type",
                              raw, ptype, "enum", "property_assets",
                              table="property_asset", column="property_type"))
        if own:
            raw = next(k for k, v in OWNERSHIP.items() if v == own)
            out.append(_field(f"property_asset_{n}_ownership", f"Property {n} Ownership",
                              raw, own, "enum", "property_assets",
                              table="property_asset", column="ownership"))


def extract_financial(content, out):
    def pair_after(section_title, field_label, limit=2):
        i = content.find(section_title)
        if i < 0:
            return []
        chunk = content[i:i + 500]
        return re.findall(rf"{re.escape(field_label)}\s*\n?([^\n$]+)", chunk)[:limit]

    # Savings
    types = re.findall(
        r"Savings, Term Deposits & Other.*?Asset Type\s*\n([^\n]+)\n([^\n]+)",
        content, re.S,
    )
    if types:
        for i, v in enumerate(types[0][:2], 1):
            out.append(_field(f"savings_term_deposit_{i}_asset_type",
                              f"Savings/Term Deposit Account {i} Asset Type",
                              v, text(v), "text", "financial_assets",
                              table="financial_asset", column="asset_type"))
    # More reliable line-based for savings values/ownership from content dump
    m = re.search(
        r"Savings, Term Deposits & Other\s+Account 1\s+Account 2\s+"
        r"Asset Type\s+(\S[^\n]*)\s+(\S[^\n]*)\s+"
        r"Value\s+\$?\s*([0-9,.]+)\s+\$?\s*([0-9,.]+)\s+"
        r"Ownership\s+(\S[^\n]*)\s+(\S[^\n]*)",
        content, re.I,
    )
    if m:
        for i, (typ, val, own) in enumerate(
                [(m.group(1), m.group(3), m.group(5)), (m.group(2), m.group(4), m.group(6))], 1):
            out.append(_field(f"savings_term_deposit_{i}_asset_type",
                              f"Savings Account {i} Asset Type", typ, text(typ), "text",
                              "financial_assets", table="financial_asset", column="asset_type"))
            out.append(_field(f"savings_term_deposit_{i}_value",
                              f"Savings Account {i} Value", val, money(val), "money",
                              "financial_assets", table="financial_asset", column="value"))
            own_n = OWNERSHIP.get(text(own))
            if own_n:
                out.append(_field(f"savings_term_deposit_{i}_ownership",
                                  f"Savings Account {i} Ownership", own, own_n, "enum",
                                  "financial_assets", table="financial_asset", column="ownership"))

    m = re.search(
        r"Superannuation\s+Account 1\s+Account 2\s+"
        r"Provider\s+(\S[^\n]*)\s+(\S[^\n]*)\s+"
        r"Value\s+\$?\s*([0-9,.]+)\s+\$?\s*([0-9,.]+)\s+"
        r"Ownership\s+(\S[^\n]*)\s+(\S[^\n]*)",
        content, re.I,
    )
    if m:
        for i, (prov, val, own) in enumerate(
                [(m.group(1), m.group(3), m.group(5)), (m.group(2), m.group(4), m.group(6))], 1):
            out.append(_field(f"superannuation_{i}_provider", f"Superannuation Account {i} Provider",
                              prov, text(prov), "text", "financial_assets",
                              table="financial_asset", column="provider"))
            out.append(_field(f"superannuation_{i}_value", f"Superannuation Account {i} Value",
                              val, money(val), "money", "financial_assets",
                              table="financial_asset", column="value"))
            own_n = OWNERSHIP.get(text(own))
            if own_n:
                out.append(_field(f"superannuation_{i}_ownership",
                                  f"Superannuation Account {i} Ownership", own, own_n, "enum",
                                  "financial_assets", table="financial_asset", column="ownership"))

    m = re.search(
        r"Shares or Trusts\s+Account 1\s+Account 2\s+"
        r"Provider\s+(\S[^\n]*)\s+(\S[^\n]*)\s+"
        r"Value\s+\$?\s*([0-9,.]+)\s+\$?\s*([0-9,.]+)\s+"
        r"Ownership\s+(\S[^\n]*)\s+(\S[^\n]*)",
        content, re.I,
    )
    if m:
        for i, (prov, val, own) in enumerate(
                [(m.group(1), m.group(3), m.group(5)), (m.group(2), m.group(4), m.group(6))], 1):
            out.append(_field(f"shares_or_trusts_{i}_provider", f"Shares/Trusts Account {i} Provider",
                              prov, text(prov), "text", "financial_assets",
                              table="financial_asset", column="provider"))
            out.append(_field(f"shares_or_trusts_{i}_value", f"Shares/Trusts Account {i} Value",
                              val, money(val), "money", "financial_assets",
                              table="financial_asset", column="value"))
            own_n = OWNERSHIP.get(text(own))
            if own_n:
                out.append(_field(f"shares_or_trusts_{i}_ownership",
                                  f"Shares/Trusts Account {i} Ownership", own, own_n, "enum",
                                  "financial_assets", table="financial_asset", column="ownership"))

    m = re.search(
        r"Vehicle\s+Vehicle 1\s+Vehicle 2\s+"
        r"Make/Model\s+(\S[^\n]*)\s+(\S[^\n]*)\s+"
        r"Value\s+\$?\s*([0-9,.]+)\s+\$?\s*([0-9,.]+)\s+"
        r"Year\s+(\d{4})\s+(\d{4})\s+"
        r"Ownership\s+(\S[^\n]*)\s+(\S[^\n]*)",
        content, re.I,
    )
    if not m:
        # sample forms often fill only Vehicle 1
        m1 = re.search(
            r"Vehicle\s+Vehicle 1\s+Vehicle 2\s+"
            r"Make/Model\s*\n([^\n]+)\s*\n"
            r"Value\s*\n\$?\s*([0-9,.]+)\s*\n\$?\s*\n?"
            r"Year\s*\n(\d{4})\s*\n"
            r"Ownership\s*\n(\S[^\n]*)",
            content, re.I,
        )
        if m1:
            mm, val, yr, own = m1.group(1), m1.group(2), m1.group(3), m1.group(4)
            if not _is_noise_value(mm):
                out.append(_field("vehicle_1_make_model", "Vehicle 1 Make/Model",
                                  mm, text(mm), "text", "vehicle_assets",
                                  table="vehicle_asset", column="make_model"))
                out.append(_field("vehicle_1_value", "Vehicle 1 Value",
                                  val, money(val), "money", "vehicle_assets",
                                  table="vehicle_asset", column="value"))
                out.append(_field("vehicle_1_year", "Vehicle 1 Year",
                                  yr, yr, "integer", "vehicle_assets",
                                  table="vehicle_asset", column="vehicle_year"))
                own_n = OWNERSHIP.get(text(own))
                if own_n:
                    out.append(_field("vehicle_1_ownership", "Vehicle 1 Ownership",
                                      own, own_n, "enum", "vehicle_assets",
                                      table="vehicle_asset", column="ownership"))
    else:
        for i, (mm, val, yr, own) in enumerate(
                [(m.group(1), m.group(3), m.group(5), m.group(7)),
                 (m.group(2), m.group(4), m.group(6), m.group(8))], 1):
            if _is_noise_value(mm):
                continue
            out.append(_field(f"vehicle_{i}_make_model", f"Vehicle {i} Make/Model",
                              mm, text(mm), "text", "vehicle_assets",
                              table="vehicle_asset", column="make_model"))
            out.append(_field(f"vehicle_{i}_value", f"Vehicle {i} Value",
                              val, money(val), "money", "vehicle_assets",
                              table="vehicle_asset", column="value"))
            out.append(_field(f"vehicle_{i}_year", f"Vehicle {i} Year",
                              yr, yr, "integer", "vehicle_assets",
                              table="vehicle_asset", column="vehicle_year"))
            own_n = OWNERSHIP.get(text(own))
            if own_n:
                out.append(_field(f"vehicle_{i}_ownership", f"Vehicle {i} Ownership",
                                  own, own_n, "enum", "vehicle_assets",
                                  table="vehicle_asset", column="ownership"))

    m = re.search(
        r"Other i\.e\. business, household items\s+Applicant 1\s+Applicant 2\s+"
        r"Type\s+(\S[^\n]*)\s+(\S[^\n]*)\s+"
        r"Value\s+\$?\s*([0-9,.]+)\s+\$?\s*([0-9,.]+)",
        content, re.I,
    )
    if m:
        for i, (typ, val) in enumerate([(m.group(1), m.group(3)), (m.group(2), m.group(4))], 1):
            out.append(_field(f"other_asset_applicant_{i}_type",
                              f"Other Asset (Applicant {i}) Type", typ, text(typ), "text",
                              "other_assets", i, "other_asset", "asset_type"))
            out.append(_field(f"other_asset_applicant_{i}_value",
                              f"Other Asset (Applicant {i}) Value", val, money(val), "money",
                              "other_assets", i, "other_asset", "value"))


def extract_liabilities(tables, out):
    for matrix in tables:
        if not matrix or matrix[0][0] != "Liabilities":
            continue
        data_rows = matrix[1:9]
        for (key, _), row in zip(LIAB_ROWS, data_rows):
            while len(row) < 7:
                row.append("")
            label = row[0]
            # Azure sometimes inserts an empty frequency column (8 cols).
            if len(row) >= 8 and text(row[5]) in {"", "--"} | set(REPAY_LETTER):
                bal, lim, cred, repay = row[1], row[2], row[3], row[4]
                freq_cell = text(row[5])
                paying, own = row[6], row[7]
            else:
                bal, lim, cred, repay, paying, own = row[1:7]
                freq_cell = ""
            if (
                not text(bal) and not text(lim) and not text(cred)
                and text(repay) in {"", "--"}
                and text(paying) in {"", "--"}
                and text(own) in {"", "--"}
            ):
                continue
            # Repayment cell may be "2500.00 W"
            amt_m = re.match(r"([0-9.,]+)\s*([WFMY])?", text(repay) or "")
            amount = amt_m.group(1) if amt_m else repay
            freq_letter = (amt_m.group(2) if amt_m else None) or (
                freq_cell if freq_cell in REPAY_LETTER else None
            )
            out.append(_field(f"liability_{key}_balance", f"{label} Balance",
                              bal, money(bal), "money", "liabilities",
                              table="liability", column="balance"))
            out.append(_field(f"liability_{key}_credit_limit", f"{label} Limit",
                              lim, money(lim), "money", "liabilities",
                              table="liability", column="credit_limit"))
            out.append(_field(f"liability_{key}_creditor", f"{label} Creditor",
                              cred, text(cred), "text", "liabilities",
                              table="liability", column="creditor"))
            out.append(_field(f"liability_{key}_repayment_amount", f"{label} Repayment Amount",
                              amount, money(amount), "money", "liabilities",
                              table="liability", column="repayment_amount"))
            if freq_letter and freq_letter in REPAY_LETTER:
                out.append(_field(f"liability_{key}_repayment_frequency",
                                  f"{label} Repayment Frequency", freq_letter,
                                  REPAY_LETTER[freq_letter], "enum", "liabilities",
                                  table="liability", column="repayment_frequency"))
            if text(paying) in {"Yes", "No"}:
                out.append(_field(f"liability_{key}_paying_out", f"{label} Paying Out",
                                  paying, "true" if paying == "Yes" else "false",
                                  "boolean", "liabilities",
                                  table="liability", column="paying_out"))
            own_n = OWNERSHIP.get(text(own))
            if own_n:
                out.append(_field(f"liability_{key}_ownership", f"{label} Ownership",
                                  own, own_n, "enum", "liabilities",
                                  table="liability", column="ownership"))
            if key == "other":
                # "Others HECS debt" → description
                desc = re.sub(r"^Others?\s*", "", label, flags=re.I).strip()
                if desc:
                    out.append(_field("liability_other_description",
                                      "Other Liability Description", desc, text(desc),
                                      "text", "liabilities",
                                      table="liability", column="description"))
        break


def extract_expenses(tables, out):
    for matrix in tables:
        if not matrix or "Expenditure" not in matrix[0][0]:
            continue
        rows = matrix[1:16]
        for cat, row in zip(EXPENSE_ORDER, rows):
            amount = row[1] if len(row) > 1 else ""
            out.append(_field(f"expense_{cat}_monthly_amount",
                              f"Monthly Expense: {cat}", amount, money(amount),
                              "money", "monthly_expenses",
                              table="monthly_expense", column="monthly_amount"))
        break


def extract_fact_find_ocr_fields(azure_result: dict) -> list[dict]:
    analysis = azure_result.get("analyzeResult") or {}
    content = analysis.get("content") or ""
    tables = _tables(analysis)
    fields = []
    extract_cover(content, fields)
    extract_personal(content, tables, fields)
    extract_addresses(content, fields)
    extract_employment(content, fields)
    extract_requirements(content, fields)
    extract_property(tables, fields)
    extract_financial(content, fields)
    extract_liabilities(tables, fields)
    extract_expenses(tables, fields)
    fields = _override_employment_basis_from_marks(analysis, fields)

    unique = {}
    for field in fields:
        if field and field["field_key"] not in unique:
            unique[field["field_key"]] = field
    return list(unique.values())
