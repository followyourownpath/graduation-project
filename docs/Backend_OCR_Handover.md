# 🚀 Frontend-Backend Integration Handover & OCR Next Steps

Hi Backend Team,

We have successfully completed the end-to-end frontend and backend integration for **Demo B**! The entire flow—from the user uploading a document on the frontend, storing it in Supabase, triggering Azure OCR, and rendering the extracted data in the Review Application page—is now **100% working for Payslips**.

However, during our testing, we discovered that while Azure is successfully processing other document types (like Bank Statements and IDs), the data isn't being displayed on the frontend. This handover document outlines the current status and the remaining backend tasks to complete the OCR integration.

---

## ✅ 1. Current Progress & What's Working
- **Frontend File Upload**: The frontend can seamlessly upload multiple files to Supabase via `POST /api/v1/submissions/{id}/documents`.
- **Signed URL Bug Fixed**: A bug in `backend/app/services/review.py` where signed URLs were missing the `/storage/v1` path has been fixed. The frontend can now successfully render PDF previews in the `iframe`.
- **Sequential OCR Triggering**: To prevent hitting Azure's Free Tier (F0) rate limit (15 pages/minute), the frontend now automatically and **sequentially** triggers the OCR job (`POST /api/v1/documents/{doc_id}/ocr`) in the background.
- **Payslip Extraction**: End-to-end extraction and frontend rendering for **Payslips** is working perfectly.

---

## 🚧 2. The Core Issue: Missing Parsing Logic
Currently, when a user uploads a `bank_statement_3m` or `id_100`, Azure successfully analyzes it, but the frontend shows an empty extracted data form.

**The cause:** In `backend/app/services/ocr_pipeline.py` (around line 120), the data extraction logic is hardcoded strictly for payslips:
```python
# The current hardcoded logic in OcrPipelineService.process()
extracted_fields = extract_payslip_fields(result) if document_type == "payslip" else []
```
Because of this `else []`, the backend discards the Azure JSON payload for any document that isn't a payslip, meaning no fields are inserted into the `extracted_field` database table.

---

## 🛠️ 3. Your Tasks

Your next objective is to write the specific mapping functions for the remaining document types. 

### Task 1: Create Normalization Mappers
Just like you created `backend/app/normalization/payslip.py` containing `extract_payslip_fields`, we need you to create similar parsing scripts for the other document types:
- **`bank_statement_3m`**: Needs an `extract_bank_statement_fields(result)` function.
- **`id_100`**: Needs an `extract_id_fields(result)` function.
- **`contract_of_sale` / `property_valuation`** *(Note: We've been using `employment_letter.pdf` as a mock for these in tests)*: Needs corresponding extraction functions.

### Task 2: Update the Pipeline Dispatcher
Once the functions are written, please update `backend/app/services/ocr_pipeline.py` to route the Azure result to the correct parser based on the `document_type`:

```python
# Example Update
if document_type == "payslip":
    extracted_fields = extract_payslip_fields(result)
elif document_type == "bank_statement_3m":
    extracted_fields = extract_bank_statement_fields(result)
elif document_type == "id_100":
    extracted_fields = extract_id_fields(result)
else:
    extracted_fields = []
```

### Task 3: Azure Free Tier (F0) Limitation Notice
Please be aware that the Azure Document Intelligence Dev Tier is strictly limited to **15 pages per minute**. 
If we upload a large 10-page bank statement alongside a 5-page contract, Azure **will** reject subsequent requests with an `HTTP 429 Too Many Requests`. Your backend correctly catches this and returns a `503 Service Unavailable`, but it means the OCR job will be marked as `failed` in the database.
- *For Demo B:* The frontend is currently patched to allow the submission of a single file to bypass this limit for presentation purposes.
- *Long-term:* We either need to upgrade the Azure tier or build a retry/queue mechanism for 429 errors.

---

## 🔗 Useful Links & Next Steps
- **Branch**: All integration fixes have been pushed to `backend-dev`.
- **Testing**: You can test your new parsing logic directly by calling `POST /api/v1/documents/{doc_id}/ocr` via Postman, and verifying if rows appear in the `extracted_field` Supabase table.
- Let us know when the mappers for `id_100` and `bank_statement_3m` are pushed, and we can immediately test it on the UI!

Happy coding! 🚀
