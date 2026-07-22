import os
import random
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """
    Canvas to add page numbers and a simple footer dynamically.
    """
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
        
        # Footer text
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 36, 20, footer_text)
        
        # Confidentiality notice
        notice = "CONFIDENTIAL - For Loan Application Purposes Only"
        self.drawString(36, 20, notice)
        
        # Draw a thin footer line
        self.setStrokeColor(colors.HexColor("#bdc3c7"))
        self.setLineWidth(0.5)
        self.line(36, 32, A4[0] - 36, 32)
        
        self.restoreState()


def render_payslip_pdf(data, output_path):
    """
    Renders a professional, realistic Australian Payslip PDF.
    """
    # 595.27 x 841.89 points (A4 size)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom colors
    primary_color = colors.HexColor("#2c3e50")   # Charcoal
    secondary_color = colors.HexColor("#34495e") # Slate
    accent_color = colors.HexColor("#16a085")    # Teal
    text_color = colors.HexColor("#2c3e50")
    light_bg = colors.HexColor("#ecf0f1")
    
    # Custom styles
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
    
    # 1. Header: Employer Details vs Doc Title
    employer_details = [
        Paragraph(f"<b>{data['company']['company_name']}</b>", body_bold),
        Paragraph(f"ABN: {data['company']['formatted_abn']}", body_style),
        Paragraph(f"ACN: {data['company']['formatted_acn']}", body_style),
        Paragraph(data['company']['address']['full_address'], body_style)
    ]
    
    title_section = [
        Paragraph("PAY SLIP", title_style),
        Paragraph(f"<b>Pay Date:</b> {data['payslip']['pay_date']}", body_style),
        Paragraph(f"<b>Pay Period:</b> {data['payslip']['period_start']} - {data['payslip']['period_end']}", body_style),
        Paragraph(f"<b>Pay Frequency:</b> {data['salary']['pay_frequency']}", body_style)
    ]
    
    header_table = Table(
        [[employer_details, title_section]],
        colWidths=[300, 223]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 20))
    
    # 2. Employee Details
    employee_info = [
        [
            Paragraph("<b>Employee Name:</b>", body_style), Paragraph(data['payslip']['employee_name'], body_style),
            Paragraph("<b>Super Fund:</b>", body_style), Paragraph("AustralianSuper", body_style)
        ],
        [
            Paragraph("<b>Job Title:</b>", body_style), Paragraph(data['salary']['job_title'], body_style),
            Paragraph("<b>Super Member ID:</b>", body_style), Paragraph(f"AS-{data['person']['passport_number'][2:]}", body_style)
        ],
        [
            Paragraph("<b>Employment Type:</b>", body_style), Paragraph("Permanent Full-Time", body_style),
            Paragraph("<b>Bank Account:</b>", body_style), Paragraph(f"BSB: {data['bank_statement']['bsb']} Acc: {data['bank_statement']['account_number']}", body_style)
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
    
    # 3. Earnings & YTD Breakdown Table
    payslip_data = data['payslip']
    sal = data['salary']
    
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
            Paragraph(f"${payslip_data['gross']:,.2f}", body_style),
            Paragraph(f"${payslip_data['ytd_gross']:,.2f}", body_style)
        ],
        [
            Paragraph("PAYG Tax Withheld", body_style),
            Paragraph("ATO Schedule", body_style),
            Paragraph(f"-${payslip_data['tax']:,.2f}", body_style),
            Paragraph(f"-${payslip_data['ytd_tax']:,.2f}", body_style)
        ]
    ]
    
    # If HECS applies, render it
    if payslip_data.get('hecs', 0) > 0:
        table_rows.append([
            Paragraph("HECS/HELP Repayment", body_style),
            Paragraph("ATO Schedule", body_style),
            Paragraph(f"-${payslip_data['hecs']:,.2f}", body_style),
            Paragraph(f"-${payslip_data.get('ytd_hecs', payslip_data['hecs']):,.2f}", body_style)
        ])
        
    # Superannuation (usually listed as employer contribution - not deducted from gross)
    table_rows.append([
        Paragraph("Super Guarantee (11.5%)", body_style),
        Paragraph("11.50%", body_style),
        Paragraph(f"${payslip_data['super']:,.2f}", body_style),
        Paragraph(f"${payslip_data['ytd_super']:,.2f}", body_style)
    ])
    
    # Calculate take home summary
    net_val = payslip_data['net']
    ytd_net_val = payslip_data['ytd_net']
    
    summary_row = [
        Paragraph("<b>Net Pay (Take Home)</b>", body_bold),
        Paragraph("", body_style),
        Paragraph(f"<b>${net_val:,.2f}</b>", body_bold),
        Paragraph(f"<b>${ytd_net_val:,.2f}</b>", body_bold)
    ]
    table_rows.append(summary_row)
    
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
    
    # 4. Message/Footer
    footer_p = Paragraph(
        "Thank you for your service. Please review your payslip details immediately. "
        "For any payroll discrepancies, contact the Human Resources and Finance department.", 
        body_style
    )
    story.append(footer_p)
    
    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)


