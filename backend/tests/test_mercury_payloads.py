import pytest
from app.integrations.mercury.payloads import (
    split_full_name,
    format_phone,
    format_number,
    format_iso_timestamp,
    build_contact_payload,
    build_opportunity_payload,
    build_address_payload,
)


def test_split_full_name_western():
    # Standard names
    assert split_full_name("Mr John Citizen") == ("Mr", "John", None, "Citizen")
    assert split_full_name("Dr. Jane Mary Doe") == ("Dr", "Jane", "Mary", "Doe")
    assert split_full_name("prof. Robert Smith") == ("Prof", "Robert", None, "Smith")
    
    # Single token
    assert split_full_name("Cher") == (None, "Cher", None, "Cher")
    
    # Compound last names
    assert split_full_name("David Van Der Berg") == (None, "David", None, "Van Der Berg")
    assert split_full_name("Martin De Silva") == (None, "Martin", None, "De Silva")
    assert split_full_name("Ms laura le grand") == ("Ms", "laura", None, "le grand")
    
    # Many tokens
    assert split_full_name("John James Robert Citizen") == (None, "John", "James Robert", "Citizen")


def test_split_full_name_chinese():
    # Two character names
    assert split_full_name("张三") == (None, "三", None, "张")
    assert split_full_name("李四") == (None, "四", None, "李")
    
    # Three character names
    assert split_full_name("李嘉琦") == (None, "嘉琦", None, "李")
    assert split_full_name("王小明") == (None, "小明", None, "王")
    
    # Four character names with double family prefixes
    assert split_full_name("司马相如") == (None, "相如", None, "司马")
    assert split_full_name("诸葛孔明") == (None, "孔明", None, "诸葛")
    assert split_full_name("欧阳六七") == (None, "六七", None, "欧阳")
    
    # Four character names with single family name fallback
    # "赵钱孙李" -> Zhaoqian (趙錢) / Sunli (孫李)? Defaults to Zhaoqian (赵钱) as Family name, Sunli (孙李) as Given name
    assert split_full_name("赵钱孙李") == (None, "孙李", None, "赵钱")


def test_format_phone():
    assert format_phone("0400 111 222") == "0400111222"
    assert format_phone("+61 400 111 222") == "0400111222"
    assert format_phone("61400111222") == "0400111222"
    assert format_phone("not-a-phone") is None


def test_format_number():
    assert format_number(123) == 123.0
    assert format_number("12,345.67") == 12345.67
    assert format_number("$150,000") == 150000.0
    assert format_number("-45.5") == -45.5
    assert format_number("") is None


def test_format_iso_timestamp():
    assert format_iso_timestamp("1990-04-22") == "1990-04-22T00:00:00.000Z"
    assert format_iso_timestamp("2000-04-22T10:00:00+00:00") == "2000-04-22T10:00:00.000Z"
    assert format_iso_timestamp("") is None


def test_build_contact_payload():
    # Given a pre-split applicant
    applicant = {
        "title": "Mr",
        "first_name": "John",
        "middle_name": "James",
        "last_name": "Citizen",
        "date_of_birth": "1990-04-22",
        "mobile": "0400111222",
        "email": "john@example.test"
    }
    payload = build_contact_payload(applicant)
    assert payload["firstName"] == "John"
    assert payload["lastName"] == "Citizen"
    assert payload["middleName"] == "James"
    assert payload["title"] == "Mr"
    assert payload["dateOfBirth"] == "1990-04-22T00:00:00.000Z"
    assert len(payload["contactMethods"]) == 2
    assert payload["contactMethods"][0] == {"contactMethod": "Mobile", "content": "0400111222"}

    # Given an applicant with only full_name
    applicant_full = {
        "full_name": "David Van Der Berg",
        "email": "david@example.test"
    }
    payload_full = build_contact_payload(applicant_full)
    assert payload_full["firstName"] == "David"
    assert payload_full["lastName"] == "Van Der Berg"
    assert payload_full["middleName"] is None
    assert payload_full["title"] is None


def test_build_opportunity_payload():
    opp_data = {
        "opportunity_name": "John Citizen Purchase",
        "amount": "$450,000",
        "status": "Lead",
        "transaction_type": "Loan",
        "transaction_subtype": "Purchase",
        "loan_term_years": "30",
        "lmi": "0"
    }
    payload = build_opportunity_payload(opp_data, default_test_prefix="SMARTFINN-TEST-")
    assert payload["opportunityName"] == "SMARTFINN-TEST-John Citizen Purchase"
    assert payload["amount"] == 450000.0
    assert payload["loanTerm"] == 30
    assert payload["tranxType"] == "Purchase"


def test_build_address_payload():
    addr = {
        "street_number": "555",
        "street_name": "Collins",
        "street_type": "Street",
        "city": "Melbourne",
        "state": "Vic",
        "postcode": "3000"
    }
    payload = build_address_payload(addr)
    assert payload["streetNumber"] == "555"
    assert payload["streetName"] == "Collins"
    assert payload["streetType"] == "Street"
    assert payload["city"] == "MELBOURNE"
    assert payload["state"] == "VIC"
    assert payload["postcode"] == "3000"
    assert payload["addressBlock"] == "555 Collins Street\nMELBOURNE VIC 3000"
