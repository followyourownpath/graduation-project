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


def australian_date(value):
    try:
        return datetime.strptime(text(value), "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def digits(value):
    result = re.sub(r"\D", "", text(value))
    return result or None
