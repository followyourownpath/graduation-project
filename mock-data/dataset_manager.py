import os
import json
import shutil
import random
from pathlib import Path

def create_dataset_directories(base_dir):
    """
    Creates train, val, and test subdirectories.
    """
    base_path = Path(base_dir)
    for split in ['train', 'val', 'test']:
        split_path = base_path / split
        split_path.mkdir(parents=True, exist_ok=True)
    return base_path

def generate_ocr_json(app_record):
    """
    Simulates the Azure Document Intelligence (OCR) response for the application's documents.
    Contains extracted fields, confidence scores, and structure.
    """
    ocr_data = {
        "application_id": app_record["application_id"],
        "documents": []
    }
    
    # 1. ID Document OCR
    ocr_data["documents"].append({
        "document_type": "Identification Document",
        "filename": "id.pdf",
        "extracted_fields": {
            "full_legal_name": {
                "value": app_record["person"]["full_name"],
                "confidence": round(random.uniform(0.95, 0.99), 4)
            },
            "date_of_birth": {
                "value": app_record["person"]["dob"],
                "confidence": round(random.uniform(0.96, 0.99), 4)
            },
            "document_number": {
                "value": app_record["person"]["passport_number"],
                "confidence": round(random.uniform(0.98, 0.99), 4)
            },
            "expiry_date": {
                "value": app_record["person"]["passport_expiry"],
                "confidence": round(random.uniform(0.95, 0.99), 4)
            },
            "residential_address": {
                "value": app_record["person"]["address"]["full_address"],
                "confidence": round(random.uniform(0.90, 0.97), 4)
            }
        }
    })
    
    # 2. Payslip OCR (might contain injected discrepancies)
    payslip_ocr = {
        "document_type": "Payslip",
        "filename": "payslip.pdf",
        "extracted_fields": {
            "employee_name": {
                "value": app_record["payslip"]["employee_name"],
                "confidence": round(random.uniform(0.93, 0.99), 4)
            },
            "employer_name": {
                "value": app_record["company"]["company_name"],
                "confidence": round(random.uniform(0.94, 0.99), 4)
            },
            "abn": {
                "value": app_record["company"]["formatted_abn"],
                "confidence": round(random.uniform(0.97, 0.99), 4)
            },
            "pay_date": {
                "value": app_record["payslip"]["pay_date"],
                "confidence": round(random.uniform(0.95, 0.99), 4)
            },
            "pay_period": {
                "value": f"{app_record['payslip']['period_start']} - {app_record['payslip']['period_end']}",
                "confidence": round(random.uniform(0.91, 0.98), 4)
            },
            "gross_income": {
                "value": f"${app_record['payslip']['gross']:,.2f}",
                "confidence": round(random.uniform(0.95, 0.99), 4)
            },
            "net_income": {
                "value": f"${app_record['payslip']['net']:,.2f}",
                "confidence": round(random.uniform(0.95, 0.99), 4)
            },
            "tax_withheld": {
                "value": f"${app_record['payslip']['tax']:,.2f}",
                "confidence": round(random.uniform(0.94, 0.99), 4)
            },
            "superannuation": {
                "value": f"${app_record['payslip']['super']:,.2f}",
                "confidence": round(random.uniform(0.92, 0.98), 4)
            },
            "ytd_gross_income": {
                "value": f"${app_record['payslip']['ytd_gross']:,.2f}",
                "confidence": round(random.uniform(0.93, 0.99), 4)
            }
        }
    }
    # Handle optional HECS
    if app_record["payslip"].get("hecs", 0) > 0:
        payslip_ocr["extracted_fields"]["hecs_repayment"] = {
            "value": f"${app_record['payslip']['hecs']:,.2f}",
            "confidence": round(random.uniform(0.92, 0.98), 4)
        }
    ocr_data["documents"].append(payslip_ocr)
    
    # 3. Employment Letter OCR (might contain injected discrepancies)
    el_ocr = {
        "document_type": "Employment Letter",
        "filename": "employment_letter.pdf",
        "extracted_fields": {
            "employee_full_name": {
                "value": app_record["person"]["full_name"], # Let's assume OCR gets full legal name
                "confidence": round(random.uniform(0.92, 0.99), 4)
            },
            "employer_name": {
                "value": app_record["company"]["company_name"],
                "confidence": round(random.uniform(0.95, 0.99), 4)
            },
            "abn": {
                "value": app_record["company"]["formatted_abn"],
                "confidence": round(random.uniform(0.96, 0.99), 4)
            },
            "job_title": {
                "value": app_record["employment_letter"]["job_title"],
                "confidence": round(random.uniform(0.90, 0.97), 4)
            },
            "employment_type": {
                "value": "Permanent full-time",
                "confidence": round(random.uniform(0.92, 0.98), 4)
            },
            "start_date": {
                "value": app_record["employment_letter"]["start_date"],
                "confidence": round(random.uniform(0.94, 0.99), 4)
            },
            "gross_annual_salary": {
                "value": f"${app_record['employment_letter']['salary']:,.2f} p.a.",
                "confidence": round(random.uniform(0.95, 0.99), 4)
            },
            "letter_date": {
                "value": app_record["employment_letter"]["letter_date"],
                "confidence": round(random.uniform(0.93, 0.98), 4)
            },
            "probation_status": {
                "value": app_record["employment_letter"]["probation_status"],
                "confidence": round(random.uniform(0.88, 0.96), 4)
            },
            "signatory_name": {
                "value": app_record["employment_letter"]["signatory_name"],
                "confidence": round(random.uniform(0.85, 0.95), 4)
            },
            "signatory_title": {
                "value": app_record["employment_letter"]["signatory_title"],
                "confidence": round(random.uniform(0.85, 0.95), 4)
            }
        }
    }
    ocr_data["documents"].append(el_ocr)
    
    # 4. Bank Statement OCR (might contain injected discrepancies)
    # Collect salary credit entries from transactions
    salary_entries = []
    for tx in app_record["bank_statement"]["transactions"]:
        if "payroll" in tx["description"].lower() or "salary" in tx["description"].lower():
            salary_entries.append({
                "date": tx["date"],
                "description": tx["description"],
                "amount": f"${tx['credit']:,.2f}"
            })
            
    bank_ocr = {
        "document_type": "Bank Statement",
        "filename": "bank_statement.pdf",
        "extracted_fields": {
            "account_holder_name": {
                "value": app_record["person"]["full_name"],
                "confidence": round(random.uniform(0.94, 0.99), 4)
            },
            "bsb": {
                "value": app_record["bank_statement"]["bsb"],
                "confidence": round(random.uniform(0.97, 0.99), 4)
            },
            "account_number": {
                "value": app_record["bank_statement"]["account_number"],
                "confidence": round(random.uniform(0.97, 0.99), 4)
            },
            "statement_period": {
                "value": f"{app_record['bank_statement']['period_start']} - {app_record['bank_statement']['period_end']}",
                "confidence": round(random.uniform(0.92, 0.98), 4)
            },
            "opening_balance": {
                "value": f"${app_record['bank_statement']['opening_balance']:,.2f}",
                "confidence": round(random.uniform(0.95, 0.99), 4)
            },
            "closing_balance": {
                "value": f"${app_record['bank_statement']['closing_balance']:,.2f}",
                "confidence": round(random.uniform(0.95, 0.99), 4)
            }
        },
        "salary_credits": salary_entries
    }
    
    # Add dishonour fees and NSF checks if any exist in transactions
    dishonour_fees = []
    for tx in app_record["bank_statement"]["transactions"]:
        if "dishonour" in tx["description"].lower() or "nsf" in tx["description"].lower():
            dishonour_fees.append({
                "date": tx["date"],
                "description": tx["description"],
                "fee_amount": f"${tx['debit']:,.2f}"
            })
    if dishonour_fees:
        bank_ocr["dishonour_fees"] = dishonour_fees
        
    ocr_data["documents"].append(bank_ocr)
    
    return ocr_data


