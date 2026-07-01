import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker('en_AU')  # Using Australian locale for names, etc.

# Suburbs list with valid postcodes & states for high realism
AU_SUBURBS = [
    # NSW
    {"suburb": "Sydney", "postcode": "2000", "state": "NSW"},
    {"suburb": "North Sydney", "postcode": "2060", "state": "NSW"},
    {"suburb": "Parramatta", "postcode": "2150", "state": "NSW"},
    {"suburb": "Chatswood", "postcode": "2067", "state": "NSW"},
    {"suburb": "Ryde", "postcode": "2112", "state": "NSW"},
    {"suburb": "Strathfield", "postcode": "2135", "state": "NSW"},
    {"suburb": "Hurstville", "postcode": "2220", "state": "NSW"},
    {"suburb": "Surry Hills", "postcode": "2010", "state": "NSW"},
    # VIC
    {"suburb": "Melbourne", "postcode": "3000", "state": "VIC"},
    {"suburb": "Richmond", "postcode": "3121", "state": "VIC"},
    {"suburb": "South Yarra", "postcode": "3141", "state": "VIC"},
    {"suburb": "St Kilda", "postcode": "3182", "state": "VIC"},
    {"suburb": "Carlton", "postcode": "3053", "state": "VIC"},
    {"suburb": "Fitzroy", "postcode": "3065", "state": "VIC"},
    {"suburb": "Hawthorn", "postcode": "3122", "state": "VIC"},
    # QLD
    {"suburb": "Brisbane", "postcode": "4000", "state": "QLD"},
    {"suburb": "Fortitude Valley", "postcode": "4006", "state": "QLD"},
    {"suburb": "South Brisbane", "postcode": "4101", "state": "QLD"},
    {"suburb": "Sunnybank", "postcode": "4109", "state": "QLD"},
    {"suburb": "Surfers Paradise", "postcode": "4217", "state": "QLD"},
    # WA
    {"suburb": "Perth", "postcode": "6000", "state": "WA"},
    {"suburb": "Fremantle", "postcode": "6160", "state": "WA"},
    {"suburb": "Subiaco", "postcode": "6008", "state": "WA"},
    {"suburb": "Joondalup", "postcode": "6027", "state": "WA"},
    # SA
    {"suburb": "Adelaide", "postcode": "5000", "state": "SA"},
    {"suburb": "Glenelg", "postcode": "5045", "state": "SA"},
    {"suburb": "Norwood", "postcode": "5067", "state": "SA"},
    # TAS
    {"suburb": "Hobart", "postcode": "7000", "state": "TAS"},
    {"suburb": "Sandy Bay", "postcode": "7005", "state": "TAS"},
    {"suburb": "Launceston", "postcode": "7250", "state": "TAS"}
]

# Occupation mapping with salary range (gross annual) and standard titles
OCCUPATIONS = [
    {"title": "Software Engineer", "min_sal": 85000, "max_sal": 145000},
    {"title": "Senior Project Manager", "min_sal": 120000, "max_sal": 180000},
    {"title": "Registered Nurse", "min_sal": 75000, "max_sal": 105000},
    {"title": "Accountant", "min_sal": 80000, "max_sal": 125000},
    {"title": "Sales Director", "min_sal": 140000, "max_sal": 230000},
    {"title": "HR Specialist", "min_sal": 70000, "max_sal": 105000},
    {"title": "Marketing Manager", "min_sal": 85000, "max_sal": 125000},
    {"title": "Data Analyst", "min_sal": 80000, "max_sal": 120000},
    {"title": "Operations Manager", "min_sal": 90000, "max_sal": 140000},
    {"title": "Financial Analyst", "min_sal": 85000, "max_sal": 130000}
]

def generate_valid_abn():
    """Generates a mathematically valid 11-digit Australian Business Number (ABN)"""
    while True:
        digits = [random.randint(0, 9) for _ in range(10)]
        weights = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
        s = sum(digits[i] * weights[i] for i in range(10))
        # We need ((d1 - 1) * 10 + s) % 89 == 0
        # Let's find d1 from 1 to 9
        for d1 in range(1, 10):
            if ((d1 - 1) * 10 + s) % 89 == 0:
                return f"{d1}" + "".join(map(str, digits))

def generate_valid_acn():
    """Generates a mathematically valid 9-digit Australian Company Number (ACN)"""
    digits = [random.randint(0, 9) for _ in range(8)]
    weights = [8, 7, 6, 5, 4, 3, 2, 1]
    s = sum(digits[i] * weights[i] for i in range(8))
    rem = s % 10
    check_digit = 0 if rem == 0 else 10 - rem
    return "".join(map(str, digits)) + str(check_digit)

def format_abn(abn_str):
    """Formats an ABN string to XX XXX XXX XXX format"""
    return f"{abn_str[0:2]} {abn_str[2:5]} {abn_str[5:8]} {abn_str[8:11]}"

def format_acn(acn_str):
    """Formats an ACN string to XXX XXX XXX format"""
    return f"{acn_str[0:3]} {acn_str[3:6]} {acn_str[6:9]}"

