import os
import sys
import json
import random
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Import our custom modules
import generators
import fraud_engine
import dataset_manager

def generate_financial_history(person, company, salary_profile):
    """
    Generates realistic, clean documents structure for an application.
    This includes:
      - 3 Payslips
      - 1 Employment Letter
      - 1 Bank Statement (with salary credits matching net pay)
    """
    # Anchor application date: July 1, 2026
    app_date = datetime(2026, 7, 1)
    
    # 1. Generate Payslips
    payslips = []
    pay_freq = salary_profile["pay_frequency"]
    net_pay = salary_profile["net_per_period"]
    gross_pay = salary_profile["gross_per_period"]
    tax_withheld = salary_profile["tax_withheld_per_period"]
    super_contrib = salary_profile["super_per_period"]
    hecs_val = salary_profile["hecs_per_period"]
    
    # Determine intervals
    if pay_freq == "Monthly":
        intervals = [30, 60, 90]
        periods_in_year_to_june = 12
    elif pay_freq == "Fortnightly":
        intervals = [14, 28, 42]
        periods_in_year_to_june = 26
    else: # Weekly
        intervals = [7, 14, 21]
        periods_in_year_to_june = 52
        
    # Payslips generated going backwards
    # Assume financial year ends June 30, so June payslip is month 12, May is 11, etc.
    # We will generate 3 payslips (e.g. June, May, April)
    ytd_gross = gross_pay * (periods_in_year_to_june - 2)
    ytd_tax = tax_withheld * (periods_in_year_to_june - 2)
    ytd_super = super_contrib * (periods_in_year_to_june - 2)
    ytd_hecs = hecs_val * (periods_in_year_to_june - 2)
    ytd_net = net_pay * (periods_in_year_to_june - 2)
    
    for idx, days_back in enumerate(reversed(intervals)):
        pay_date = app_date - timedelta(days=days_back - 1) # pay date is near end of period
        period_start = pay_date - timedelta(days=intervals[0])
        period_end = pay_date - timedelta(days=1)
        
        # Increment YTD
        ytd_gross = round(ytd_gross + gross_pay, 2)
        ytd_tax = round(ytd_tax + tax_withheld, 2)
        ytd_super = round(ytd_super + super_contrib, 2)
        ytd_hecs = round(ytd_hecs + hecs_val, 2)
        ytd_net = round(ytd_net + net_pay, 2)
        
        payslips.append({
            "employee_name": person["full_name"],
            "pay_date": pay_date.strftime("%d/%m/%Y"),
            "period_start": period_start.strftime("%d/%m/%Y"),
            "period_end": period_end.strftime("%d/%m/%Y"),
            "gross": gross_pay,
            "net": net_pay,
            "tax": tax_withheld,
            "hecs": hecs_val,
            "super": super_contrib,
            "ytd_gross": ytd_gross,
            "ytd_tax": ytd_tax,
            "ytd_super": ytd_super,
            "ytd_hecs": ytd_hecs,
            "ytd_net": ytd_net
        })
        
    # 2. Generate Employment Letter details
    tenure_years = random.randint(1, 4)
    start_date = app_date - timedelta(days=365 * tenure_years + random.randint(0, 360))
    el_date = app_date - timedelta(days=random.randint(2, 10))
    
    employment_letter = {
        "letter_date": el_date.strftime("%d/%m/%Y"),
        "employee_name": person["full_name"],
        "job_title": salary_profile["job_title"],
        "start_date": start_date.strftime("%d/%m/%Y"),
        "salary": salary_profile["gross_annual_salary"],
        "probation_status": "Not on probation",
        "signatory_name": company["hr_name"],
        "signatory_title": company["hr_title"]
    }
    
    # 3. Generate Bank Statement details (3 months transactions)
    # Start: April 1, 2026. End: June 30, 2026.
    stmt_start = app_date - timedelta(days=91)
    stmt_end = app_date - timedelta(days=1)
    bsb = f"{random.randint(10, 99):02d}{random.randint(0, 9):01d}-{random.randint(100, 999):03d}"
    acc_num = f"{random.randint(1000, 9999):04d} {random.randint(1000, 9999):04d}"
    
    opening_bal = round(random.uniform(5000.0, 25000.0), 2)
    balance = opening_bal
    
    transactions = []
    
    # Determine transaction dates
    curr_date = stmt_start
    
    # Regular bills schedule
    rent_day_interval = 7 if random.random() < 0.5 else 30 # Weekly vs Monthly rent
    rent_amount = round(random.uniform(350, 600) if rent_day_interval == 7 else random.uniform(1500, 2600), 2)
    
    while curr_date <= stmt_end:
        # Check if salary date
        is_sal_day = False
        for payslip in payslips:
            p_dt = datetime.strptime(payslip["pay_date"], "%d/%m/%Y")
            if curr_date.date() == p_dt.date():
                is_sal_day = True
                break
                
        if is_sal_day:
            desc = f"DIRECT DEP {company['company_name'].upper()[:15]} PAYROLL"
            transactions.append({
                "date": curr_date.strftime("%d/%m/%Y"),
                "description": desc,
                "debit": 0.0,
                "credit": net_pay,
                "balance": 0.0 # will fill later
            })
            
        # Rent payment
        if rent_day_interval == 7 and curr_date.weekday() == 3: # Thursday rent
            transactions.append({
                "date": curr_date.strftime("%d/%m/%Y"),
                "description": "RENT DEBIT REAL ESTATE MGT",
                "debit": rent_amount,
                "credit": 0.0,
                "balance": 0.0
            })
        elif rent_day_interval == 30 and curr_date.day == 1: # 1st of month rent
            transactions.append({
                "date": curr_date.strftime("%d/%m/%Y"),
                "description": "RENT DEBIT REAL ESTATE MGT",
                "debit": rent_amount,
                "credit": 0.0,
                "balance": 0.0
            })
            
        # Groceries (Coles / Woolworths, twice a week)
        if curr_date.weekday() in [2, 5]: # Wed and Sat
            groc_store = random.choice(["COLES SUPERMARKETS", "WOOLWORTHS MELBOURNE", "ALDI STORES"])
            transactions.append({
                "date": curr_date.strftime("%d/%m/%Y"),
                "description": f"DEBIT CARD {groc_store}",
                "debit": round(random.uniform(60.0, 220.0), 2),
                "credit": 0.0,
                "balance": 0.0
            })
            
        # Utilities/subscriptions (random days)
        if curr_date.day == 10:
            transactions.append({
                "date": curr_date.strftime("%d/%m/%Y"),
                "description": "TELSTRA BILL PAYMENT DIRECT DEBIT",
                "debit": round(random.uniform(50.0, 120.0), 2),
                "credit": 0.0,
                "balance": 0.0
            })
        if curr_date.day == 20:
            transactions.append({
                "date": curr_date.strftime("%d/%m/%Y"),
                "description": "ORIGIN ENERGY ELECTRICITY BILL",
                "debit": round(random.uniform(120.0, 310.0), 2),
                "credit": 0.0,
                "balance": 0.0
            })
            
        # Random daily transactions (coffee, eating out)
        if random.random() < 0.4:
            desc = random.choice([
                "POS DEBIT STARBUCKS SYDNEY",
                "POS DEBIT UBER EATS",
                "ATM WITHDRAWAL ATM-FEE $2.50",
                "POS DEBIT JB HI-FI",
                "POS DEBIT 7-ELEVEN STORE",
                "POS DEBIT CHEAPAS CHIPS",
                "NETFLIX.COM INTERNET SUB"
            ])
            transactions.append({
                "date": curr_date.strftime("%d/%m/%Y"),
                "description": desc,
                "debit": round(random.uniform(5.0, 80.0), 2),
                "credit": 0.0,
                "balance": 0.0
            })
            
        curr_date += timedelta(days=1)
        
    # Sort transactions by date (optional, already chronologically generated)
    # Fill balances
    for tx in transactions:
        balance = round(balance - tx["debit"] + tx["credit"], 2)
        tx["balance"] = balance
        
    closing_bal = balance
    
    bank_statement = {
        "bsb": bsb,
        "account_number": acc_num,
        "period_start": stmt_start.strftime("%d/%m/%Y"),
        "period_end": stmt_end.strftime("%d/%m/%Y"),
        "opening_balance": opening_bal,
        "closing_balance": closing_bal,
        "address": person["address"],
        "transactions": transactions
    }
    
    # We return the latest payslip as the main "payslip" record, and keep the list
    return {
        "person": person,
        "company": company,
        "salary": salary_profile,
        "payslips": payslips,
        "payslip": payslips[-1], # The latest payslip
        "employment_letter": employment_letter,
        "bank_statement": bank_statement
    }

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic Australian mock data with fraud injection.")
    parser.add_argument('--num-apps', type=int, default=20, help="Number of applications to generate (default: 20)")
    parser.add_argument('--output-dir', type=str, default="dataset", help="Output directory path (default: 'dataset')")
    parser.add_argument('--fraud-ratio', type=type(0.1), default=0.3, help="Ratio of fraudulent applications (default: 0.3)")
    parser.add_argument('--no-pdf', action='store_true', help="Skip PDF rendering (generates only JSONs, much faster)")
    
    args = parser.parse_args()
    
    print(f"Initializing Dataset Generation in '{args.output_dir}'...")
    base_path = dataset_manager.create_dataset_directories(args.output_dir)
    
    # Generate common Pools
    print("Generating Persons & Companies pool...")
    companies_pool = [generators.generate_company() for _ in range(max(10, args.num_apps // 5))]
    
    # Track metadata
    ground_truth_dict = {}
    label_dict = {}
    
    # Determine splits for indices
    splits = dataset_manager.split_dataset(args.num_apps)
    
    # Counts
    fraud_count = int(args.num_apps * args.fraud_ratio)
    fraud_indices = set(random.sample(range(args.num_apps), fraud_count))
    
    print(f"Generating {args.num_apps} applications ({args.num_apps - fraud_count} clean, {fraud_count} fraudulent)...")
    
    for i in range(args.num_apps):
        app_id = f"{100000 + i}"
        
        # 1. Generate clean profile
        person = generators.generate_person()
        company = random.choice(companies_pool)
        salary_profile = generators.generate_salary_profile()
        
        clean_record = generate_financial_history(person, company, salary_profile)
        clean_record["application_id"] = app_id
        
        # Store clean details for Ground Truth
        # Ground Truth contains the absolute correct information
        ground_truth_dict[app_id] = {
            "applicant_name": person["full_name"],
            "date_of_birth": person["dob"],
            "residential_address": person["address"]["full_address"],
            "employer_name": company["company_name"],
            "employer_abn": company["abn"],
            "annual_gross_salary": salary_profile["gross_annual_salary"],
            "job_title": salary_profile["job_title"],
            "monthly_net_income": round(salary_profile["gross_annual_salary"] * 0.8 / 12, 2), # approx net standard
            "bank_account": f"BSB: {clean_record['bank_statement']['bsb']} Acc: {clean_record['bank_statement']['account_number']}"
        }
        
        # 2. Fraud Injection (if index is marked for fraud)
        if i in fraud_indices:
            fraud_type_id = random.randint(1, 15)
            final_record = fraud_engine.inject_fraud(clean_record, fraud_type_id)
        else:
            final_record = clean_record
            final_record["is_fraud"] = False
            final_record["fraud_type_id"] = 0
            final_record["fraud_type_name"] = "None"
            final_record["fraud_description"] = "Clean application, no discrepancies detected."
            final_record["risk_score"] = random.randint(5, 22)
            
        # Store Label details
        label_dict[app_id] = {
            "application_id": app_id,
            "is_fraud": final_record["is_fraud"],
            "fraud_type_id": final_record["fraud_type_id"],
            "fraud_type_name": final_record["fraud_type_name"],
            "fraud_description": final_record["fraud_description"],
            "risk_score": final_record["risk_score"]
        }
        
        # Save application split folder
        split = splits[i]
        sys.stdout.write(f"\rProcessing App {i+1}/{args.num_apps} ({split})...")
        sys.stdout.flush()
        
        dataset_manager.save_application_data(
            base_path=base_path,
            app_record=final_record,
            split=split,
            render_pdfs=not args.no_pdf
        )
        
    print("\nWriting global dataset files...")
    
    # Save global ground truth JSON
    with open(base_path / "ground_truth.json", 'w', encoding='utf-8') as f:
        json.dump(ground_truth_dict, f, indent=2, ensure_ascii=False)
        
    # Save global labels JSON
    with open(base_path / "label.json", 'w', encoding='utf-8') as f:
        json.dump(label_dict, f, indent=2, ensure_ascii=False)
        
    print(f"Dataset Generation Complete! Outputs saved in: {base_path.absolute()}")
    print(f"Summary: Clean = {args.num_apps - len(fraud_indices)}, Fraudulent = {len(fraud_indices)}")

if __name__ == "__main__":
    main()
