# SmartFINN Backend API Contract

This document is the version-controlled contract between the SmartFINN frontend
and backend. It describes the current `/api/v1` interface implemented in Flask.

Base URLs:

```text
Direct local backend: http://localhost:5000/api/v1
Docker Compose:       http://localhost:8000/api/v1
```

## Authentication

All endpoints except `GET /health` require a Supabase access token belonging to
an active SmartFINN staff member:

```http
Authorization: Bearer <supabase_access_token>
```

Authentication failures use the common error format below:

```json
{
  "error": {
    "code": "bearer_token_required",
    "message": "Missing or invalid Authorization header"
  }
}
```

Typical authentication status codes are:

- `401`: token missing, invalid, or expired.
- `403`: user is not an active staff member, or database access is denied.

## Endpoint summary

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Check service and integration configuration |
| GET | `/auth/me` | Return the authenticated staff identity |
| POST | `/applications` | Create an application and submission |
| POST | `/submissions/{submission_id}/documents` | Upload one document |
| POST | `/documents/{document_id}/ocr` | Extract and persist document data |
| GET | `/submissions` | List submissions for the dashboard |
| GET | `/submissions/{submission_id}` | Get a submission and its documents |
| GET | `/documents/{document_id}/extracted-data` | Get review-ready fields |
| PUT | `/fields/{field_id}/review` | Save a field review or correction |
| PUT | `/submissions/{submission_id}/status` | Approve or reject a submission |

## Health

### `GET /health`

No authentication required.

```json
{
  "service": "smartfinn-backend",
  "status": "ok",
  "integrations_configured": {
    "supabase": true,
    "azure_document_intelligence": true
  }
}
```

## Staff identity

### `GET /auth/me`

Returns the authenticated Supabase user and matching active `staff_profile`.

```json
{
  "user": {
    "id": "user-id",
    "email": "staff@example.com"
  },
  "staff_profile": {
    "user_id": "user-id",
    "full_name": "Example Staff",
    "role": "analyst",
    "is_active": true
  }
}
```

## Application intake

### `POST /applications`

Request:

```json
{
  "customer_name": "Alice Smith",
  "loan_type": "purchase",
  "source_channel": "frontend"
}
```

Supported `loan_type` values:

```text
purchase, investment, refinance, first_home, self_employed
```

Success: `201 Created`

```json
{
  "application_id": "application-uuid",
  "submission_id": "submission-uuid"
}
```

### `POST /submissions/{submission_id}/documents`

Content type: `multipart/form-data`

| Field | Type | Required |
|---|---|---|
| `file` | PDF, JPEG, PNG, or TIFF | Yes |
| `document_type` | String enum | Yes |

Supported document types:

```text
payslip, bank_statement_3m, id_100, contract_of_sale,
property_valuation, rental_appraisal, existing_loan_statements,
first_home_grant, tax_return, ato_notice, profit_loss, fact_find
```

Success: `201 Created`. The response contains the stored document record,
including at least `id`, `document_type`, and `processing_status`.

## Extraction

### `POST /documents/{document_id}/ocr`

Runs Azure Document Intelligence, or direct AcroForm extraction for a filled
Fact Find PDF. Results are persisted before the request returns.

```json
{
  "job_id": "job-uuid",
  "document_id": "document-uuid",
  "status": "completed",
  "pages": 1,
  "tables": 2,
  "cells": 20,
  "fields": 8
}
```

A blank fillable Fact Find form may return `422`.

## Submission queries

### `GET /submissions`

Optional query parameters:

| Parameter | Default | Rules |
|---|---:|---|
| `page` | `1` | Positive integer |
| `limit` | `50` | Integer from 1 to 100 |
| `status` | None | Exact submission-status filter |

```json
{
  "total_count": 1,
  "data": [
    {
      "id": "submission-uuid",
      "customer_name": "Alice Smith",
      "loan_type": "purchase",
      "submission_status": "in_review",
      "extraction_status": "completed",
      "created_at": "2026-07-29T10:00:00Z",
      "risk_level": null,
      "overall_risk_score": null
    }
  ]
}
```

Risk fields remain `null` until the risk-scoring module is implemented.

### `GET /submissions/{submission_id}`

Returns the same submission fields plus linked documents:

```json
{
  "id": "submission-uuid",
  "customer_name": "Alice Smith",
  "loan_type": "purchase",
  "submission_status": "in_review",
  "extraction_status": "completed",
  "risk_level": null,
  "overall_risk_score": null,
  "documents": [
    {
      "doc_id": "document-uuid",
      "original_file_name": "payslip.pdf",
      "document_type": "payslip",
      "processing_status": "completed",
      "storage_uri": "short-lived-signed-url"
    }
  ]
}
```

## Extracted fields and review

### `GET /documents/{document_id}/extracted-data`

Returns fields from the document's latest completed extraction:

```json
{
  "doc_id": "document-uuid",
  "document_type": "payslip",
  "fields": [
    {
      "field_id": "field-uuid",
      "section_name": "payslip",
      "field_key": "net_income",
      "field_label": "Net Income",
      "raw_value": "7200.00",
      "confidence": 0.94,
      "review_status": "pending"
    }
  ]
}
```

### `PUT /fields/{field_id}/review`

Request:

```json
{
  "corrected_value": "7500.00",
  "review_status": "corrected",
  "review_notes": "Confirmed against the uploaded payslip."
}
```

Supported review states:

```text
pending, corrected, confirmed, rejected
```

Response:

```json
{
  "message": "Updated successfully"
}
```

### `PUT /submissions/{submission_id}/status`

Request:

```json
{
  "status": "approved"
}
```

Supported values are `approved` and `rejected`.

```json
{
  "message": "Status updated successfully"
}
```

## Common errors

All API errors follow this structure:

```json
{
  "error": {
    "code": "document_not_found",
    "message": "Document not found."
  }
}
```

| Status | Meaning |
|---:|---|
| `400` | Invalid path, query, form, or JSON input |
| `401` | Bearer token missing, invalid, or expired |
| `403` | Staff inactive/unauthorised or database access denied |
| `404` | Requested record not found |
| `413` | Uploaded file exceeds the configured limit |
| `422` | Valid request but document cannot be processed |
| `500` | Unexpected backend error |
| `502` | Supabase or Azure failed to complete an operation |
| `503` | Integration service unavailable |

## Maintenance rule

Any pull request that changes an endpoint, request field, response field,
authentication rule, enum, or error code must update this contract in the same
pull request. Frontend integration should refer to this file rather than a
separate copy of the API definition.
