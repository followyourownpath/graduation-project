"""ATO Notice of Assessment field extraction from Azure layout JSON."""

from __future__ import annotations

import re

from app.normalization.values import australian_date, digits, money, text


# Always emit these keys (null when absent) so the frontend can reserve slots.
REQUIRED_KEYS = (
    "taxpayer_name",
    "taxpayer_address",
    "tfn",
    "ato_reference",
    "year_ended",
    "income_year",
    "date_of_issue",
    "taxable_income",
    "tax_on_taxable_income",
    "low_income_tax_offset",
    "non_refundable_tax_offsets",
    "assessed_tax_payable",
    "medicare_levy",
    "other_liabilities",
    "tax_offset_refunds",
    "payg_withholding_credits",
    "payg_credits_and_entitlements",
    "result_of_notice_amount",
    "result_of_notice_direction",
    "outcome_amount",
    "outcome_direction",
    "refund_amount",
    "refund_status",
    "refund_reference",
)

LABELS = {
    "taxpayer_name": "Taxpayer Name",
    "taxpayer_address": "Taxpayer Address",
    "tfn": "Tax File Number",
    "ato_reference": "ATO Reference",
    "year_ended": "Year Ended",
    "income_year": "Income Year",
    "date_of_issue": "Date of Issue",
    "taxable_income": "Taxable Income",
    "tax_on_taxable_income": "Tax on Taxable Income",
    "low_income_tax_offset": "Low Income Tax Offset",
    "non_refundable_tax_offsets": "Total Non-refundable Tax Offsets",
    "assessed_tax_payable": "Assessed Tax Payable",
    "medicare_levy": "Medicare Levy",
    "other_liabilities": "Total Other Liabilities",
    "tax_offset_refunds": "Tax Offset Refunds",
    "payg_withholding_credits": "PAYG Withholding Credits",
    "payg_credits_and_entitlements": "Total PAYG and Other Entitlements",
    "result_of_notice_amount": "Result of This Notice Amount",
    "result_of_notice_direction": "Result of This Notice Direction",
    "outcome_amount": "Outcome Amount",
    "outcome_direction": "Outcome Direction",
    "refund_amount": "Refund Amount",
    "refund_status": "Refund Status",
    "refund_reference": "Refund Reference",
}

DATA_TYPES = {
    "taxpayer_name": "text",
    "taxpayer_address": "text",
    "tfn": "identifier",
    "ato_reference": "identifier",
    "year_ended": "date",
    "income_year": "text",
    "date_of_issue": "date",
    "taxable_income": "money",
    "tax_on_taxable_income": "money",
    "low_income_tax_offset": "money",
    "non_refundable_tax_offsets": "money",
    "assessed_tax_payable": "money",
    "medicare_levy": "money",
    "other_liabilities": "money",
    "tax_offset_refunds": "money",
    "payg_withholding_credits": "money",
    "payg_credits_and_entitlements": "money",
    "result_of_notice_amount": "money",
    "result_of_notice_direction": "enum",
    "outcome_amount": "money",
    "outcome_direction": "enum",
    "refund_amount": "money",
    "refund_status": "text",
    "refund_reference": "identifier",
}

_MONEY = r"\$?\s*[\d,]+(?:\.\d{2})?"
_DIR = r"(?:CR|DR)"
_DATE_LONG = r"\d{1,2}\s+[A-Za-z]+\s+\d{4}|\d{1,2}-[A-Za-z]{3}-\d{2,4}|\d{2}/\d{2}/\d{4}"


def _field(key, raw, normalised):
    raw_str = text(raw) if raw is not None and text(raw) else None
    return {
        "section_name": "ato_notice",
        "applicant_number": 1,
        "field_key": key,
        "field_label": LABELS[key],
        "raw_value": raw_str,
        "normalised_value": normalised if raw_str is not None else None,
        "data_type": DATA_TYPES[key],
        "mapped_table": None,
        "mapped_column": None,
        "review_status": "pending",
    }


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


def _money_near(content: str, patterns: tuple[str, ...]):
    for pattern in patterns:
        match = re.search(rf"{pattern}\s*[:.]?\s*({_MONEY})", content, re.I)
        if match:
            return text(match.group(1)), money(match.group(1))
    return None, None


def _row_money(matrices, label_patterns: tuple[str, ...], prefer_column=("debit", "credit", None)):
    """Find a description row and return (raw, money, direction) from debit/credit cols."""
    for matrix in matrices:
        if len(matrix) < 2 or len(matrix[0]) < 2:
            continue
        header = [col.lower() for col in matrix[0]]
        debit_col = next((i for i, h in enumerate(header) if "debit" in h), None)
        credit_col = next((i for i, h in enumerate(header) if "credit" in h), None)
        desc_col = 0
        for row in matrix[1:]:
            desc = row[desc_col] if row else ""
            if not any(re.search(p, desc, re.I) for p in label_patterns):
                continue
            # Prefer explicit debit/credit cells
            for kind, col in (("DR", debit_col), ("CR", credit_col)):
                if col is None or col >= len(row):
                    continue
                cell = row[col]
                if text(cell) and money(cell) is not None:
                    return text(cell), money(cell), kind
            # Fallback: amount embedded in description or any numeric cell
            embedded = re.search(rf"({_MONEY})\s*({_DIR})?", desc, re.I)
            if embedded and money(embedded.group(1)) is not None:
                direction = embedded.group(2).upper() if embedded.group(2) else None
                return text(embedded.group(0)), money(embedded.group(1)), direction
            for cell in row[1:]:
                if money(cell) is not None:
                    return text(cell), money(cell), None
    return None, None, None


