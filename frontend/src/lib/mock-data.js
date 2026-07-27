export const mockSubmissions = [
  { id: 'sub-2026-001', local_application_id: 'app-local-901', crm_application_id: 'MERC-88231', source_channel: 'crm', customer_name: 'Alice Smith', loan_type: 'purchase', submission_status: 'in_review', extraction_status: 'completed', created_at: '2026-06-25T10:00:00Z', risk_level: 'High', overall_risk_score: 85 },
  { id: 'sub-2026-002', local_application_id: 'app-local-902', crm_application_id: null, source_channel: 'manual', customer_name: 'Bob Johnson', loan_type: 'refinance', submission_status: 'approved', extraction_status: 'completed', created_at: '2026-06-24T14:30:00Z', risk_level: 'Low', overall_risk_score: 12 },
  { id: 'sub-2026-003', local_application_id: 'app-local-903', crm_application_id: 'MERC-88245', source_channel: 'crm', customer_name: 'Charlie Davis', loan_type: 'purchase', submission_status: 'in_review', extraction_status: 'completed', created_at: '2026-06-24T09:15:00Z', risk_level: 'Medium', overall_risk_score: 45 },
  { id: 'sub-2026-004', local_application_id: 'app-local-904', crm_application_id: null, source_channel: 'manual', customer_name: 'Diana Prince', loan_type: 'purchase', submission_status: 'in_review', extraction_status: 'processing', created_at: '2026-06-23T16:45:00Z', risk_level: 'Low', overall_risk_score: 22 },
  { id: 'sub-2026-005', local_application_id: 'app-local-905', crm_application_id: 'MERC-88290', source_channel: 'crm', customer_name: 'Evan Wright', loan_type: 'refinance', submission_status: 'rejected', extraction_status: 'completed', created_at: '2026-06-22T11:20:00Z', risk_level: 'High', overall_risk_score: 92 },
];

export const mockDocuments = {
  'sub-2026-001': [
    { doc_id: 'doc-001', original_file_name: 'Alice_Payslip_Aug.pdf', document_type: 'payslip', processing_status: 'completed', storage_uri: '/mock-pdfs/payslip.pdf' },
    { doc_id: 'doc-002', original_file_name: 'Alice_Passport.pdf', document_type: 'id_100', processing_status: 'completed', storage_uri: '/mock-pdfs/passport.pdf' },
    { doc_id: 'doc-003', original_file_name: 'Alice_Bank_Statement.pdf', document_type: 'bank_statement_3m', processing_status: 'completed', storage_uri: '/mock-pdfs/bank_statement.pdf' },
  ],
  'sub-2026-004': [
    { doc_id: 'doc-004', original_file_name: 'Diana_Payslip.pdf', document_type: 'payslip', processing_status: 'processing', storage_uri: '/mock-pdfs/payslip.pdf' },
  ]
};

export const mockExtractedData = {
  'doc-001': {
    doc_id: 'doc-001',
    document_type: 'payslip',
    fields: [
      { field_id: 'f-01', section_name: 'Personal Details', field_key: 'employee_name', field_label: 'Employee Name', raw_value: 'Alice Smith', confidence: 0.98, review_status: 'pending' },
      { field_id: 'f-02', section_name: 'Employment', field_key: 'employer_name', field_label: 'Employer Name', raw_value: 'Tech Corp Inc.', confidence: 0.95, review_status: 'pending' },
      { field_id: 'f-03', section_name: 'Income', field_key: 'net_income', field_label: 'Net Pay', raw_value: '$7,200.00', confidence: 0.75, review_status: 'pending' },
      { field_id: 'f-04', section_name: 'Income', field_key: 'pay_period', field_label: 'Pay Period', raw_value: 'Aug 01 - Aug 31, 2023', confidence: 0.92, review_status: 'pending' },
    ]
  },
  'doc-002': {
    doc_id: 'doc-002',
    document_type: 'id_100',
    fields: [
      { field_id: 'f-05', section_name: 'Identity', field_key: 'full_name', field_label: 'Full Name', raw_value: 'Alice Smith', confidence: 0.99, review_status: 'pending' },
      { field_id: 'f-06', section_name: 'Identity', field_key: 'document_number', field_label: 'Document Number', raw_value: 'P12345678', confidence: 0.97, review_status: 'pending' },
      { field_id: 'f-07', section_name: 'Identity', field_key: 'dob', field_label: 'Date of Birth', raw_value: '15/05/1990', confidence: 0.96, review_status: 'pending' },
    ]
  },
  'doc-003': {
    doc_id: 'doc-003',
    document_type: 'bank_statement_3m',
    fields: [
      { field_id: 'f-08', section_name: 'Account', field_key: 'account_name', field_label: 'Account Name', raw_value: 'Alice Smith', confidence: 0.95, review_status: 'pending' },
      { field_id: 'f-09', section_name: 'Account', field_key: 'bsb', field_label: 'BSB', raw_value: '062-000', confidence: 0.99, review_status: 'pending' },
      { field_id: 'f-10', section_name: 'Balances', field_key: 'closing_balance', field_label: 'Closing Balance', raw_value: '$15,450.00', confidence: 0.89, review_status: 'pending' },
      { field_id: 'f-11', section_name: 'Transactions', field_key: 'salary_credits', field_label: 'Salary Credits (Total)', raw_value: '$7,200.00', confidence: 0.82, review_status: 'pending' },
    ]
  }
};