def render_bank_statement_pdf(data, output_path):
    """
    Renders a professional, realistic Australian Bank Statement PDF.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Bank theme colors: Deep navy
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
    
    # 1. Header: Bank Logo vs Account Holder info
    bank_logo = [
        Paragraph("<b>SMARTFINN MUTUAL BANK</b>", title_style),
        Paragraph("SmartFinn Banking Corporation Ltd", body_style),
        Paragraph("AFSL & Australian Credit Licence 234567", body_style)
    ]
    
    holder_info = [
        Paragraph(f"<b>{data['person']['full_name']}</b>", body_bold),
        Paragraph(data['bank_statement']['address']['full_address'], body_style),
        Paragraph(f"BSB: <b>{data['bank_statement']['bsb']}</b>", body_style),
        Paragraph(f"Account No: <b>{data['bank_statement']['account_number']}</b>", body_style)
    ]
    
    header_table = Table(
        [[bank_logo, holder_info]],
        colWidths=[280, 243]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 15))
    
    # Horizontal line
    story.append(Table([[""]], colWidths=[523], rowHeights=[2], style=[('BACKGROUND', (0,0), (-1,-1), primary_navy)]))
    story.append(Spacer(1, 15))
    
    # 2. Statement Summary
    # Calculate debits and credits totals
    total_debits = sum(tx["debit"] for tx in data['bank_statement']['transactions'])
    total_credits = sum(tx["credit"] for tx in data['bank_statement']['transactions'])
    
    summary_data = [
        [
            Paragraph("<b>Opening Balance</b>", body_style),
            Paragraph("<b>Total Credits</b>", body_style),
            Paragraph("<b>Total Debits</b>", body_style),
            Paragraph("<b>Closing Balance</b>", body_style)
        ],
        [
            Paragraph(f"${data['bank_statement']['opening_balance']:,.2f}", body_bold),
            Paragraph(f"+${total_credits:,.2f}", body_bold),
            Paragraph(f"-${total_debits:,.2f}", body_bold),
            Paragraph(f"${data['bank_statement']['closing_balance']:,.2f}", body_bold)
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
    
    story.append(Paragraph(f"<b>Statement Period:</b> {data['bank_statement']['period_start']} - {data['bank_statement']['period_end']}", body_style))
    story.append(Spacer(1, 8))
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # 3. Transactions Table
    tx_headers = [
        Paragraph("Date", header_style),
        Paragraph("Description", header_style),
        Paragraph("Debit (-)", header_style),
        Paragraph("Credit (+)", header_style),
        Paragraph("Balance", header_style)
    ]
    
    tx_rows = [tx_headers]
    for tx in data['bank_statement']['transactions']:
        debit_str = f"-${tx['debit']:,.2f}" if tx['debit'] > 0 else ""
        credit_str = f"+${tx['credit']:,.2f}" if tx['credit'] > 0 else ""
        
        # Style highlighted items like salary or fees
        desc_text = tx['description']
        if "payroll" in desc_text.lower() or "salary" in desc_text.lower():
            desc_p = Paragraph(f"<b>{desc_text}</b>", body_bold)
        elif "dishonour" in desc_text.lower() or "nsf" in desc_text.lower():
            desc_p = Paragraph(f"<font color='red'><b>{desc_text}</b></font>", body_style)
        else:
            desc_p = Paragraph(desc_text, body_style)
            
        row = [
            Paragraph(tx['date'], body_style),
            desc_p,
            Paragraph(debit_str, body_style),
            Paragraph(credit_str, body_style),
            Paragraph(f"${tx['balance']:,.2f}", body_style)
        ]
        tx_rows.append(row)
        
    tx_table = Table(tx_rows, colWidths=[70, 210, 80, 80, 83])
    
    # Build alternating row background colors list
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


def render_employment_letter_pdf(data, output_path):
    """
    Renders a professional, realistic Australian Employment Verification Letter PDF.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    primary_color = colors.HexColor("#2d3748")
    text_color = colors.HexColor("#2d3748")
    
    body_style = ParagraphStyle(
        'LetterBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=text_color,
        leading=16,
        spaceAfter=12
    )
    
    bold_style = ParagraphStyle(
        'LetterBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    letterhead_company = ParagraphStyle(
        'LHCompany',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=colors.HexColor("#2c3e50"),
        spaceAfter=4
    )
    
    letterhead_sub = ParagraphStyle(
        'LHSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor("#7f8c8d")
    )

    story = []
    
    # 1. Letterhead
    letterhead_content = [
        Paragraph(data['company']['company_name'], letterhead_company),
        Paragraph(f"ABN: {data['company']['formatted_abn']} | Registered Office: {data['company']['address']['full_address']}", letterhead_sub),
        Paragraph(f"Contact: HR Department | Phone: 1300 {random.randint(100, 999)} {random.randint(100, 999)} | Email: hr@{data['company']['company_name'].lower().replace(' ', '').replace('pty', '').replace('ltd', '').replace('.', '')}.com.au", letterhead_sub)
    ]
    
    lh_table = Table([[letterhead_content]], colWidths=[487])
    lh_table.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor("#3498db")),
        ('PADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    
    story.append(lh_table)
    story.append(Spacer(1, 25))
    
    # 2. Date
    story.append(Paragraph(data['employment_letter']['letter_date'], body_style))
    story.append(Spacer(1, 10))
    
    # 3. Addressee
    story.append(Paragraph("<b>To Whom It May Concern,</b>", body_style))
    story.append(Spacer(1, 10))
    
    # 4. Body
    story.append(Paragraph(
        f"<b>RE: Employment Verification for {data['person']['full_name']}</b>", 
        bold_style
    ))
    story.append(Spacer(1, 5))
    
    # Determine the status text
    status_text = "permanent full-time"
    probation_text = "has successfully completed their probationary period." if data['employment_letter']['probation_status'] == "Not on probation" else "is currently on probation."
    
    body_p1 = (
        f"Please be advised that this letter serves to confirm that <b>{data['person']['full_name']}</b> is currently employed "
        f"with <b>{data['company']['company_name']}</b> in a <b>{status_text}</b> capacity."
    )
    story.append(Paragraph(body_p1, body_style))
    
    body_p2 = (
        f"<b>{data['person']['full_name']}</b> commenced employment with us on <b>{data['employment_letter']['start_date']}</b> "
        f"and holds the position of <b>{data['employment_letter']['job_title']}</b>. "
        f"As of the date of this letter, the employee {probation_text}"
    )
    story.append(Paragraph(body_p2, body_style))
    
    body_p3 = (
        f"Their remuneration package consists of a gross base annual salary of <b>${data['employment_letter']['salary']:,.2f} AUD</b>. "
        f"This salary is exclusive of the mandatory Superannuation Guarantee (SG) contributions, which are paid at the current statutory rate of 11.5%."
    )
    story.append(Paragraph(body_p3, body_style))
    
    body_p4 = (
        "Should you require any further information or verbal validation regarding this employment status, "
        "please do not hesitate to contact our Human Resources department during normal business hours."
    )
    story.append(Paragraph(body_p4, body_style))
    story.append(Spacer(1, 20))
    
    # 5. Sign-off
    sign_off = [
        Paragraph("Yours sincerely,", body_style),
        Spacer(1, 20),
    ]
    
    # Stylized script for signature
    sig_font_style = ParagraphStyle(
        'SigFont',
        parent=styles['Normal'],
        fontName='Times-Italic',
        fontSize=14,
        textColor=colors.HexColor("#2c3e50"),
        spaceAfter=2
    )
    
    if data['employment_letter']['signatory_name'] != "Missing Signature":
        sign_off.append(Paragraph(f"<i>{data['employment_letter']['signatory_name']}</i>", sig_font_style))
        sign_off.append(Paragraph(data['employment_letter']['signatory_name'], bold_style))
        if data['employment_letter']['signatory_title']:
            sign_off.append(Paragraph(data['employment_letter']['signatory_title'], body_style))
        else:
            sign_off.append(Paragraph("HR Representative", body_style))
    else:
        sign_off.append(Paragraph("<b>[UNSIGNED]</b>", ParagraphStyle('Unsigned', parent=body_style, textColor=colors.red)))
        
    story.append(KeepTogether(sign_off))
    
    doc.build(story, canvasmaker=NumberedCanvas)
