from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from difflib import SequenceMatcher

from app.rules.models import NormalizedAddress

_NAME_TITLES = frozenset({"MR", "MRS", "MS", "MISS", "DR"})
_ENTITY_SUFFIXES = (
    "PTY LTD",
    "PTY. LTD.",
    "PTY LIMITED",
    "LIMITED",
    "LTD",
    "PTY",
)
_STREET_TYPES = {
    "ST": "STREET",
    "STREET": "STREET",
    "RD": "ROAD",
    "ROAD": "ROAD",
    "AVE": "AVENUE",
    "AVENUE": "AVENUE",
    "DR": "DRIVE",
    "DRIVE": "DRIVE",
    "CRES": "CRESCENT",
    "CRESCENT": "CRESCENT",
    "HWY": "HIGHWAY",
    "HIGHWAY": "HIGHWAY",
}
_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d/%m/%y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%d %b %Y",
    "%d %B %Y",
)


def _nfkc_upper(value: str | None) -> str | None:
    if value is None:
        return None
    text = unicodedata.normalize("NFKC", str(value)).strip()
    if not text:
        return None
    return text.upper()


def _collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _replace_punctuation_with_space(value: str) -> str:
    return re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)


def normalize_name(value: str | None) -> str | None:
    text = _nfkc_upper(value)
    if text is None:
        return None
    text = text.replace("-", " ")
    text = _replace_punctuation_with_space(text)
    text = _collapse_spaces(text)
    tokens = [token for token in text.split(" ") if token and token not in _NAME_TITLES]
    return " ".join(tokens) or None


def normalize_entity(value: str | None) -> str | None:
    text = _nfkc_upper(value)
    if text is None:
        return None
    text = text.replace("&", " AND ")
    text = _replace_punctuation_with_space(text)
    text = _collapse_spaces(text)
    stripped = text
    changed = True
    while changed:
        changed = False
        for suffix in _ENTITY_SUFFIXES:
            suffix_norm = _collapse_spaces(_replace_punctuation_with_space(suffix))
            if stripped == suffix_norm:
                stripped = ""
                changed = True
                break
            if stripped.endswith(" " + suffix_norm):
                stripped = stripped[: -(len(suffix_norm) + 1)].rstrip()
                changed = True
                break
    return stripped or None


def normalize_address(value: str | None) -> NormalizedAddress | None:
    original = None if value is None else str(value).strip()
    text = _nfkc_upper(value)
    if text is None:
        return None
    text = _replace_punctuation_with_space(text)
    text = _collapse_spaces(text)
    tokens = text.split(" ")
    normalised_tokens = [_STREET_TYPES.get(token, token) for token in tokens]
    normalised_text = _collapse_spaces(" ".join(normalised_tokens))
    street_number = None
    for token in normalised_tokens:
        if re.fullmatch(r"\d+[A-Z]?", token):
            street_number = token
            break
    postcode = None
    for token in reversed(normalised_tokens):
        if re.fullmatch(r"\d{4}", token):
            postcode = token
            break
    return NormalizedAddress(
        normalised_text=normalised_text,
        street_number=street_number,
        postcode=postcode,
        display_text=original or normalised_text,
    )


def normalize_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    text = unicodedata.normalize("NFKC", str(value)).strip()
    if not text:
        return None
    cleaned = re.sub(r"[\s\-]", "", text)
    return cleaned or None


def parse_iso_date(value: str | None) -> date | None:
    if value is None:
        return None
    raw = unicodedata.normalize("NFKC", str(value)).strip()
    if not raw:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def parse_money(value: str | None) -> Decimal | None:
    if value is None:
        return None
    raw = unicodedata.normalize("NFKC", str(value)).strip()
    if not raw:
        return None
    negative = raw.startswith("(") and raw.endswith(")")
    cleaned = re.sub(r"[^0-9.\-]", "", raw)
    if not cleaned or cleaned in {".", "-", "-."}:
        return None
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        return None
    if negative:
        amount = -abs(amount)
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def similarity(left: str | None, right: str | None) -> Decimal:
    if left is None or right is None:
        return Decimal("0.00")
    ratio = SequenceMatcher(None, left, right).ratio()
    return Decimal(str(ratio)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_money(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")


def relative_difference(left: Decimal, right: Decimal) -> Decimal | None:
    if left == 0:
        return Decimal("0.00") if right == 0 else None
    return (abs(right - left) / abs(left)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
