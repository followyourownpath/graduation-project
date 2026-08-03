import os
import sys
import fitz
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#7f8c8d"))
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 36, 20, footer_text)
        notice = "CONFIDENTIAL - For Loan Application Purposes Only"
        self.drawString(36, 20, notice)
        self.setStrokeColor(colors.HexColor("#bdc3c7"))
        self.setLineWidth(0.5)
        self.line(36, 32, A4[0] - 36, 32)
        self.restoreState()


def build_payslip(output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=54
    )
    styles = getSampleStyleSheet()
    primary_color = colors.HexColor("#2c3e50")
    text_color = colors.HexColor("#2c3e50")
    light_bg = colors.HexColor("#ecf0f1")
    accent_color = colors.HexColor("#16a085")

    title_style = ParagraphStyle(
        'PayslipTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=primary_color,
        spaceAfter=15
    )

    body_style = ParagraphStyle(
        'PayslipBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9,
        textColor=text_color,
        leading=12
    )

    body_bold = ParagraphStyle(
        'PayslipBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    header_style = ParagraphStyle(
        'PayslipHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=colors.white
    )

    story = []

    employer_details = [
        Paragraph("<b>Tech Solutions Pty Ltd</b>", body_bold),
        Paragraph("ABN: 65 435 933 731", body_style),
        Paragraph("ACN: 562 903 575", body_style),
        Paragraph("1 George St, Sydney NSW 2000", body_style)
    ]

    title_section = [
        Paragraph("PAY SLIP", title_style),
        Paragraph("<b>Pay Date:</b> 18/06/2026", body_style),
        Paragraph("<b>Pay Period:</b> 04/06/2026 - 17/06/2026", body_style),
        Paragraph("<b>Pay Frequency:</b> Fortnightly", body_style)
    ]

    header_table = Table([[employer_details, title_section]], colWidths=[300, 223])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 20))

    employee_info = [
        [
            Paragraph("<b>Employee Name:</b>", body_style), Paragraph("Junhong Zhong", body_style),
            Paragraph("<b>Super Fund:</b>", body_style), Paragraph("AustralianSuper", body_style)
        ],
        [
            Paragraph("<b>Job Title:</b>", body_style), Paragraph("Software Engineer", body_style),
            Paragraph("<b>Super Member ID:</b>", body_style), Paragraph("AS-9450643", body_style)
        ],
        [
            Paragraph("<b>Employment Type:</b>", body_style), Paragraph("Permanent Full-Time", body_style),
            Paragraph("<b>Bank Account:</b>", body_style), Paragraph("BSB: 062-235 Acc: 10473829", body_style)
        ]
    ]

    emp_table = Table(employee_info, colWidths=[110, 150, 110, 153])
    emp_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,-1), light_bg),
        ('PADDING', (0,0), (-1,-1), 6),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#bdc3c7")),
        ('INNERGRID', (0,0), (-1,-1), 0.25, colors.HexColor("#dcdde1")),
    ]))

    story.append(emp_table)
    story.append(Spacer(1, 20))

    table_headers = [
        Paragraph("Description", header_style),
        Paragraph("Hours/Rate", header_style),
        Paragraph("Current Amount", header_style),
        Paragraph("YTD Amount", header_style)
    ]

    table_rows = [
        table_headers,
        [
            Paragraph("Ordinary Earnings", body_style),
            Paragraph("Salaried", body_style),
            Paragraph("$4,583.33", body_style),
            Paragraph("$119,166.58", body_style)
        ],
        [
            Paragraph("PAYG Tax Withheld", body_style),
            Paragraph("ATO Schedule", body_style),
            Paragraph("-$916.67", body_style),
            Paragraph("-$23,833.42", body_style)
        ],
        [
            Paragraph("Super Guarantee (11.5%)", body_style),
            Paragraph("11.50%", body_style),
            Paragraph("$527.08", body_style),
            Paragraph("$13,704.16", body_style)
        ],
        [
            Paragraph("<b>Net Pay (Take Home)</b>", body_bold),
            Paragraph("", body_style),
            Paragraph("<b>$3,666.66</b>", body_bold),
            Paragraph("<b>$95,333.16</b>", body_bold)
        ]
    ]

    breakdown_table = Table(table_rows, colWidths=[180, 100, 120, 123])
    breakdown_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor("#bdc3c7")),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#dff9fb")),
        ('BOX', (0,-1), (-1,-1), 1, accent_color),
    ]))

    story.append(breakdown_table)
    story.append(Spacer(1, 30))

    footer_p = Paragraph(
        "Thank you for your service. Please review your payslip details immediately. "
        "For any payroll discrepancies, contact the Human Resources and Finance department.", 
        body_style
    )
    story.append(footer_p)

    doc.build(story, canvasmaker=NumberedCanvas)
    print("Generated payslip.pdf successfully.")


