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


def parse_full_address(addr_str: str) -> dict:
    if not addr_str or not isinstance(addr_str, str):
        return {}
    addr_str = addr_str.strip()
    
    # Try parsing postcode (4 digits at the end)
    postcode_match = re.search(r'\b(\d{4})$', addr_str)
    postcode = postcode_match.group(1) if postcode_match else None
    
    # Strip postcode from end
    if postcode_match:
        addr_str = addr_str[:postcode_match.start()].strip()
        
    # Try parsing state (ACT|NSW|NT|QLD|SA|TAS|VIC|WA) at the end
    state_match = re.search(r'\b(ACT|NSW|NT|QLD|SA|TAS|VIC|WA|OTHER)\b$', addr_str, re.IGNORECASE)
    state = state_match.group(1).upper() if state_match else None
    
    # Strip state from end
    if state_match:
        addr_str = addr_str[:state_match.start()].strip()
        
    # Strip trailing commas
    addr_str = addr_str.rstrip(",").strip()

    # Try splitting remaining by comma to separate street part from suburb part
    street_part = ""
    city = ""
    if "," in addr_str:
        parts = addr_str.rsplit(",", 1)
        street_part = parts[0].strip()
        city = parts[1].strip()
    else:
        parts = addr_str.rsplit(" ", 1)
        if len(parts) > 1:
            street_part = parts[0].strip()
            city = parts[1].strip()
        else:
            street_part = addr_str
            city = ""
            
    # Parse street_part into street_number, street_name, street_type
    street_number = None
    street_name = None
    street_type = None
    
    if street_part:
        street_parts = street_part.split(" ", 1)
        street_number = street_parts[0] if street_parts else None
        if len(street_parts) > 1:
            street_name_full = street_parts[1]
            type_match = re.search(
                r'\b(Street|St|Road|Rd|Way|Lane|Ln|Drive|Dr|Avenue|Ave|Court|Ct|Place|Pl|Parade|Pde|Crescent|Cres|Close|Cl|Grange|Gra|Terrace|Tce|Boulevard|Bvd|Highway|Hwy)\b$',
                street_name_full, re.IGNORECASE
            )
            if type_match:
                street_type = type_match.group(1).title()
                street_name = street_name_full[:type_match.start()].strip()
            else:
                street_name = street_name_full
                
    return {
        "street_number": street_number,
        "street_name": street_name,
        "street_type": street_type,
        "city": city,
        "state": state,
        "postcode": postcode,
    }
