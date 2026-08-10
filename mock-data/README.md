# Australian Lending Document Synthetic Dataset Generator

A professional Python-based synthetic data generation pipeline designed for compliance testing, document fraud detection, and verification engine validation. This tool generates realistic Australian financial documents (Payslips, Bank Statements, Employment Letters, IDs) and simulates Azure Document Intelligence OCR extraction outputs, with support for **15 types of injected fraud discrepancies**.

---

## ✨ Features

- **Realistic Persona Pool**: Generates authentic Australian addresses mapped to real suburbs and postcodes, names, phones, and ID details.
- **Valid Financial Calculations**: Evaluates pay cycles (Weekly/Fortnightly/Monthly), dynamic PAYG tax withholding, Medicare levy (2%), HECS/HELP repayments, and superannuation contributions (11.5% SG) based on standard Australian marginal tax schedules.
- **Valid Business Entities**: Generates mathematically correct ABN and ACN identifiers adhering to the official ATO checksum algorithms.
- **15 Fraud Injection Types**: Artificially injects distinct document tampering anomalies (e.g., salary/employer mismatches, invalid BSB/ABN, future pay dates, cumulative YTD duplicate errors, overdrawn balances, and signature issues) to test rule engines.
- **Premium PDF Layouts**: Automatically renders clean, professional-looking PDFs using ReportLab.
- **Dataset Orchestration**: Partitions data into `train`, `val`, and `test` segments and exports structured global annotation registers (`label.json` & `ground_truth.json`).

---

## 📁 Repository Structure

```
├── generate.py           # Main driver CLI script
├── generators.py         # Entities, addresses, ABN/ACN, and financial math
├── fraud_engine.py       # Injects 15 classes of document discrepancies
├── document_renderer.py  # PDF render templates (ReportLab implementation)
├── dataset_manager.py    # Directory management, splits, and OCR simulation
├── .gitignore            # Excludes datasets from git tracking
└── README.md             # Project documentation
```

---

## 🛠️ Installation & Setup

1. **Clone this repository**:
   ```bash
   git clone git@github.com:unsw-cse-comp99-3900/capstone-project-26t2-9900-w19b-bread.git
   cd capstone-project-26t2-9900-w19b-bread/mock-data
   ```

2. **Install the dependencies**:
   This project relies on `reportlab` (for PDF generation) and `faker` (for mock data profiles).
   ```bash
   pip install reportlab faker
   ```

---

## 🚀 How to Run the Generator

Configure the dataset parameters using command-line arguments:

```bash
python generate.py [OPTIONS]
```

### Options:
- `--num-apps INT`: Number of applications (folders containing documents + OCR data) to generate. (Default: `20`)
- `--output-dir PATH`: Target output directory. (Default: `dataset`)
- `--fraud-ratio FLOAT`: Proportion of generated applications containing fraud. (Default: `0.3`)
- `--no-pdf`: Generates JSON metadata and OCR outputs only (skips PDF rendering for high speed).

### Examples:

- **Generate a small test batch (20 apps) with PDFs**:
  ```bash
  python generate.py --num-apps 20 --output-dir dataset
  ```

- **Generate a large training split (1000 apps) for ML models (Fast Mode, no PDFs)**:
  ```bash
  python generate.py --num-apps 1000 --fraud-ratio 0.35 --no-pdf --output-dir dataset_json
  ```

---

## 📦 Generated Dataset Anatomy

Each output dataset contains a directory structure like the following:

```
output_directory/
├── train/
│   ├── app_100000/
│   │   ├── payslip.pdf            # Salary/Payslip PDF
│   │   ├── bank_statement.pdf     # Transaction/Ledger PDF
│   │   ├── employment_letter.pdf  # HR Verification Letter PDF
│   │   ├── id.pdf                 # Identity Verification PDF
│   │   └── ocr.json               # Simulated Azure OCR Extracted Fields & Confidence
│   └── ...
├── val/
├── test/
├── ground_truth.json              # Global true values map (for accuracy calculation)
└── label.json                     # Global label map (target variable, risk score, fraud flags)
```
