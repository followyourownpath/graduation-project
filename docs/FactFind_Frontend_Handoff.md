# Fact Find Backend-to-Frontend Handoff

> Updated: 23 July 2026
> Backend owner: Jiawen (Gavin085)
> Branch / PR: `feature/fact-find-extraction` · [#13](https://github.com/unsw-cse-comp99-3900/capstone-project-26t2-9900-w19b-bread/pull/13)
> Status: **Ready for frontend integration.** The PR is awaiting review and all CI checks pass.

---

## 1. Summary

The backend is ready for frontend integration. It supports the complete
`document_type=fact_find` flow: upload, extraction, and database persistence. The new-application
page already includes a Fact Find upload option and sends `fact_find` in `document_types`.

Run the backend from this feature branch, or wait until PR #13 is merged. Older backend versions
do not contain Fact Find extraction.

---

## 2. Required Code

```bash
git fetch origin
git checkout feature/fact-find-extraction
# Or: git pull origin feature/fact-find-extraction
```

- The branch includes the current frontend from `main`, including the Fact Find UI and toast
  notifications from PR #12.
- The backend supports direct AcroForm extraction and paged Azure OCR.
- Do not commit the local `.env`. Ask Jiawen or Huaiyu for Supabase configuration and, when
  testing scanned files, Azure configuration.

### Start the Backend

```bash
cd backend
# Confirm that .venv and .env are configured
.venv/bin/python wsgi.py
# http://localhost:5000
curl http://localhost:5000/api/v1/health
```

The `integrations_configured.supabase` and `azure_document_intelligence` values should reflect the
local configuration.

### Start the Frontend

```bash
cd frontend
npm install   # The branch may include dependencies such as sonner
npm run dev   # Defaults to localhost:3000; api.js targets localhost:5000
```

In `frontend/src/lib/api.js`, `USE_REAL_API = true` and
`BASE_URL = http://localhost:5000/api/v1`.

---

## 3. Backend Capabilities

### 3.1 Capability Matrix

| Capability | Implementation |
|------------|----------------|
| Document type | The intake allowlist includes **`fact_find`** |
| Path A: direct AcroForm read | PyMuPDF reads controls from an electronically completed PDF without calling Azure |
| Path B: Azure OCR | Scanned or flattened PDFs are split into requests of at most two pages for the F0 tier, analysed, merged, and mapped to business fields |
| Blank fillable form | A form with controls but no values returns HTTP **422** with `error.code = fact_find_blank_form` |
| Persistence | Fields use the same shape as payslip output and are written to Supabase `extracted_field` |
| Raw backup | Responses are stored under `ocr-responses/{document_id}/{job_id}.json` |
| Unit tests | `tests/test_fact_find.py` and `tests/test_fact_find_ocr.py` |
| Smoke test | `tools/smoke_test_fact_find.py`; the seven-page completed fixture produces **264** fields |

### 3.2 Key Files

| File | Purpose |
|------|---------|
| `backend/app/normalization/fact_find.py` | Direct AcroForm extraction |
| `backend/app/normalization/fact_find_mapping.json` | Control-name to `field_key` mapping from Mapping Matrix v1 |
| `backend/app/normalization/fact_find_ocr.py` | Azure layout JSON to business fields |
| `backend/app/services/azure_paging.py` | PDF page chunking and result merging |
| `backend/app/services/ocr_pipeline.py` | Pipeline routing and persistence |
| `backend/app/routes/intake.py` | `DOCUMENT_TYPES` allowlist containing `fact_find` |
| `backend/tests/fixtures/fact_find_filled.pdf` | Completed-form test fixture |

### 3.3 Verified Backend Flow

- Completed fixture: `pages=7`, `fields=264`,
  `ocr_extraction_job.provider=acroform_direct_read`, and `model_name=pymupdf`.
- Historical smoke-test job: `9a1f35be-dcc4-446d-b7a5-eeecb9671182`, expected to have
  264 `extracted_field` rows.

---

## 4. End-to-End Flow

```text
[Frontend] Create an application
  → POST /api/v1/applications
      { customer_name, loan_type, ... }
  → Receive submission_id

[Frontend] Upload each file, including the Fact Find PDF
  → POST /api/v1/submissions/{submission_id}/documents
      multipart: file + document_type
      Fact Find must use the literal document_type: fact_find
  → Receive document.id

[Frontend] Trigger extraction, as implemented in api.js
  → POST /api/v1/documents/{document_id}/ocr
  → Processing is synchronous at the backend; direct reads are quick, while paged OCR may take minutes

[Backend] Route the document
  fact_find + PDF + populated controls → AcroForm → extracted_field
  fact_find + PDF + empty controls     → 422 fact_find_blank_form
  fact_find + PDF + no controls        → paged Azure OCR → fact_find_ocr → extracted_field
  other types, such as payslip         → existing pipeline

[Frontend] Review details
  → GET /api/v1/documents/{document_id}/extracted-data
  → Display the field list using the same response shape as payslip data
```

### 4.1 Existing Frontend Integration Points

In `applications/new/page.js`:

- Fact Find upload uses **`categoryId = 'fact_find'`**.
- `handleSubmit` calls `formData.append('document_types', categoryId)`.

This sends `document_type=fact_find` to the backend.

Important limitations:

- Email sync is currently a UI stub and does not upload attachments. Use **Upload Fact Find PDF**
  during integration testing.
- A simulated `factFindImported` value does not create a backend document unless
  `categoryFiles['fact_find']` contains a real PDF.

### 4.2 OCR Timing

After upload, `api.createSubmission` triggers `POST .../ocr` sequentially and asynchronously to
avoid rate limits and thread exhaustion. If the detail page opens too soon, a document may still
be `processing` or contain no fields. Poll or refresh until processing completes.

---

## 5. Integration API Contract

Base URL: `http://localhost:5000/api/v1`
Authentication: `Authorization: Bearer <token>`. See section 7 for the demo bypass.

### 5.1 Create an Application

`POST /applications`

```json
{
  "customer_name": "John & Mary Citizen",
  "loan_type": "purchase",
  "source_channel": "frontend"
}
```

The response contains `application_id` and `submission_id`.

### 5.2 Upload a Document

`POST /submissions/{submission_id}/documents`

`multipart/form-data`:

- `file`: PDF
- `document_type`: `fact_find`

A successful request normally returns 201. The body contains the document `id` and
`processing_status`, which usually starts as `uploaded`.

### 5.3 Trigger Extraction

`POST /documents/{document_id}/ocr`

Successful response:

```json
{
  "job_id": "...",
  "document_id": "...",
  "status": "completed",
  "pages": 7,
  "fields": 264,
  "tables": 0,
  "cells": 0
}
```

Blank fillable form:

```json
{
  "error": {
    "code": "fact_find_blank_form",
    "message": "The fact find form contains no filled-in values. Please upload a completed copy."
  }
}
```

Other possible errors include `azure_rate_limited`, other `azure_*` codes, and
`document_not_found`.

### 5.4 Retrieve Extracted Fields

`GET /documents/{document_id}/extracted-data`

Each field aligns with the payslip response and the `extracted_field` table:

| Field | Meaning |
|-------|---------|
| `id` | `extracted_field` UUID used for review updates |
| `field_key` | Stable key such as `applicant_1_mobile` |
| `field_label` | Display label |
| `raw_value` | Original extracted value |
| `normalised_value` | Normalised value |
| `data_type` | `text`, `money`, `date`, `phone`, `email`, `enum`, `boolean`, `integer`, and others |
| `section_name` | Section such as `personal_details`, `employment`, or `monthly_expenses` |
| `applicant_number` | 1 or 2; some global fields use 1 |
| `mapped_table` / `mapped_column` | Optional mapping to a business-table column |
| `review_status` | Initially `pending` |
| `confidence` | Usually `1.0` for direct reads; may be absent for OCR |
| `bounding_box` | Optional eight-number polygon |

A completed form contains approximately **264** fields. Group the UI by `section_name` and
`applicant_number`; do not hard-code the small set of fields used by a payslip.

---

## 6. Display and Review Rules

### 6.1 Same as Applicant 1

When Same as Applicant 1 is selected, extraction stores only a flag:

- `applicant_2_current_address_same_as_applicant_1` → normalised `true`

The backend does not duplicate Applicant 1's address into Applicant 2 fields. When the flag is
true, display Applicant 1's address, including any reviewer corrections. This follows section 6.1
of the client Mapping Matrix.

### 6.2 Normalisation Examples

- Dates prefer Australian ordering and use ISO `YYYY-MM-DD`, for example
  `15/03/2020` → `2020-03-15`.
- Mobile numbers use E.164, for example `0412 345 678` → `+61412345678`.
- Money values use decimal strings such as `2500.00`.
- Enums use values such as `single` for marital status and `applicant_1` or `both` for ownership.

### 6.3 Distinguishing Direct Read from OCR

Inspect `ocr_extraction_job` in Supabase:

| `provider` | `model_name` | Meaning |
|------------|--------------|---------|
| `acroform_direct_read` | `pymupdf` | Direct electronic-form read |
| `azure_document_intelligence` | `prebuilt-layout`, or configured value | OCR |

`raw_response_uri` points to the raw JSON in Storage.

---

## 7. Authentication

`require_staff` in `backend/app/auth.py` still uses the Demo B bypass:

- It does not validate a real user JWT.
- It injects `demo_user` and `demo_profile`.
- It uses `SUPABASE_SECRET_KEY`, when available, to access the database without RLS.

Consequences:

- Local integration may work without a login token, depending on the frontend request headers.
- `/api/v1/auth/me` may return `demo@smartfinn.com` and cannot verify real staff access.
- Before merging into `main` or deploying, coordinate with Jerry to restore real JWT and
  `staff_profile` validation.

A real staff account exists at `z5560574@ad.unsw.edu.au`; ask Jiawen for its password after real
authentication is restored.

---

## 8. Test PDFs

| File | Purpose |
|------|---------|
| `backend/tests/fixtures/fact_find_filled.pdf` | Completed direct-read form; expect approximately 264 fields |
| Team drive: `Client_form_2024_FILLED.pdf` and `Client_form 2024_sample_1.pdf` | Completed forms; the sample contains fewer fields |
| Flattened or scanned PDF without AcroForm controls | Exercises the slower Azure OCR path and consumes F0 quota |

A blank template with empty controls should return 422 and is not a successful test case.

---

## 9. Frontend Test Checklist

1. Check out `feature/fact-find-extraction` and start both services.
2. Create an application, upload a **completed PDF** in the Fact Find section, add any other
   required documents, and submit.
3. Open the application detail page. After OCR completes, refresh and confirm that the Fact Find
   document contains many fields, approximately 264 for the completed fixture.
4. Check representative fields such as `cover_customer_name`, `applicant_1_mobile`, and
   `expense_groceries_monthly_amount`.
5. Optionally upload a blank fillable form and confirm that the UI shows the backend error.
6. Optionally group fields into collapsible `section_name` sections rather than rendering an
   unstructured list of 264 rows.

---

## 10. Known Limitations and Handoff Boundary

| Item | Status | Owner |
|------|--------|-------|
| Merge PR #13 into `main` | Awaiting review | Team |
| Restore real `require_staff` | Demo bypass remains | Backend and Jerry |
| Group Fact Find fields by section in the review UI | Optional enhancement | Frontend |
| End-to-end scanned-file test against Azure | Unit tests exist; complete UI test is optional | Backend support |
| Fact Find email sync | Frontend stub | Frontend or later phase |
| Expand `extracted_field` into business tables such as `applicant` | Outside PR #13; current flow ends at extraction and review | Later phase |

---

## 11. Troubleshooting

1. Run `curl localhost:5000/api/v1/health`.
2. In the browser Network panel, confirm that the upload sends `document_type=fact_find`, not
   `Fact Find` or `ffs`.
3. Inspect the `POST .../ocr` HTTP status and JSON `error.code`.
4. With Supabase Dashboard access, inspect:
   - `ocr_extraction_job` for provider and status.
   - `extracted_field` counts filtered by `source_document_id` or `ocr_extraction_job_id`.
5. Inspect backend terminal logs.
6. Contact Jiawen or comment on the PR.

---

## 12. References

- PR: https://github.com/unsw-cse-comp99-3900/capstone-project-26t2-9900-w19b-bread/pull/13
- Branch: `feature/fact-find-extraction`
- Local progress notes maintained by Jiawen are not tracked in Git.
- Supabase project reference: `eebqyropaqcdvepcjqxo`; ask Huaiyu for Dashboard access.

---

## 13. Quick Start

1. Run `git checkout feature/fact-find-extraction && git pull`.
2. Configure `backend/.env`, then start `wsgi.py` and `npm run dev`.
3. Create an application and upload `fact_find_filled.pdf`, or the team's completed PDF, to the
   Fact Find section.
4. Refresh the detail page and inspect the extracted fields.
5. Send Jiawen the `document_id` and Network error if integration fails.

Integration can begin on the feature branch before PR #13 is merged.
