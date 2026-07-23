import re
from datetime import datetime
from decimal import Decimal, InvalidOperation


def text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def money(value):
    raw = text(value)
    negative_parentheses = raw.startswith("(") and raw.endswith(")")
    cleaned = re.sub(r"[^0-9.\-]", "", raw)
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        return None
    if negative_parentheses:
        amount = -abs(amount)
    return format(amount.quantize(Decimal("0.01")), "f")


# Day-first (Australian) styles take priority; year-first and written-month
# styles are unambiguous additions for free-text form input.
DATE_FORMATS = (
    "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d.%m.%Y",
    "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
    "%d %b %Y", "%d %B %Y", "%b %Y", "%B %Y",
    "%m/%Y", "%m/%y",
)


def australian_date(value):
    raw = text(value)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def digits(value):
    result = re.sub(r"\D", "", text(value))
    return result or None


def phone(value):
    """Normalise Australian numbers to E.164 (+61...), matching the client
    data-model example: '0412 345 678' -> '+61412345678'.
    """
    raw = text(value)
    if not raw:
        return None
    digits_only = re.sub(r"\D", "", raw)
    if not digits_only:
        return None
    if digits_only.startswith("61") and len(digits_only) >= 11:
        return f"+{digits_only}"
    if digits_only.startswith("0") and len(digits_only) >= 9:
        return f"+61{digits_only[1:]}"
    if raw.startswith("+"):
        return f"+{digits_only}"
    return digits_only


def email(value):
    raw = text(value).lower()
    return raw if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", raw) else None
