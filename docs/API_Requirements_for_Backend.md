# [DEPRECATED] Frontend API Requirements for the Backend

> [!CAUTION]
> **This document is deprecated.** It is based on an outdated database design.
> Refer to [API_Contract_v2_Demo_B.md](./API_Contract_v2_Demo_B.md), which aligns with the
> current Supabase schema and frontend implementation.

This document records the endpoints and request and response fields expected by the original
frontend implementation. It remains available only as a historical backend reference.

---

## 1. Authentication

### 1.1 User Login (`POST /api/auth/login`)

- **Scenario:** Submit the form on `/login`.
- **Request:**
  - `email` (string): Email address or username
  - `password` (string): Password
- **Response:**
  - `token` (string): JWT credential
  - `user` (object):
    - `id` (string): User ID
    - `name` (string): Name displayed in the dashboard header
    - `role` (string): Role such as `Compliance Officer` or `Admin`

---

## 2. Dashboard and Applications

### 2.1 Dashboard Metrics (`GET /api/dashboard/metrics`)

- **Scenario:** Populate the four summary cards on `/dashboard`.
- **Request:** No body; include the JWT in the request headers.
- **Response:**
  - `total_applications` (number): Total applications
  - `pending_review` (number): Applications awaiting review
  - `high_risk_alerts` (number): High-risk alerts
  - `approved_today` (number): Applications approved today

### 2.2 Application List (`GET /api/applications`)

- **Scenario:** Populate the dashboard summary table and full `/applications` management table.
- **Query parameters:**
  - `page` (number): Page number, default 1
  - `limit` (number): Rows per page
  - `search` (string): Partial match on applicant name or ID
  - `status` (string): Status such as `Pending`, `Approved`, or `Rejected`
  - `risk_level` (string): Risk-level filter
- **Response:**
  - `total_count` (number): Total matching rows
  - `data` (array of objects):
    - `id` (string): Case number, for example `APP-2026-001`
    - `applicant_name` (string): Applicant name
    - `loan_type` (string): Loan type such as `Purchase` or `Refinance`
    - `date_submitted` (string): Submission date in `YYYY-MM-DD` format
    - `status` (string): Current status
    - `risk_score` (number): Automated risk score from 0 to 100
    - `risk_level` (string): `High`, `Medium`, or `Low`

---

## 3. Application Creation

### 3.1 Create an Application and Upload Files (`POST /api/applications`)

- **Scenario:** Submit the applicant form and multiple files from `/applications/new`.
- **Request (`multipart/form-data`):**
  - `applicant_name` (string): Applicant name
  - `loan_type` (string): Loan type
  - `files` (array of files): PDF, JPG, or PNG documents
- **Response:**
  - `application_id` (string): Newly generated case number
  - `message` (string): `"Upload successful, OCR processing started"`

OCR may take time, so the backend should process files asynchronously. The frontend can navigate
back to the application list after receiving a successful upload response.

---

## 4. Review and Decisions

### 4.1 Application Details and Documents (`GET /api/applications/:id`)

- **Scenario:** Load case-level details and documents on `/application/[id]`.
- **Response:**
  - `id` (string): Case number
  - `applicant_name` (string): Applicant name
  - `status` (string): Overall status
  - `overall_risk_score` (number): Aggregate score
  - `documents` (array): Documents shown as tabs
    - `doc_id` (string): Document ID
    - `doc_type` (string): Category such as `Payslip` or `Passport`
    - `file_url` (string): Temporary URL for the PDF renderer

### 4.2 Extracted Data for a Document (`GET /api/documents/:doc_id/extracted-data`)

- **Scenario:** Update the form when a reviewer selects a document tab.
- **Response:**
  - `data_fields` (array of objects):
    - `key` (string): Stable field key such as `net_pay`
    - `label` (string): Display label such as `Net Pay`
    - `value` (string): Extracted OCR value
    - `confidence` (number): Confidence score; low values may be highlighted

### 4.3 Compliance Alerts (`GET /api/applications/:id/alerts`)

- **Scenario:** Populate the compliance-alert panel.
- **Response:**
  - `alerts` (array of objects):
    - `alert_id` (string)
    - `severity` (string): `High` or `Medium`
    - `title` (string): Short title such as `Income Discrepancy`
    - `description` (string): Detailed explanation
    - `status` (string): `Open` or `Resolved`

### 4.4 Save Reviewer Corrections (`PUT /api/documents/:doc_id/extracted-data`)

- **Scenario:** Save fields changed by the reviewer through `Save Corrections`.
- **Request (JSON):**
  - `corrected_fields`: Key-value object such as `{ net_pay: "$7,200.00" }`
- **Response:**
  - `message` (string): `"Updated successfully"`

### 4.5 Final Decision (`POST /api/applications/:id/decision`)

- **Scenario:** Confirm an Approve or Reject action.
- **Request (JSON):**
  - `decision` (string): `Approve` or `Reject`
  - `reason` (string): Reviewer's reason or notes
- **Response:**
  - `message` (string): `"Decision recorded successfully"`