def build_bank_statement(output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=54
    )
    styles = getSampleStyleSheet()
    primary_navy = colors.HexColor("#1b3a4b")
    text_color = colors.HexColor("#2d3748")
    border_color = colors.HexColor("#e2e8f0")
    light_bg = colors.HexColor("#f7fafc")

    title_style = ParagraphStyle(
        'BankTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=primary_navy,
        spaceAfter=5
    )

    body_style = ParagraphStyle(
        'BankBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=8,
        textColor=text_color,
        leading=11
    )

    body_bold = ParagraphStyle(
        'BankBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    header_style = ParagraphStyle(
        'BankTableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.white
    )

    story = []

    bank_logo = [
        Paragraph("<b>SMARTFINN MUTUAL BANK</b>", title_style),
        Paragraph("SmartFinn Banking Corporation Ltd", body_style),
        Paragraph("AFSL & Australian Credit Licence 234567", body_style)
    ]

    holder_info = [
        Paragraph("<b>Junhong Zhong</b>", body_bold),
        Paragraph("150 Todman Ave, Kensington NSW 2033", body_style),
        Paragraph("BSB: <b>062-235</b>", body_style),
        Paragraph("Account No: <b>10473829</b>", body_style)
    ]

    header_table = Table([[bank_logo, holder_info]], colWidths=[280, 243])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 0),
    ]))

    story.append(header_table)
    story.append(Spacer(1, 15))

    story.append(Table([[""]], colWidths=[523], rowHeights=[2], style=[('BACKGROUND', (0,0), (-1,-1), primary_navy)]))
    story.append(Spacer(1, 15))

    summary_data = [
        [
            Paragraph("<b>Opening Balance</b>", body_style),
            Paragraph("<b>Total Credits</b>", body_style),
            Paragraph("<b>Total Debits</b>", body_style),
            Paragraph("<b>Closing Balance</b>", body_style)
        ],
        [
            Paragraph("$12,180.00", body_bold),
            Paragraph("+$25,666.62", body_bold),
            Paragraph("-$22,426.62", body_bold),
            Paragraph("$15,420.00", body_bold)
        ]
    ]
    summary_table = Table(summary_data, colWidths=[130, 130, 130, 133])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), light_bg),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
    ]))

    story.append(Paragraph("<b>Statement Period:</b> 01/04/2026 - 30/06/2026", body_style))
    story.append(Spacer(1, 8))
    story.append(summary_table)
    story.append(Spacer(1, 20))

    tx_headers = [
        Paragraph("Date", header_style),
        Paragraph("Description", header_style),
        Paragraph("Debit (-)", header_style),
        Paragraph("Credit (+)", header_style),
        Paragraph("Balance", header_style)
    ]

    raw_txs = [
        # April 2026
        ('01/04/2026', 'RENT DEBIT REAL ESTATE MGT', 2341.87, 0),
        ('02/04/2026', 'DEBIT CARD COLES SUPERMARKETS KENSINGTON', 145.20, 0),
        ('03/04/2026', 'POS DEBIT STARBUCKS SYDNEY', 12.80, 0),
        ('05/04/2026', 'NETFLIX.COM INTERNET SUB', 22.99, 0),
        ('07/04/2026', 'DIRECT DEP TECH SOLUTIONS PTY LTD PAYROLL', 0, 3666.66),
        ('08/04/2026', 'DEBIT CARD ALDI STORES KENSINGTON', 164.30, 0),
        ('10/04/2026', 'TELSTRA BILL PAYMENT DIRECT DEBIT', 119.90, 0),
        ('11/04/2026', 'TERM DEPOSIT INVESTMENT TRANSFER', 5000.00, 0),
        ('12/04/2026', 'POS DEBIT UBER EATS SYDNEY', 44.50, 0),
        ('14/04/2026', 'DEBIT CARD WOOLWORTHS MOORE PARK', 182.60, 0),
        ('15/04/2026', 'ATM WITHDRAWAL ATM-FEE $2.50', 200.00, 0),
        ('17/04/2026', 'CREDIT CARD REPAYMENT AMEX', 450.00, 0),
        ('18/04/2026', 'DEBIT CARD CHEMIST WAREHOUSE', 65.20, 0),
        ('20/04/2026', 'ORIGIN ENERGY ELECTRICITY BILL', 285.80, 0),
        ('21/04/2026', 'DIRECT DEP TECH SOLUTIONS PTY LTD PAYROLL', 0, 3666.66),
        ('22/04/2026', 'DEBIT CARD COLES SUPERMARKETS', 155.40, 0),
        ('25/04/2026', 'POS DEBIT JB HI-FI SYDNEY', 229.00, 0),
        ('28/04/2026', 'POS DEBIT UBER EATS SYDNEY', 58.90, 0),
        ('30/04/2026', 'SPOTIFY AUSTRALIA SUB', 18.99, 0),

        # May 2026
        ('01/05/2026', 'RENT DEBIT REAL ESTATE MGT', 2341.87, 0),
        ('03/05/2026', 'DEBIT CARD WOOLWORTHS SYDNEY', 198.40, 0),
        ('05/05/2026', 'DIRECT DEP TECH SOLUTIONS PTY LTD PAYROLL', 0, 3666.66),
        ('07/05/2026', 'DEBIT CARD ALDI STORES', 135.20, 0),
        ('10/05/2026', 'TELSTRA BILL PAYMENT DIRECT DEBIT', 119.90, 0),
        ('12/05/2026', 'SYDNEY WATER BILL DIRECT DEBIT', 216.30, 0),
        ('14/05/2026', 'TERM DEPOSIT INVESTMENT TRANSFER', 4749.13, 0),
        ('15/05/2026', 'ATM WITHDRAWAL ATM-FEE $2.50', 150.00, 0),
        ('17/05/2026', 'CREDIT CARD REPAYMENT ANZ', 520.00, 0),
        ('18/05/2026', 'DEBIT CARD COLES SUPERMARKETS', 172.50, 0),
        ('19/05/2026', 'DIRECT DEP TECH SOLUTIONS PTY LTD PAYROLL', 0, 3666.66),
        ('21/05/2026', 'POS DEBIT STARBUCKS SYDNEY', 18.20, 0),
        ('24/05/2026', 'DEBIT CARD WOOLWORTHS KENSINGTON', 198.60, 0),
        ('27/05/2026', 'ORIGIN ENERGY GAS BILL', 142.40, 0),
        ('30/05/2026', 'POS DEBIT UBER EATS SYDNEY', 62.10, 0),

        # June 2026
        ('01/06/2026', 'RENT DEBIT REAL ESTATE MGT', 2341.87, 0),
        ('02/06/2026', 'DIRECT DEP TECH SOLUTIONS PTY LTD PAYROLL', 0, 3666.66),
        ('04/06/2026', 'DEBIT CARD COLES SUPERMARKETS', 185.80, 0),
        ('08/06/2026', 'DEBIT CARD ALDI STORES KENSINGTON', 128.30, 0),
        ('10/06/2026', 'TELSTRA BILL PAYMENT DIRECT DEBIT', 119.90, 0),
        ('12/06/2026', 'MEDIBANK PRIVATE INSURANCE', 235.00, 0),
        ('14/06/2026', 'POS DEBIT UBER EATS SYDNEY', 41.50, 0),
        ('16/06/2026', 'DIRECT DEP TECH SOLUTIONS PTY LTD PAYROLL', 0, 3666.66),
        ('18/06/2026', 'DEBIT CARD WOOLWORTHS SYDNEY', 192.40, 0),
        ('22/06/2026', 'ORIGIN ENERGY ELECTRICITY BILL', 275.60, 0),
        ('25/06/2026', 'DEBIT CARD COLES SUPERMARKETS', 184.20, 0),
        ('28/06/2026', 'ATM WITHDRAWAL ATM-FEE $2.50', 200.00, 0),
        ('30/06/2026', 'DIRECT DEP TECH SOLUTIONS PTY LTD PAYROLL', 0, 3666.66),
    ]

    bal = 12180.00
    tx_rows = [tx_headers]
    for date_str, desc, debit, credit in raw_txs:
        bal = round(bal - debit + credit, 2)
        debit_str = f"-${debit:,.2f}" if debit > 0 else ""
        credit_str = f"+${credit:,.2f}" if credit > 0 else ""
        if credit > 0:
            desc_p = Paragraph(f"<b>{desc}</b>", body_bold)
        else:
            desc_p = Paragraph(desc, body_style)

        row = [
            Paragraph(date_str, body_style),
            desc_p,
            Paragraph(debit_str, body_style),
            Paragraph(credit_str, body_style),
            Paragraph(f"${bal:,.2f}", body_style)
        ]
        tx_rows.append(row)

    tx_table = Table(tx_rows, colWidths=[70, 210, 80, 80, 83])
    ts = [
        ('BACKGROUND', (0,0), (-1,0), primary_navy),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 5),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
    ]
    for r in range(1, len(tx_rows)):
        if r % 2 == 0:
            ts.append(('BACKGROUND', (0,r), (-1,r), light_bg))

    tx_table.setStyle(TableStyle(ts))
    story.append(tx_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print("Generated long bank_statement.pdf successfully.")


def build_noa(output_path):
    template_path = os.path.join(os.path.dirname(__file__), "goldenData", "Mock_Notice_of_Assessment.pdf")
    doc = fitz.open(template_path)
    page = doc[0]

    # White out original name & address
    rect = fitz.Rect(35, 70, 320, 135)
    page.draw_rect(rect, color=(1,1,1), fill=(1,1,1))

    # Insert updated fields matching FFS and ID
    font_size = 10.0
    page.insert_text((42, 85), "MR JUNHONG ZHONG", fontname="helv", fontsize=font_size, color=(0,0,0))
    page.insert_text((42, 100), "150 TODMAN AVE", fontname="helv", fontsize=font_size, color=(0,0,0))
    page.insert_text((42, 115), "KENSINGTON NSW 2033", fontname="helv", fontsize=font_size, color=(0,0,0))

    doc.save(output_path)
    print("Updated Mock_Notice_of_Assessment.pdf from template successfully.")


if __name__ == "__main__":
    target_dir = os.path.join(os.path.dirname(__file__), "goldenData_zero_risk")
    os.makedirs(target_dir, exist_ok=True)
    build_payslip(os.path.join(target_dir, "payslip.pdf"))
    build_bank_statement(os.path.join(target_dir, "bank_statement.pdf"))
    build_noa(os.path.join(target_dir, "Mock_Notice_of_Assessment.pdf"))
