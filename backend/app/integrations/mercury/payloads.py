import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import logging

log = logging.getLogger("mercury_payloads")

TITLE_REGEX = re.compile(r"^\s*(mr|mrs|ms|miss|dr|prof|rev)\.?\s+", re.IGNORECASE)

COMPOUND_PREFIXES = {
    "van", "der", "de", "di", "la", "le", "von", "mc", "mac", "st", "saint"
}

# Standard title map for Mercury Title Enum
MERCURY_TITLE_MAP = {
    "Mr": "Mr",
    "Mrs": "Mrs",
    "Ms": "Ms",
    "Miss": "Miss",
    "Dr": "Dr",
    "Prof": "Prof",
    "Rev": "Rev"
}


def split_full_name(
    full_name: str,
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Splits a full name string into (title, first_name, middle_name, last_name).

    Handles English and Chinese characters name splitting rules.
    """
    if not full_name:
        return None, None, None, None

    full_name = full_name.strip()

    # 1. Title Stripping
    title = None
    match = TITLE_REGEX.match(full_name)
    if match:
        title = match.group(1).title()
        full_name = full_name[match.end():].strip()

    # Standardize Title to Mercury Enum
    if title:
        title = MERCURY_TITLE_MAP.get(title, title)

    # 2. Check for Chinese characters
    if re.search(r"[\u4e00-\u9fa5]", full_name):
        chinese_name = re.sub(r"\s+", "", full_name)
        n = len(chinese_name)
        if n == 0:
            return title, None, None, None
        elif n == 1:
            return title, chinese_name, None, None
        elif n == 2:
            return title, chinese_name[1:], None, chinese_name[0]  # e.g., 张三
        elif n == 3:
            return title, chinese_name[1:], None, chinese_name[0]  # e.g., 李嘉琦
        elif n == 4:
            double_family_prefixes = {
                "司马", "欧阳", "诸葛", "东方", "皇甫", "独孤", "南宫", "公孙"
            }
            prefix = chinese_name[:2]
            if prefix in double_family_prefixes:
                return title, chinese_name[2:], None, prefix  # e.g., 司马相如
            else:
                return title, chinese_name[2:], None, chinese_name[:2]
        else:
            return title, chinese_name[2:], None, chinese_name[:2]

    # 3. Western name tokenization
    tokens = [t for t in re.split(r"\s+", full_name) if t]
    if not tokens:
        return title, None, None, None

    # Single token (Cher)
    if len(tokens) == 1:
        return title, tokens[0], None, tokens[0]

    # Check for compound last names backwards
    split_idx = len(tokens) - 1
    for i in range(len(tokens) - 2, -1, -1):
        if tokens[i].lower() in COMPOUND_PREFIXES:
            split_idx = i
        else:
            break

    if split_idx < len(tokens) - 1:
        first_tokens = tokens[:split_idx]
        last_tokens = tokens[split_idx:]
        last_name = " ".join(last_tokens)

        if len(first_tokens) == 0:
            return title, last_name, None, last_name
        elif len(first_tokens) == 1:
            return title, first_tokens[0], None, last_name
        else:
            first_name = first_tokens[0]
            middle_name = " ".join(first_tokens[1:])
            return title, first_name, middle_name, last_name

    # 2 tokens: John Citizen
    if len(tokens) == 2:
        return title, tokens[0], None, tokens[1]

    # 3 tokens: John James Citizen
    if len(tokens) == 3:
        return title, tokens[0], tokens[1], tokens[2]

    # > 3 tokens: John James Robert Citizen
    return title, tokens[0], " ".join(tokens[1:-1]), tokens[-1]


def format_iso_timestamp(date_val: Any) -> Optional[str]:
    """Formats date to YYYY-MM-DDTHH:MM:SS.000Z."""
    if not date_val:
        return None
    try:
        if isinstance(date_val, str):
            date_val = re.sub(r"\+00:00$", "Z", date_val.strip())
            if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", date_val):
                return f"{date_val[:19]}.000Z"
            dt = datetime.strptime(date_val[:10], "%Y-%m-%d")
            return dt.strftime("%Y-%m-%dT00:00:00.000Z")
        elif hasattr(date_val, "strftime"):
            return date_val.strftime("%Y-%m-%dT00:00:00.000Z")
    except Exception as e:
        log.warning(f"Could not parse ISO timestamp from {date_val}: {e}")
    return None


def format_date_only(date_val: Any) -> Optional[str]:
    """Formats date to YYYY-MM-DD."""
    if not date_val:
        return None
    try:
        if isinstance(date_val, str):
            return date_val.strip()[:10]
        elif hasattr(date_val, "strftime"):
            return date_val.strftime("%Y-%m-%d")
    except Exception as e:
        log.warning(f"Could not parse date only from {date_val}: {e}")
    return None


def format_number(val: Any) -> Optional[float]:
    """Extracts numeric float from strings or numbers."""
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        cleaned = re.sub(r"[^\d\.\-]", "", str(val))
        return float(cleaned)
    except Exception as e:
        log.warning(f"Could not parse float from {val}: {e}")
        return None


def format_phone(val: Any) -> Optional[str]:
    """Formats phone to Australian format e.g. 0400111222."""
    if not val:
        return None
    cleaned = re.sub(r"\D", "", str(val))
    if not cleaned:
        return None
    if cleaned.startswith("61") and len(cleaned) > 2:
        cleaned = "0" + cleaned[2:]
    return cleaned


# --- Contact Payload Builder ---
def build_contact_payload(applicant: Dict[str, Any]) -> Dict[str, Any]:
    """Constructs a Mercury Contact/Person payload from approved applicant snapshot."""
    first_name = applicant.get("first_name")
    middle_name = applicant.get("middle_name")
    last_name = applicant.get("last_name")
    title = applicant.get("title")

    # If first name is missing but full_name is present, parse it
    if not first_name and applicant.get("full_name"):
        title, first_name, middle_name, last_name = split_full_name(applicant["full_name"])

    # Fallbacks to prevent empty name fields which Mercury rejects
    first_name = first_name or "Applicant"
    last_name = last_name or "Citizen"

    dob = format_iso_timestamp(applicant.get("date_of_birth"))

    contact_methods = []
    mobile = format_phone(applicant.get("mobile"))
    if mobile:
        contact_methods.append({"contactMethod": "Mobile", "content": mobile})

    email = applicant.get("email")
    if email:
        contact_methods.append({"contactMethod": "Email 1", "content": email.strip()})

    payload = {
        "isDeleted": False,
        "firstName": first_name,
        "lastName": last_name,
        "middleName": middle_name,
        "title": title,
        "dateOfBirth": dob,
        "contactMethods": contact_methods,
    }

    # If updating, person ID may be stored
    if applicant.get("mercury_person_id"):
        payload["uniqueId"] = applicant["mercury_person_id"]

    return payload


# --- Opportunity Payload Builder ---
def build_opportunity_payload(
    opp_data: Dict[str, Any], default_test_prefix: str = "SMARTFINN-TEST-"
) -> Dict[str, Any]:
    """Constructs a Mercury Opportunity payload from approved snapshot."""
    name = opp_data.get("opportunity_name", "Application")
    # Force test prefix in safety constraints
    if default_test_prefix and not name.startswith(default_test_prefix):
        name = f"{default_test_prefix}{name}"

    amount = format_number(opp_data.get("amount")) or 0.0

    payload = {
        "isDeleted": False,
        "opportunityName": name,
        "amount": amount,
        "status": opp_data.get("status") or "Lead",
        "transactionType": opp_data.get("transaction_type") or "Loan",
        "tranxType": opp_data.get("transaction_subtype") or "Purchase",
        "notePadText": opp_data.get("objectives") or "Created by SmartFINN AI platform",
    }

    # Handle optional standard properties
    if opp_data.get("loan_term_years"):
        payload["loanTerm"] = int(format_number(opp_data["loan_term_years"]) or 30)
    if opp_data.get("lmi"):
        payload["lmi"] = format_number(opp_data["lmi"])

    if opp_data.get("mercury_opportunity_id"):
        payload["uniqueId"] = opp_data["mercury_opportunity_id"]

    return payload


# --- Related Party Payload Builder ---
def build_related_party_payload(person_id: str, relationship: str) -> Dict[str, Any]:
    """Constructs Related Party payload."""
    return {"personID": person_id, "relationship": relationship}


# --- Address Payload Builder ---
def build_address_payload(addr: Dict[str, Any]) -> Dict[str, Any]:
    """Constructs Address payload from approved address snapshot."""
    postcode = str(addr.get("postcode") or "").strip()
    street_number = str(addr.get("street_number") or "").strip()
    street_name = str(addr.get("street_name") or "").strip()
    street_type = str(addr.get("street_type") or "").strip()
    city = str(addr.get("city") or "").strip().upper()
    state = str(addr.get("state") or "").strip().upper()

    address_block_lines = []
    if street_number or street_name:
        address_block_lines.append(
            f"{street_number} {street_name} {street_type}".strip()
        )
    if city or state or postcode:
        address_block_lines.append(f"{city} {state} {postcode}".strip())

    address_block = "\n".join(address_block_lines)

    payload = {
        "isDeleted": False,
        "streetNumber": street_number or None,
        "streetName": street_name or None,
        "streetType": street_type or None,
        "city": city or None,
        "state": state or None,
        "postcode": postcode or None,
        "country": addr.get("country") or "Australia",
        "type": addr.get("type") or "Home",
        "addressBlock": address_block or None,
    }

    if addr.get("mercury_address_id"):
        payload["uniqueId"] = addr["mercury_address_id"]

    return payload


# --- Employment Payload Builder ---
def build_employment_payload(emp: Dict[str, Any], person_id: str) -> Dict[str, Any]:
    """Constructs Employment payload."""
    payload = {
        "isDeleted": False,
        "personId": person_id,
        "employerName": emp.get("employer_name"),
        "jobTitle": emp.get("job_title"),
        "employmentBasis": emp.get("employment_basis") or "Full Time Permanent",
        "employmentStatus": emp.get("employment_status") or "Primary",
        "employmentType": emp.get("employment_type") or "PAYG",
        "startDate": format_date_only(emp.get("start_date")),
        "endDate": format_date_only(emp.get("end_date")),
    }

    if emp.get("mercury_employment_id"):
        payload["uniqueId"] = emp["mercury_employment_id"]

    return payload


# --- Income Payload Builder ---
def build_income_payload(inc: Dict[str, Any], person_id: str) -> Dict[str, Any]:
    """Constructs Income payload."""
    payload = {
        "isDeleted": False,
        "personID": person_id,
        "amount": format_number(inc.get("amount")) or 0.0,
        "type": inc.get("type") or "Salary",
        "frequency": inc.get("frequency") or "Annual",
        "dateCommenced": format_date_only(inc.get("date_commenced")),
        "comment": inc.get("comment"),
    }

    if inc.get("mercury_income_id"):
        payload["uniqueId"] = inc["mercury_income_id"]

    return payload


# --- Asset Payload Builder ---
def build_asset_payload(asset: Dict[str, Any]) -> Dict[str, Any]:
    """Constructs Asset payload."""
    payload = {
        "isDeleted": False,
        "name": asset.get("name") or "Asset",
        "type": asset.get("type") or "other",
        "value": format_number(asset.get("value")) or 0.0,
    }

    if asset.get("mercury_asset_id"):
        payload["uniqueId"] = asset["mercury_asset_id"]

    return payload


# --- Liability Payload Builder ---
def build_liability_payload(liab: Dict[str, Any]) -> Dict[str, Any]:
    """Constructs Liability payload."""
    payload = {
        "isDeleted": False,
        "name": liab.get("name") or "Liability",
        "type": liab.get("type") or "other",
        "value": format_number(liab.get("value")) or 0.0,
        "limit": format_number(liab.get("limit")),
        "institution": liab.get("institution"),
        "accountRepayment": format_number(liab.get("account_repayment")),
        "accountRepaymentFrequency": liab.get("account_repayment_frequency")
        or "monthly",
    }

    if liab.get("mercury_liability_id"):
        payload["uniqueId"] = liab["mercury_liability_id"]

    return payload