def _derive_income_year(year_ended_raw: str | None, content: str) -> tuple[str | None, str | None]:
    """Return (raw, normalised) income year like 2021–2022 from 'year ended 30 June 2022'."""
    match = re.search(r"year\s+ended\s+(\d{1,2}\s+[A-Za-z]+\s+(\d{4}))", content, re.I)
    if match:
        end_year = int(match.group(2))
        return text(match.group(0)), f"{end_year - 1}–{end_year}"
    if year_ended_raw:
        parsed = australian_date(year_ended_raw)
        if parsed:
            end_year = int(parsed[:4])
            return year_ended_raw, f"{end_year - 1}–{end_year}"
    # Direct "2022–2023" / "2022-2023"
    direct = re.search(r"(20\d{2})\s*[–-]\s*(20\d{2})", content)
    if direct:
        return text(direct.group(0)), f"{direct.group(1)}–{direct.group(2)}"
    return None, None


def extract_ato_notice_fields(result):
    analysis = result.get("analyzeResult") or {}
    content = text(analysis.get("content"))
    raw_content = str(analysis.get("content") or "")
    matrices = _tables(analysis)
    values: dict[str, tuple] = {key: (None, None) for key in REQUIRED_KEYS}

    # --- Header identity ---
    name_match = re.search(
        r"\b(MR|MRS|MS|MISS|MX)\s+([A-Z][A-Z' \-]+)\b",
        content,
    )
    if name_match:
        values["taxpayer_name"] = (text(name_match.group(0)), text(name_match.group(0)))

    addr_match = re.search(
        r"(\d+\s+[A-Z0-9][A-Z0-9' /\-]*(?:AVE|AVENUE|ST|STREET|RD|ROAD|DR|DRIVE|CT|COURT|PL|PLACE|CRES|CRESCENT|HWY|PDE|PARADE|WAY|TCE|TERRACE)\.?)"
        r"[\s,]+([A-Z][A-Za-z' \-]+)\s+(NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s+(\d{4})",
        content,
        re.I,
    )
    if addr_match:
        address = text(
            f"{addr_match.group(1)}, {addr_match.group(2)} {addr_match.group(3).upper()} {addr_match.group(4)}"
        )
        values["taxpayer_address"] = (address, address)

    tfn_match = re.search(r"(?:Tax\s*File\s*Number|TFN)\s*[:.]?\s*([\d ]{8,15})", content, re.I)
    if tfn_match:
        values["tfn"] = (text(tfn_match.group(1)), digits(tfn_match.group(1)))

    ref_match = re.search(r"(?:Our\s*Reference|Reference)\s*[:.]?\s*([\d ]{8,20})", content, re.I)
    if ref_match:
        values["ato_reference"] = (text(ref_match.group(1)), digits(ref_match.group(1)))

    year_ended_match = re.search(r"year\s+ended\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})", content, re.I)
    if year_ended_match:
        raw_ye = text(year_ended_match.group(1))
        values["year_ended"] = (raw_ye, australian_date(raw_ye))

    income_raw, income_norm = _derive_income_year(
        values["year_ended"][0], content
    )
    if income_norm:
        values["income_year"] = (income_raw, income_norm)

    issue_match = re.search(rf"(?:Date\s*of\s*Issue|Issue\s*Date)\s*[:.]?\s*({_DATE_LONG})", content, re.I)
    if not issue_match:
        # Common placement: bare date near TFN block, e.g. "3 October 2022"
        issue_match = re.search(rf"\b({_DATE_LONG})\b", content)
        # Prefer October/Aug style near top half only if labeled elsewhere fails
        if issue_match and year_ended_match and text(issue_match.group(1)) == text(year_ended_match.group(1)):
            issue_match = None
    # More precise: look for month names after "Date of issue" variants in raw lines
    if not issue_match:
        m = re.search(r"Date\s+of\s+issue\s*[:.]?\s*(" + _DATE_LONG + ")", raw_content, re.I)
        if m:
            issue_match = m
    if issue_match:
        raw_issue = text(issue_match.group(1))
        values["date_of_issue"] = (raw_issue, australian_date(raw_issue))

    # --- Taxable income (often embedded in description, not a money column) ---
    ti = re.search(r"Your\s+taxable\s+income\s+is\s*[:.]?\s*\$?\s*([\d,]+(?:\.\d{2})?)", content, re.I)
    if ti:
        values["taxable_income"] = (text(ti.group(1)), money(ti.group(1)))

    # --- Table / labelled money rows ---
    row_specs = [
        ("tax_on_taxable_income", (r"Tax\s+on\s+your\s+taxable\s+income", r"Tax\s+on\s+taxable\s+income")),
        ("low_income_tax_offset", (r"Low\s+income\s+tax\s+offset",)),
        ("non_refundable_tax_offsets", (r"Total\s+non[- ]?refundable\s+tax\s+offsets", r"non[- ]?refundable\s+tax\s+offsets")),
        ("assessed_tax_payable", (r"Assessed\s+tax\s+payable",)),
        ("medicare_levy", (r"Medicare\s+levy",)),
        ("other_liabilities", (r"Total\s+other\s+liabilities", r"Other\s+liabilities")),
        ("tax_offset_refunds", (r"Less\s+tax\s+offset\s+refunds", r"Tax\s+offset\s+refunds")),
        ("payg_withholding_credits", (r"PAYG\s+withholding",)),
        ("payg_credits_and_entitlements", (r"Total\s+PAYG\s+and\s+other\s+entitlements", r"PAYG\s+and\s+other\s+entitlements")),
        ("result_of_notice_amount", (r"Result\s+of\s+this\s+notice",)),
    ]
    directions = {}
    for key, patterns in row_specs:
        raw, amount, direction = _row_money(matrices, patterns)
        if amount is None:
            raw2, amount2 = _money_near(content, patterns)
            raw, amount = raw2, amount2
            # Direction from nearby CR/DR
            if raw:
                dm = re.search(rf"{re.escape(raw)}\s*({_DIR})\b", content, re.I)
                if not dm:
                    dm = re.search(rf"(?:{'|'.join(patterns)}).*?({_DIR})\b", content, re.I)
                direction = dm.group(1).upper() if dm else direction
        if amount is not None:
            values[key] = (raw, amount)
            if direction:
                directions[key] = direction

    if "result_of_notice_amount" in directions:
        values["result_of_notice_direction"] = (
            directions["result_of_notice_amount"],
            directions["result_of_notice_amount"],
        )
    else:
        m = re.search(r"Result\s+of\s+this\s+notice.*?(\d[\d,]*\.\d{2})\s*(CR|DR)", content, re.I)
        if m:
            values["result_of_notice_amount"] = (text(m.group(1)), money(m.group(1)))
            values["result_of_notice_direction"] = (m.group(2).upper(), m.group(2).upper())

    # Outcome box
    outcome = re.search(
        r"Outcome\s+of\s+this\s+notice\s*[:.]?\s*\$?\s*([\d,]+(?:\.\d{2})?)\s*(CR|DR)?",
        content,
        re.I,
    )
    if outcome:
        values["outcome_amount"] = (text(outcome.group(1)), money(outcome.group(1)))
        if outcome.group(2):
            values["outcome_direction"] = (outcome.group(2).upper(), outcome.group(2).upper())
    elif values["result_of_notice_amount"][1] is not None:
        # Often identical to result of notice
        values["outcome_amount"] = values["result_of_notice_amount"]
        values["outcome_direction"] = values["result_of_notice_direction"]

    # Refund amount: prefer "... 1,051.43 CR has been forwarded..."
    refund = re.search(
        rf"({_MONEY})\s*(CR|DR)\s+has\s+been\s+forwarded",
        content,
        re.I,
    )
    if refund:
        values["refund_amount"] = (text(refund.group(1)), money(refund.group(1)))
    elif values["outcome_amount"][1] is not None and values.get("outcome_direction", (None, None))[1] == "CR":
        values["refund_amount"] = values["outcome_amount"]
    elif values["result_of_notice_amount"][1] is not None and values.get("result_of_notice_direction", (None, None))[1] == "CR":
        values["refund_amount"] = values["result_of_notice_amount"]

    status_match = re.search(
        r"((?:has\s+been\s+)?forwarded\s+to\s+(?:your\s+)?nominated\s+financial\s+institution)",
        content,
        re.I,
    )
    if status_match:
        values["refund_status"] = (text(status_match.group(1)), text(status_match.group(1)))
    else:
        m = re.search(r"([^.]*nominated\s+financial\s+institution)", content, re.I)
        if m:
            values["refund_status"] = (text(m.group(1)), text(m.group(1)))

    ref_tx = re.search(r"(?:Transaction\s*Reference\s*(?:Number)?|Reference\s*Number)\s*[:.]?\s*(ATO[\d]+|\w[\w\d-]{8,})", content, re.I)
    if not ref_tx:
        ref_tx = re.search(r"\b(ATO\d{10,})\b", content, re.I)
    if ref_tx:
        values["refund_reference"] = (text(ref_tx.group(1)), text(ref_tx.group(1)))

    # assessed tax payable direction text like "18,742.15 DR"
    assessed = re.search(r"Assessed\s+tax\s+payable\s*\$?\s*([\d,]+(?:\.\d{2})?)\s*(DR|CR)?", content, re.I)
    if assessed and values["assessed_tax_payable"][1] is None:
        values["assessed_tax_payable"] = (text(assessed.group(1)), money(assessed.group(1)))

    fields = []
    for key in REQUIRED_KEYS:
        raw, normalised = values[key]
        fields.append(_field(key, raw, normalised))
    return fields
