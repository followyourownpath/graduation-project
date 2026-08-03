# Golden Test Dataset (Zero-Risk) — Handoff Documentation

> **Audience**: SmartFinn Developers, QA Testers, and CRM Integration Engineers  
> **Location**: `mock-data/goldenData_zero_risk/`  
> **Goal**: Provide a 100% consistent, realistic 5-document test suite that passes all 13 Phase 1 Rules Engine rules with an **Overall Risk Score of 0** (`low` risk level).

---

## 1. Directory & File Overview

Path: `mock-data/goldenData_zero_risk/`

| File Name | Document Type | Description |
|---|---|---|
| `FFS zero risk.pdf` | `fact_find` | Fillable Customer Fact Find PDF with non-repeating distinct field values. |
| `id.jpg` | `id_100` | NSW Driver Licence image for Junhong ZHONG. |
| `payslip.pdf` | `payslip` | Official 1-page payslip from Tech Solutions Pty Ltd. |
| `bank_statement.pdf` | `bank_statement_3m` | Multi-page (47 transactions, 3 months) bank statement from SmartFinn Mutual Bank. |
| `Mock_Notice_of_Assessment.pdf` | `ato_notice` | ATO Notice of Assessment based on official ATO template format. |

---

## 2. Baseline Customer Profile (`Junhong Zhong`)

| Parameter | Baseline Value | Source |
|---|---|---|
| **Full Legal Name** | `Junhong Zhong` (ID: `Junhong ZHONG`, NOA: `MR JUNHONG ZHONG`) | FFS & ID |
| **Residential Address** | `150 Todman Ave, Kensington NSW 2033` | FFS & ID |
| **FFS Cover Form Date** | `01/07/2022` (ID Expiry Date: `12 DEC 2023`) | FFS & ID |
| **Employer Name** | `Tech Solutions Pty Ltd` | FFS Current Employment |
| **Employment Start Date** | `2015-10-15` (Payslip Pay Period End: `17/06/2026`) | FFS Current Employment |
| **Repayment Account Name**| `Junhong Zhong` | FFS Preferred Repayment Account |
| **Repayment BSB** | `062-235` (digits: `062235`) | FFS Preferred Repayment Account |
| **Repayment Account Number**| `10473829` | FFS Preferred Repayment Account |
| **Declared Savings Asset** | `Savings Account` value `$15,420` | FFS Financial Position (Asset 1) |

---

## 3. Phase 1 Rules Compliance Matrix (13/13 Passed)

| Rule ID | Rule Label | Document | Field Compared | Target Value | Evaluation |
|---|---|---|---|---|---|
| **FF-ID-001** | Applicant name matches ID | ID (`id_100`) | `full_legal_name` | `Junhong ZHONG` | **PASS** |
| **FF-ID-002** | Applicant address matches ID | ID (`id_100`) | `residential_address` | `150 TODMAN AVE, KENSINGTON NSW 2033` | **PASS** |
| **FF-ID-003** | ID valid on cover date | ID (`id_100`) | `expiry_date` | `2023-12-12` >= `2022-07-01` | **PASS** |
| **FF-PS-001** | Applicant name matches Payslip | Payslip (`payslip`) | `employee_name` | `Junhong Zhong` | **PASS** |
| **FF-PS-002** | Employer matches Payslip | Payslip (`payslip`) | `employer_name` | `Tech Solutions Pty Ltd` | **PASS** |
| **FF-PS-003** | Pay period after employment start | Payslip (`payslip`) | `pay_period_end` | `2026-06-17` >= `2015-10-15` | **PASS** |
| **FF-BS-001** | Bank holder matches Applicant | Bank Statement (`bank_statement_3m`) | `account_holder_name` | `Junhong Zhong` | **PASS** |
| **FF-BS-002** | Bank holder matches Repayment Name | Bank Statement (`bank_statement_3m`) | `account_holder_name` | `Junhong Zhong` | **PASS** |
| **FF-BS-003** | Bank BSB matches Repayment BSB | Bank Statement (`bank_statement_3m`) | `bsb` | `062-235` | **PASS** |
| **FF-BS-004** | Bank Acc # matches Repayment Acc # | Bank Statement (`bank_statement_3m`) | `account_number` | `10473829` | **PASS** |
| **FF-BS-006** | Closing balance matches Savings | Bank Statement (`bank_statement_3m`) | `closing_balance` | `$15,420.00` | **PASS** |
| **FF-NOA-001** | Applicant name matches NOA | NOA (`ato_notice`) | `taxpayer_name` | `MR JUNHONG ZHONG` | **PASS** |
| **FF-NOA-002** | Applicant address matches NOA | NOA (`ato_notice`) | `taxpayer_address` | `150 TODMAN AVE, KENSINGTON NSW 2033` | **PASS** |

**Document Scores**: ID = 0, Payslip = 0, Bank Statement = 0, NOA = 0  
**Overall Risk Score**: **0** (Risk Level: `low`)

---

## 4. Key Highlights & Verification Details

1. **Distinct FFS Field Inputs**:
   - All fields in `FFS zero risk.pdf` have unique, distinct values (e.g. unique income, expense, asset, and liability numbers) rather than repeated placeholder values (like `2500`), making it ideal for testing CRM parameter pass-through.

2. **Long Multi-Page Bank Statement Flow**:
   - `bank_statement.pdf` features **47 transactions** spanning 3 full months (01/04/2026 – 30/06/2026).
   - Starts at Opening Balance `$12,180.00`, records regular salary deposits from `Tech Solutions Pty Ltd` ($3,666.66) alongside realistic living expenses, and ends at Closing Balance **`$15,420.00`** with 100% exact running arithmetic.

3. **Official ATO Template Preservation for NOA**:
   - `Mock_Notice_of_Assessment.pdf` is built directly on the template from `mock-data/goldenData/Mock_Notice_of_Assessment.pdf`, maintaining 100% of the original ATO logo, layout, fonts, and table structure while updating taxpayer identity fields.

---

## 5. Scripts & Re-generation Commands

- **Generation Script**: `mock-data/generate_golden_zero_risk.py`
  - Re-renders `payslip.pdf`, `bank_statement.pdf`, and `Mock_Notice_of_Assessment.pdf`.
  - Command:
    ```bash
    python mock-data/generate_golden_zero_risk.py
    ```

- **Rules Engine Test Verification Script**: `mock-data/test_golden_zero_risk.py`
  - Executes AcroForm PDF parsing on `FFS zero risk.pdf` and runs `evaluate_phase1` to verify rule statuses.
  - Command:
    ```bash
    python mock-data/test_golden_zero_risk.py
    ```
