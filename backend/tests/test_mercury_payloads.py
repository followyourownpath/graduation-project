import pytest
from app.integrations.mercury.payloads import (
    split_full_name,
    format_phone,
    format_number,
    format_iso_timestamp,
    build_contact_payload,
    build_opportunity_payload,
    build_address_payload,
    build_asset_payload,
    build_liability_payload,
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
    assert split_full_name("\u5f20\u4e09") == (None, "\u4e09", None, "\u5f20")
    assert split_full_name("\u674e\u56db") == (None, "\u56db", None, "\u674e")
    
    # Three character names
    assert split_full_name("\u674e\u5609\u7426") == (None, "\u5609\u7426", None, "\u674e")
    assert split_full_name("\u738b\u5c0f\u660e") == (None, "\u5c0f\u660e", None, "\u738b")
    
    # Four character names with double family prefixes
    assert split_full_name("\u53f8\u9a6c\u76f8\u5982") == (None, "\u76f8\u5982", None, "\u53f8\u9a6c")
    assert split_full_name("\u8bf8\u845b\u5b54\u660e") == (None, "\u5b54\u660e", None, "\u8bf8\u845b")
    assert split_full_name("\u6b27\u9633\u516d\u4e03") == (None, "\u516d\u4e03", None, "\u6b27\u9633")
    
    # Four character names with single family name fallback
    # Four code points without a known compound surname use a two-and-two split.
    assert split_full_name("\u8d75\u94b1\u5b59\u674e") == (None, "\u5b59\u674e", None, "\u8d75\u94b1")


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


def test_build_asset_payload():
    asset = {
        "name": "150 Todman Ave, Kensington NSW 2033",
        "type": "realEstate",
        "value": "1150000",
        "account_name": "Junhong Zhong",
        "address": {
            "street_number": "150",
            "street_name": "Todman",
            "street_type": "Ave",
            "city": "KENSINGTON",
            "state": "NSW",
            "postcode": "2033"
        }
    }
    payload = build_asset_payload(asset)
    assert payload["name"] == "Real Estate"
    assert payload["type"] == "realEstate"
    assert payload["value"] == 1150000.0
    assert payload["details"] == "150 Todman Ave, Kensington NSW 2033"
    assert payload["accountName"] == "Junhong Zhong"
    assert payload["address"]["streetNumber"] == "150"
    assert payload["address"]["city"] == "KENSINGTON"


def test_build_liability_payload():
    liab = {
        "name": "Credit Card",
        "type": "account",
        "value": "4120",
        "limit": "10000",
        "institution": "ANZ",
        "account_repayment": "280",
        "account_repayment_frequency": "monthly",
        "details": "150 Todman Ave, Kensington NSW 2033",
        "account_name": "Junhong Zhong"
    }
    payload = build_liability_payload(liab)
    assert payload["name"] == "Credit Card"
    assert payload["type"] == "account"
    assert payload["value"] == 4120.0
    assert payload["limit"] == 10000.0
    assert payload["institution"] == "ANZ"
    assert payload["details"] == "150 Todman Ave, Kensington NSW 2033"
    assert payload["accountName"] == "Junhong Zhong"
