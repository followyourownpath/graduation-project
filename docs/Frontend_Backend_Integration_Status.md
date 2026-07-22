# Frontend-Backend Integration Status & Missing APIs

**To: Backend Team (Huaiyu)**
**From: Frontend Team**
**Date: 2026-07-21**

## 1. Integration Test Success (What's Working)

Great news! We have successfully tested the end-to-end data pipeline from the Frontend -> Python Backend -> Supabase Database. 

Using the `service_role secret` key to bypass RLS, we confirmed that the upload process works flawlessly. Applications are being created in the database (`fact_find_submission` table), and files are correctly uploaded and linked in the `source_document` table.

### ✅ Implemented & Tested APIs (Done)
- `POST /api/v1/applications` (Creates the application record)
- `POST /api/v1/submissions/<id>/documents` (Uploads documents one by one)
- `POST /api/v1/documents/<id>/ocr` (Triggers Azure OCR)

---

## 2. Blockers (Missing APIs)

While the upload process succeeds, the frontend automatically redirects to the **Dashboard** and **Review Application** pages after uploading. These pages immediately crash with a `404 Not Found` error because the corresponding `GET` endpoints are completely missing from the backend routes (e.g., `app/routes/intake.py`).

To unblock the frontend and finish the Demo flow, **please implement the following missing endpoints** based on the schemas defined in `API_Contract_v2_Demo_B.md`:

### ❌ 1. Get Submission Details (High Priority)
- **Endpoint:** `GET /api/v1/submissions/:id`
- **Why it's needed:** After uploading, the frontend jumps to `/applications/:id` and calls this to load the submission details and the list of documents. Without this, the Review Page is a blank 404 screen.

### ❌ 2. Get Submissions List (High Priority)
- **Endpoint:** `GET /api/v1/submissions`
- **Why it's needed:** The main Dashboard page needs this to populate the list/table of all applications. 

### ❌ 3. Get Extracted OCR Data (Medium Priority)
- **Endpoint:** `GET /api/v1/documents/:doc_id/extracted-data`
- **Why it's needed:** On the Review Page, when the user clicks a specific document (e.g., a payslip), the frontend needs to fetch the parsed JSON data to display in the right-hand form for human review.

### ❌ 4. Save Human Corrections (Low Priority)
- **Endpoint:** `PUT /api/v1/fields/:field_id/review`
- **Why it's needed:** When a compliance officer edits an incorrect OCR field and clicks "Save Corrections".

## 3. Next Steps
Please prioritize writing the `GET /api/v1/submissions` and `GET /api/v1/submissions/:id` routes so we can unblock the UI rendering for the Dashboard and Review pages. Let us know once they are pushed!