def save_application_data(base_path, app_record, split, render_pdfs=True):
    """
    Saves PDFs, OCR data, and details for a single application.
    """
    app_id = app_record["application_id"]
    app_dir = base_path / split / f"app_{app_id}"
    app_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Save simulated OCR JSON
    ocr_content = generate_ocr_json(app_record)
    ocr_file = app_dir / "ocr.json"
    with open(ocr_file, 'w', encoding='utf-8') as f:
        json.dump(ocr_content, f, indent=2, ensure_ascii=False)
        
    # 2. Render PDFs if requested
    if render_pdfs:
        import document_renderer
        
        # Paths
        payslip_path = str(app_dir / "payslip.pdf")
        bank_stmt_path = str(app_dir / "bank_statement.pdf")
        emp_letter_path = str(app_dir / "employment_letter.pdf")
        id_path = str(app_dir / "id.pdf")
        
        # Render Payslip
        document_renderer.render_payslip_pdf(app_record, payslip_path)
        
        # Render Bank Statement
        document_renderer.render_bank_statement_pdf(app_record, bank_stmt_path)
        
        # Render Employment Letter
        document_renderer.render_employment_letter_pdf(app_record, emp_letter_path)
        
        # Render a simple ID Document PDF (Mock Passport / Licence card layout)
        render_mock_id_pdf(app_record, id_path)