def generate_address():
    """Generates a random valid-looking Australian address"""
    sub_info = random.choice(AU_SUBURBS)
    street_num = random.randint(1, 450)
    street_name = fake.street_name()
    street_suffix = fake.street_suffix()
    
    # Randomly add unit numbers to some addresses (approx 30% of the time)
    if random.random() < 0.3:
        unit_num = random.randint(1, 80)
        address_line = f"Unit {unit_num}, {street_num} {street_name} {street_suffix}"
    else:
        address_line = f"{street_num} {street_name} {street_suffix}"
        
    return {
        "street": address_line,
        "suburb": sub_info["suburb"],
        "state": sub_info["state"],
        "postcode": sub_info["postcode"],
        "full_address": f"{address_line}, {sub_info['suburb']} {sub_info['state']} {sub_info['postcode']}"
    }

def generate_person():
    """Generates a single Person profile"""
    first_name = fake.first_name()
    last_name = fake.last_name()
    middle_name = fake.first_name() if random.random() < 0.5 else ""
    
    if middle_name:
        full_name = f"{first_name} {middle_name} {last_name}"
    else:
        full_name = f"{first_name} {last_name}"
        
    dob = fake.date_of_birth(minimum_age=21, maximum_age=65)
    email = f"{first_name.lower()}.{last_name.lower()}@example.com"
    phone = f"04{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100, 999)}"
    addr = generate_address()
    
    # ID Details
    passport_num = f"PA{random.randint(1000000, 9999999)}"
    passport_expiry = datetime.today() + timedelta(days=random.randint(365, 3650))
    driver_licence = f"{random.randint(10000000, 99999999)}"
    licence_expiry = datetime.today() + timedelta(days=random.randint(365, 1825))
    
    return {
        "first_name": first_name,
        "last_name": last_name,
        "middle_name": middle_name,
        "full_name": full_name,
        "dob": dob.strftime("%d/%m/%Y"),
        "email": email,
        "phone": phone,
        "address": addr,
        "passport_number": passport_num,
        "passport_expiry": passport_expiry.strftime("%d/%m/%Y"),
        "driver_licence": driver_licence,
        "licence_expiry": licence_expiry.strftime("%d/%m/%Y")
    }

def generate_company():
    """Generates a single Company profile"""
    company_suffix = random.choice(["Pty Ltd", "Ltd", "Group Pty Ltd"])
    company_name = f"{fake.company()} {company_suffix}"
    abn = generate_valid_abn()
    acn = generate_valid_acn()
    addr = generate_address()
    
    hr_first = fake.first_name()
    hr_last = fake.last_name()
    
    return {
        "company_name": company_name,
        "abn": abn,
        "formatted_abn": format_abn(abn),
        "acn": acn,
        "formatted_acn": format_acn(acn),
        "address": addr,
        "hr_name": f"{hr_first} {hr_last}",
        "hr_title": random.choice(["HR Manager", "People & Culture Lead", "Human Resources Director", "Talent Acquisition Lead"])
    }

def calculate_net_income(gross_income, pay_frequency):
    """Calculates Australian net income after tax, medicare, HECS (optional)"""
    # 2024-25 simplified rates
    if gross_income <= 18200:
        tax = 0
    elif gross_income <= 45000:
        tax = (gross_income - 18200) * 0.16
    elif gross_income <= 135000:
        tax = 4288 + (gross_income - 45000) * 0.30
    elif gross_income <= 190000:
        tax = 31288 + (gross_income - 135000) * 0.37
    else:
        tax = 51638 + (gross_income - 190000) * 0.45
        
    # Medicare levy 2%
    medicare = gross_income * 0.02
    total_tax = tax + medicare
    
    # HECS/HELP liability simulation (approx 20% probability if income is higher than $60k)
    hecs = 0
    if gross_income > 60000 and random.random() < 0.2:
        # Simplified HECS rate (between 2.5% and 8% depending on income)
        hecs_rate = min(0.08, 0.025 + (gross_income - 60000) / 100000 * 0.05)
        hecs = gross_income * hecs_rate
        
    net_annual = gross_income - total_tax - hecs
    
    periods = {"Weekly": 52, "Fortnightly": 26, "Monthly": 12}
    n_periods = periods[pay_frequency]
    
    return {
        "gross_per_period": round(gross_income / n_periods, 2),
        "tax_withheld_per_period": round(total_tax / n_periods, 2),
        "hecs_per_period": round(hecs / n_periods, 2),
        "net_per_period": round(net_annual / n_periods, 2),
        "super_per_period": round((gross_income * 0.115) / n_periods, 2), # 11.5% SG
        "hecs_flag": hecs > 0
    }

def generate_salary_profile():
    """Generates salary, occupation, and financial profile details"""
    occ = random.choice(OCCUPATIONS)
    gross_income = random.randint(occ["min_sal"], occ["max_sal"])
    pay_freq = random.choice(["Weekly", "Fortnightly", "Monthly"])
    
    calc = calculate_net_income(gross_income, pay_freq)
    
    return {
        "job_title": occ["title"],
        "gross_annual_salary": gross_income,
        "pay_frequency": pay_freq,
        **calc
    }
