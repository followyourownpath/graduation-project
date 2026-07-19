# SmartFinn API Contract (v2 - Demo B)

> **Status:** Draft / Ready for Backend Implementation
> **Target:** Demo B Minimum Viable Flow
> **Note to Backend (Huaiyu):** The frontend has been refactored to expect exactly these endpoints and JSON shapes. The schema aligns with Shuyang's `supabase` branch database design.

---

## 1. Create Submission (Upload)

**Endpoint:** `POST /api/submissions`
**Content-Type:** `multipart/form-data`

### Request Payload (FormData)
| Field | Type | Description |
|-------|------|-------------|
| `customer_name` | string | Full name of applicant |
| `loan_type` | string | e.g. "purchase", "refinance" |
| `files` | File[] | Array of uploaded binary files |
| `document_types` | string[] | Array of document categories (e.g. "payslip", "id_100"). Order must match the `files` array. |

### Expected Response (201 Created)
```json
{
  "submission_id": "sub-2026-001",
  "message": "Upload successful, OCR processing started"
}
```
*Note: Backend must immediately return this response and trigger Azure OCR processing asynchronously.*

---

## 2. Get Submission Details & Documents

**Endpoint:** `GET /api/submissions/:id`

### Expected Response (200 OK)
```json
{
  "id": "sub-2026-001",
  "customer_name": "Alice Smith",
  "loan_type": "purchase",
  "submission_status": "in_review",
  "extraction_status": "processing",
  "created_at": "2026-06-25T10:00:00Z",
  "risk_level": "High",
  "overall_risk_score": 85,
  "documents": [
    {
      "doc_id": "doc-001",
      "original_file_name": "Alice_Payslip.pdf",
      "document_type": "payslip",
      "processing_status": "completed", 
      "storage_uri": "https://supabase-bucket-url/payslip.pdf"
    },
    {
      "doc_id": "doc-004",
      "original_file_name": "Diana_Payslip.pdf",
      "document_type": "payslip",
      "processing_status": "processing",
      "storage_uri": ""
    }
  ]
}
```
*Note: The frontend polls this endpoint every 3 seconds if any document has `processing_status: "processing"`. Backend needs to update this status to `"completed"` once OCR is done.*

---

## 3. Get Extracted OCR Data (Per Document)

**Endpoint:** `GET /api/documents/:doc_id/extracted-data`

### Expected Response (200 OK)
```json
{
  "doc_id": "doc-001",
  "document_type": "payslip",
  "fields": [
    { 
      "field_id": "f-01", 
      "section_name": "Personal Details", 
      "field_key": "employee_name", 
      "field_label": "Employee Name", 
      "raw_value": "Alice Smith", 
      "confidence": 0.98, 
      "review_status": "pending" 
    },
    { 
      "field_id": "f-03", 
      "section_name": "Income", 
      "field_key": "net_income", 
      "field_label": "Net Pay", 
      "raw_value": "$7,200.00", 
      "confidence": 0.75, 
      "review_status": "pending" 
    }
  ]
}
```
*Note: Fields with `confidence < 0.8` will automatically be highlighted in red by the frontend.*

---

## 4. Save Human Corrections

**Endpoint:** `PUT /api/fields/:field_id/review`
**Content-Type:** `application/json`

### Request Payload (JSON)
```json
{
  "corrected_value": "$7,500.00",
  "review_status": "corrected",
  "review_notes": "Manual correction"
}
```

### Expected Response (200 OK)
```json
{
  "message": "Updated successfully"
}
```

---

## 5. Get Submissions List (Dashboard)

**Endpoint:** `GET /api/submissions`

### Expected Response (200 OK)
```json
{
  "total_count": 50,
  "data": [
    {
      "id": "sub-2026-001",
      "customer_name": "Alice Smith",
      "loan_type": "purchase",
      "submission_status": "in_review",
      "created_at": "2026-06-25T10:00:00Z",
      "risk_level": "High",
      "overall_risk_score": 85
    }
  ]
}
```