def render_mock_id_pdf(data, output_path):
    """
    Generates a simple, clean Identification Document PDF using reportlab.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    primary_color = colors.HexColor("#1b3a4b")
    text_color = colors.HexColor("#2d3748")
    
    title_style = ParagraphStyle(
        'IDTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=primary_color,
        spaceAfter=15
    )
    
    body_style = ParagraphStyle(
        'IDBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=text_color,
        leading=14,
        spaceAfter=8
    )
    
    story = []
    
    # Header
    story.append(Paragraph("AUSTRALIAN PASSPORT / IDENTITY DOCUMENT VERIFICATION", title_style))
    story.append(Table([[""]], colWidths=[487], rowHeights=[2], style=[('BACKGROUND', (0,0), (-1,-1), primary_color)]))
    story.append(Spacer(1, 20))
    
    # ID Details Table
    id_info = [
        [Paragraph("<b>Document Type:</b>", body_style), Paragraph("Passport", body_style)],
        [Paragraph("<b>Full Legal Name:</b>", body_style), Paragraph(data['person']['full_name'], body_style)],
        [Paragraph("<b>Date of Birth:</b>", body_style), Paragraph(data['person']['dob'], body_style)],
        [Paragraph("<b>Document Number:</b>", body_style), Paragraph(data['person']['passport_number'], body_style)],
        [Paragraph("<b>Expiry Date:</b>", body_style), Paragraph(data['person']['passport_expiry'], body_style)],
        [Paragraph("<b>Residential Address:</b>", body_style), Paragraph(data['person']['address']['full_address'], body_style)],
        [Paragraph("<b>Driver Licence Link:</b>", body_style), Paragraph(f"Licence No: {data['person']['driver_licence']} (Expiry: {data['person']['licence_expiry']})", body_style)]
    ]
    
    id_table = Table(id_info, colWidths=[150, 337])
    id_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8f9fa")),
        ('PADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e0")),
    ]))
    
    story.append(id_table)
    story.append(Spacer(1, 30))
    
    # Disclaimer
    story.append(Paragraph(
        "<i>Notice: This is a verified electronic replica of the applicant's identification document. "
        "Generated strictly for sandbox verification and compliance testing under regulatory mock frameworks.</i>",
        ParagraphStyle('IDDisclaimer', parent=body_style, fontSize=8, textColor=colors.HexColor("#7f8c8d"))
    ))
    
    doc.build(story)


def split_dataset(num_apps, train_ratio=0.7, val_ratio=0.2):
    """
    Calculates splits based on ratio.
    Returns list of split assignments for each index.
    """
    splits = []
    for i in range(num_apps):
        r = random.random()
        if r < train_ratio:
            splits.append('train')
        elif r < train_ratio + val_ratio:
            splits.append('val')
        else:
            splits.append('test')
    return splits
