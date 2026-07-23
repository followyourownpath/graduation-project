"""Fact Find (AcroForm) direct-read extraction.

The SmartFINN Customer Fact Find is a fillable PDF form. When completed
electronically, every value is stored as structured AcroForm widget data
inside the PDF, so fields can be read directly with PyMuPDF - no OCR needed.

Widget-name to field_key mapping lives in fact_find_mapping.json and follows
the "Smartfinn Fact Find Field Mapping Matrix v1" document. Scanned or
flattened copies have no widgets; callers should fall back to the OCR route.
"""

import json
from pathlib import Path

import fitz

from app.normalization.values import australian_date, digits, money, phone, text

_MAPPING_PATH = Path(__file__).with_name("fact_find_mapping.json")

with _MAPPING_PATH.open() as _fh:
    _MAPPING = json.load(_fh)["fields"]

# Radio buttons default to "Off", combo boxes to "--"; neither is user input.
_EMPTY_VALUES = {"", "--", "Off"}


def _email(value):
    raw = text(value).lower()
    return raw if "@" in raw and "." in raw.rsplit("@", 1)[-1] else None


_NORMALISERS = {
    "money": money,
    "date": australian_date,
    "integer": digits,
    "phone": phone,
    "email": _email,
}


def _normalise(spec, raw):
    if spec["enum_map"] is not None:
        return spec["enum_map"].get(text(raw))
    if spec["data_type"] == "boolean":
        return "true"
    normaliser = _NORMALISERS.get(spec["data_type"])
    return normaliser(raw) if normaliser else (text(raw) or None)


def _bounding_box(widget):
    """Axis-aligned widget rect as an 8-number polygon (Azure-compatible)."""
    rect = widget.rect
    return [
        round(rect.x0, 2), round(rect.y0, 2),
        round(rect.x1, 2), round(rect.y0, 2),
        round(rect.x1, 2), round(rect.y1, 2),
        round(rect.x0, 2), round(rect.y1, 2),
    ]


def extract_fact_find_acroform(pdf_bytes):
    """Read a fact-find PDF's AcroForm widgets.

    Returns a dict:
      has_form  - True when the PDF contains form widgets at all
      fields    - extracted_field-shaped dicts (plus a page_number key the
                  caller uses to link document_page rows, then removes)
      pages     - per-page metadata for document_page rows
    """
    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return {"has_form": False, "fields": [], "pages": []}

    has_form = False
    fields = []
    seen = set()
    pages = []
    for page in document:
        pages.append({
            "page_number": page.number + 1,
            "width": round(page.rect.width, 2),
            "height": round(page.rect.height, 2),
            "raw_text": page.get_text(),
        })
        for widget in page.widgets() or []:
            has_form = True
            spec = _MAPPING.get(widget.field_name)
            if spec is None or widget.field_name in seen:
                continue
            raw = widget.field_value
            if widget.field_type_string == "CheckBox":
                raw = "Yes" if raw and raw != "Off" else ""
            if text(raw) in _EMPTY_VALUES:
                continue
            seen.add(widget.field_name)
            fields.append({
                "section_name": spec["section_name"],
                "applicant_number": spec["applicant_number"] or 1,
                "field_key": spec["field_key"],
                "field_label": spec["field_label"],
                "raw_value": text(raw),
                "normalised_value": _normalise(spec, raw),
                "data_type": spec["data_type"],
                "confidence": 1.0,
                "bounding_box": _bounding_box(widget),
                "mapped_table": spec["mapped_table"],
                "mapped_column": spec["mapped_column"],
                "review_status": "pending",
                "page_number": page.number + 1,
            })
    return {"has_form": has_form, "fields": fields, "pages": pages}
