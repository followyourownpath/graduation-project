import random
from datetime import datetime, timedelta
import generators

FRAUD_TYPES = {
    1: "Salary Mismatch (Income Increased)",
    2: "Employer Mismatch",
    3: "No Salary Credit",
    4: "Future Pay Date",
    5: "Name Typo / Mismatch",
    6: "Invalid BSB Code",
    7: "Invalid ABN Checksum",
    8: "Duplicate Payslip Content",
    9: "Tax Withheld Mismatch",
    10: "Super Guarantee Mismatch",
    11: "Tenure / Start Date Mismatch",
    12: "Address Mismatch",
    13: "Cash Deposit Injection",
    14: "Overdrawn Account Status",
    15: "Signature / Date Anomaly"
}

def inject_fraud(clean_record, fraud_type_id):
    """
    Injects a specific type of fraud into a clean record.
    Returns a modified copy of the record with labels.
    """
    import copy
    record = copy.deepcopy(clean_record)
    
    # Initialize labels
    record["is_fraud"] = True
    record["fraud_type_id"] = fraud_type_id
    record["fraud_type_name"] = FRAUD_TYPES[fraud_type_id]
    record["fraud_description"] = ""
    
    # Generate risk score for fraudulent accounts (typically 70-98)
    record["risk_score"] = random.randint(75, 98)
    
    if fraud_type_id == 1:
        # Salary Mismatch (Income Increased by 40% on Payslips/Letter, but Bank Credit remains the same)
        # We increase payslips and employment letter gross & net, but keep bank credit at original level.
        factor = 1.40
        record["salary"]["gross_annual_salary"] = round(record["salary"]["gross_annual_salary"] * factor, 2)
        record["salary"]["gross_per_period"] = round(record["salary"]["gross_per_period"] * factor, 2)
        record["salary"]["net_per_period"] = round(record["salary"]["net_per_period"] * factor, 2)
        record["salary"]["tax_withheld_per_period"] = round(record["salary"]["tax_withheld_per_period"] * factor, 2)
        record["salary"]["super_per_period"] = round(record["salary"]["super_per_period"] * factor, 2)
        
        # Update payslips lists to reflect higher income
        ytd_gross = 0
        ytd_net = 0
        ytd_tax = 0
        for payslip in record["payslips"]:
            payslip["gross"] = record["salary"]["gross_per_period"]
            payslip["net"] = record["salary"]["net_per_period"]
            payslip["tax"] = record["salary"]["tax_withheld_per_period"]
            payslip["super"] = record["salary"]["super_per_period"]
            
            ytd_gross += payslip["gross"]
            ytd_net += payslip["net"]
            ytd_tax += payslip["tax"]
            
            payslip["ytd_gross"] = round(ytd_gross, 2)
            payslip["ytd_net"] = round(ytd_net, 2)
            payslip["ytd_tax"] = round(ytd_tax, 2)
            
        # Update employment letter
        record["employment_letter"]["salary"] = record["salary"]["gross_annual_salary"]
        
        record["fraud_description"] = "Salary mismatch: Payslip and employment letter state a salary 40% higher than the bank statement deposit."

    elif fraud_type_id == 2:
        # Employer Mismatch
        # Change the employer name on the payslip and employment letter to a different company name
        fake_employer = generators.generate_company()
        record["company"]["company_name"] = fake_employer["company_name"]
        record["company"]["abn"] = fake_employer["abn"]
        record["company"]["formatted_abn"] = fake_employer["formatted_abn"]
        record["company"]["acn"] = fake_employer["acn"]
        record["company"]["formatted_acn"] = fake_employer["formatted_acn"]
        record["company"]["address"] = fake_employer["address"]
        
        # Payslips and Employment Letter now show fake_employer,
        # but the bank statement transaction descriptions will still show the original company name as the credit source.
        # Original company name is stored in clean_record["company"]["company_name"]
        record["fraud_description"] = f"Employer mismatch: Payslip/Letter states employer is '{fake_employer['company_name']}', but bank deposits are from '{clean_record['company']['company_name']}'."

    elif fraud_type_id == 3:
        # No Salary Credit
        # Remove all salary/payroll credits from the bank statement
        filtered_txs = []
        for tx in record["bank_statement"]["transactions"]:
            if "payroll" not in tx["description"].lower() and "salary" not in tx["description"].lower():
                filtered_txs.append(tx)
            else:
                # If salary transaction is removed, we must deduct it from closing balance and transaction amounts
                record["bank_statement"]["closing_balance"] -= tx["credit"]
        record["bank_statement"]["transactions"] = filtered_txs
        record["fraud_description"] = "No Salary Credit: Bank statement has no record of salary/payroll credits matching the payslip."

    elif fraud_type_id == 4:
        # Future Pay Date
        # Set the pay date of the latest payslip to a future date relative to the application date.
        # Let's say application date is today. We set pay date of the latest payslip to today + 15 days.
        app_date = datetime.today()
        future_date = app_date + timedelta(days=15)
        record["payslips"][-1]["pay_date"] = future_date.strftime("%d/%m/%Y")
        
        # Change pay period to match
        p_len = 30 if record["salary"]["pay_frequency"] == "Monthly" else (14 if record["salary"]["pay_frequency"] == "Fortnightly" else 7)
        p_start = future_date - timedelta(days=p_len)
        p_end = future_date - timedelta(days=1)
        record["payslips"][-1]["period_start"] = p_start.strftime("%d/%m/%Y")
        record["payslips"][-1]["period_end"] = p_end.strftime("%d/%m/%Y")
        
        record["fraud_description"] = f"Future date: Latest payslip has a payment date in the future ({future_date.strftime('%d/%m/%Y')})."

    elif fraud_type_id == 5:
        # Name Typo / Mismatch
        # Introduce a typo in the employee name on the payslip
        original_name = record["person"]["full_name"]
        # E.g. "Jane Smith" -> "Jane Smtih" or "Jame Smith"
        if len(record["person"]["first_name"]) > 3:
            typo_first = record["person"]["first_name"][:-2] + record["person"]["first_name"][-1] + record["person"]["first_name"][-2]
        else:
            typo_first = record["person"]["first_name"] + "x"
            
        typo_name = f"{typo_first} {record['person']['last_name']}"
        
        # Update name on payslips only
        for payslip in record["payslips"]:
            payslip["employee_name"] = typo_name
            
        record["fraud_description"] = f"Name mismatch: Payslips list name as '{typo_name}', but ID and Bank Statement list '{original_name}'."

    elif fraud_type_id == 6:
        # Invalid BSB Code
        # Change the bank BSB code to a random invalid code, e.g. "999-999" or letters
        record["bank_statement"]["bsb"] = "999-999"
        record["fraud_description"] = "Invalid BSB: The BSB code on the bank statement (999-999) is invalid."

    elif fraud_type_id == 7:
        # Invalid ABN Checksum
        # Change the employer ABN to an invalid ABN on the payslips and employment letter
        invalid_abn = "12345678901" # Obviously invalid as it fails the checksum
        record["company"]["abn"] = invalid_abn
        record["company"]["formatted_abn"] = f"{invalid_abn[0:2]} {invalid_abn[2:5]} {invalid_abn[5:8]} {invalid_abn[8:11]}"
        record["fraud_description"] = f"Invalid ABN: The ABN '{record['company']['formatted_abn']}' on the payslip/letter fails the Australian checksum validation."

    elif fraud_type_id == 8:
        # Duplicate Payslip Content
        # Copy the second payslip's fields completely into the third payslip (including dates or YTD numbers)
        # indicating copy-paste forgery.
        if len(record["payslips"]) >= 3:
            # Keep the pay date and periods but make all financial and YTD fields identical,
            # which is mathematically impossible because YTD should increase.
            p2 = record["payslips"][1]
            p3 = record["payslips"][2]
            p3["gross"] = p2["gross"]
            p3["net"] = p2["net"]
            p3["tax"] = p2["tax"]
            p3["super"] = p2["super"]
            p3["ytd_gross"] = p2["ytd_gross"]
            p3["ytd_net"] = p2["ytd_net"]
            p3["ytd_tax"] = p2["ytd_tax"]
            p3["ytd_super"] = p2["ytd_super"]
            
        record["fraud_description"] = "Duplicate payslip YTD: The cumulative YTD values on the latest payslip are identical to the previous payslip, indicating manual manipulation."

    elif fraud_type_id == 9:
        # Tax Withheld Mismatch
        # Set the tax withheld to a ridiculously low level on the payslips (e.g. $10 per period)
        # while gross income is high.
        for payslip in record["payslips"]:
            payslip["tax"] = 10.00
            # Adjust net accordingly
            payslip["net"] = round(payslip["gross"] - payslip["tax"], 2)
            
        record["fraud_description"] = "Tax withheld mismatch: The tax withheld on payslips is mathematically inconsistent with Australian PAYG withholding schedules for the stated gross income."

    elif fraud_type_id == 10:
        # Super Guarantee Mismatch
        # Set superannuation contribution to 0 or < 5% (instead of standard 11.5%)
        for payslip in record["payslips"]:
            payslip["super"] = round(payslip["gross"] * 0.02, 2) # Only 2%
            
        record["fraud_description"] = "Superannuation mismatch: Superannuation contributions on payslips are below the mandatory Australian Super Guarantee (SG) rate of 11.5%."

    elif fraud_type_id == 11:
        # Tenure / Start Date Mismatch
        # Change start date in employment letter to be after payslip dates.
        # E.g. first payslip is from 3 months ago, but letter says employee started 1 month ago.
        letter_date = datetime.strptime(record["employment_letter"]["letter_date"], "%d/%m/%Y")
        future_start_date = letter_date - timedelta(days=20)
        record["employment_letter"]["start_date"] = future_start_date.strftime("%d/%m/%Y")
        
        record["fraud_description"] = f"Tenure mismatch: Employment letter lists start date as {record['employment_letter']['start_date']}, but payslips showing active pay period begin prior to this date."

    elif fraud_type_id == 12:
        # Address Mismatch
        # Change bank statement address to a different address than ID/Application
        fake_addr = generators.generate_address()
        record["bank_statement"]["address"] = fake_addr
        
        record["fraud_description"] = f"Address mismatch: Bank statement address '{fake_addr['full_address']}' does not match the residential address on the ID/Application '{record['person']['address']['full_address']}'."

    elif fraud_type_id == 13:
        # Cash Deposit Injection
        # Add a large cash deposit to bank statement transactions just before application date
        last_tx_date = datetime.strptime(record["bank_statement"]["transactions"][-1]["date"], "%d/%m/%Y")
        injection_date = last_tx_date - timedelta(days=2)
        
        large_dep = {
            "date": injection_date.strftime("%d/%m/%Y"),
            "description": "CASH DEPOSIT BRANCH SYDNEY",
            "debit": 0.0,
            "credit": 35000.0,
            "balance": record["bank_statement"]["transactions"][-1]["balance"]
        }
        
        # Inject and adjust balances for subsequent transactions
        record["bank_statement"]["transactions"].insert(-1, large_dep)
        for i in range(len(record["bank_statement"]["transactions"])):
            tx = record["bank_statement"]["transactions"][i]
            # Recalculate rolling balance
            if i == 0:
                tx["balance"] = record["bank_statement"]["opening_balance"] - tx["debit"] + tx["credit"]
            else:
                prev_bal = record["bank_statement"]["transactions"][i-1]["balance"]
                tx["balance"] = prev_bal - tx["debit"] + tx["credit"]
                
        record["bank_statement"]["closing_balance"] = record["bank_statement"]["transactions"][-1]["balance"]
        record["fraud_description"] = "Large cash deposit injection: Bank statement shows a large cash deposit of $35,000 just before the application, which represents a potential unverified source of funds."

    elif fraud_type_id == 14:
        # Overdrawn Account Status / Dishonour fees
        # Inject multiple transactions with dishonor fees and push balance negative
        last_tx_date = datetime.strptime(record["bank_statement"]["transactions"][-1]["date"], "%d/%m/%Y")
        
        fee1_date = last_tx_date - timedelta(days=12)
        fee2_date = last_tx_date - timedelta(days=10)
        
        fees = [
            {"date": fee1_date.strftime("%d/%m/%Y"), "description": "DISHONOUR FEE - DIRECT DEBIT", "debit": 15.00, "credit": 0.0, "balance": 0.0},
            {"date": fee2_date.strftime("%d/%m/%Y"), "description": "DISHONOUR FEE - DIRECT DEBIT", "debit": 15.00, "credit": 0.0, "balance": 0.0}
        ]
        
        # Force a negative balance transaction
        neg_tx = {"date": (fee1_date - timedelta(days=1)).strftime("%d/%m/%Y"), "description": "WITHDRAWAL ATM OVERDRAWN", "debit": 200.00, "credit": 0.0, "balance": -150.00}
        
        # Inject transactions at index 5, 6, 7
        record["bank_statement"]["transactions"].insert(5, neg_tx)
        record["bank_statement"]["transactions"].insert(6, fees[0])
        record["bank_statement"]["transactions"].insert(7, fees[1])
        
        # Recalculate rolling balances
        for i in range(len(record["bank_statement"]["transactions"])):
            tx = record["bank_statement"]["transactions"][i]
            if i == 0:
                tx["balance"] = record["bank_statement"]["opening_balance"] - tx["debit"] + tx["credit"]
            else:
                prev_bal = record["bank_statement"]["transactions"][i-1]["balance"]
                tx["balance"] = prev_bal - tx["debit"] + tx["credit"]
                
        record["bank_statement"]["closing_balance"] = record["bank_statement"]["transactions"][-1]["balance"]
        
        record["fraud_description"] = "Financial distress indicators: Bank statement shows multiple dishonour fees and persistent negative balances."

    elif fraud_type_id == 15:
        # Signature / Date Anomaly
        # Employment letter date set to 180 days ago (too old)
        six_months_ago = datetime.today() - timedelta(days=180)
        record["employment_letter"]["letter_date"] = six_months_ago.strftime("%d/%m/%Y")
        record["employment_letter"]["signatory_name"] = "Missing Signature"
        record["employment_letter"]["signatory_title"] = ""
        
        record["fraud_description"] = "Document anomaly: Employment letter is outdated (> 180 days old) and lacks HR signatory details."

    return record
