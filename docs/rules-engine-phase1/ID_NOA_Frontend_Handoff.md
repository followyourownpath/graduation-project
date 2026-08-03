# ID (NSW Licence) & NOA Backend-to-Frontend Handoff

> Updated: 30 July 2026  
> Backend owner: Jiawen  
> Branch: `feature/ocr-id-licence-ato-notice` (PR open, awaiting review into `main`)  
> Status: **Backend ready for frontend integration** after the PR merges (or checkout this branch for local testing).

Reference style: `capstone-project-26t2-9900-w19b-bread/docs/FactFind_Frontend_Handoff.md`.

---

## 1. Summary

The backend now supports full OCR → normalisation → Supabase persistence for:

| Upload `document_type` | Document | Extracted fields (typical) |
|------------------------|----------|----------------------------|
| **`id_100`** | NSW Driver Licence (card image / PDF) | **9** licence identity fields |
| **`ato_notice`** | ATO Notice of Assessment (NOA) | **24** keys always emitted (empty amounts may be `null`) |

Same intake / OCR / review APIs as payslip and Fact Find. No new endpoints.

**Breaking note for `id_100`:** legacy passport-style keys (`document_number`, `driver_licence_link`, …) are **removed**. Use the NSW licence keys below.

---

## 2. Required Code

```bash
git fetch origin
git checkout feature/ocr-id-licence-ato-notice
# After merge: git checkout main && git pull
```

```bash
cd backend
.venv/bin/python wsgi.py
# Default listen: http://localhost:8000
curl http://localhost:8000/api/v1/health
```

Confirm `integrations_configured.supabase` and `azure_document_intelligence` are true when testing real OCR.

Frontend (`USE_REAL_API`, `BASE_URL`) should point at the same host/port as the running backend.

---

## 3. Backend Capabilities

### 3.1 Capability Matrix

| Capability | `id_100` | `ato_notice` |
|------------|----------|--------------|
| Allowlist | Already in `DOCUMENT_TYPES` | Already in `DOCUMENT_TYPES` |
| Extraction path | Azure Document Intelligence `prebuilt-layout` → `extract_id_fields` | Same Azure path → `extract_ato_notice_fields` |
| AcroForm shortcut | No | No |
| Empty / missing amounts | Field omitted if not found | **Always insert all 24 keys**; missing amounts → `null` |
| Verified E2E | Licence JPG → 9 fields in DB | NOA PDF → 24 fields in DB |

### 3.2 Key Files

| File | Purpose |
|------|---------|
| `backend/app/normalization/id_100.py` | NSW Driver Licence mapper |
| `backend/app/normalization/ato_notice.py` | Notice of Assessment mapper |
| `backend/app/services/ocr_pipeline.py` | Routes `id_100` / `ato_notice` |
| `backend/tests/test_normalization.py` | Unit tests for both |

### 3.3 Field catalogue (frontend binding)

Full key lists and normalisation rules:  
[`ID_NOA_Field_Reference.md`](./ID_NOA_Field_Reference.md)

---

## 4. End-to-End Flow

```text
[Frontend] POST /api/v1/applications
  → submission_id

[Frontend] POST /api/v1/submissions/{submission_id}/documents
  multipart: file + document_type
  → id_100  for NSW Driver Licence
  → ato_notice  for ATO Notice of Assessment
  → document.id

[Frontend] POST /api/v1/documents/{document_id}/ocr
  → Azure layout → mapper → extracted_field
  → synchronous; typically seconds–1 min for 1-page docs

[Frontend] GET /api/v1/documents/{document_id}/extracted-data
  → review UI
```

Trigger OCR **sequentially** across documents (Azure F0 rate limits), same as existing Demo B behaviour.

---

## 5. API Contract (unchanged shapes)

### 5.1 Upload

`POST /submissions/{submission_id}/documents`

- Form field `document_type` must be exactly `id_100` or `ato_notice`.
- Licence sample may be `image/jpeg` or PDF; NOA sample is typically PDF (often image-only scan).

### 5.2 Trigger OCR

`POST /documents/{document_id}/ocr`

Success includes counts such as `pages`, `tables`, `fields`, `job_id`.

Expect roughly:

- `id_100` → `fields ≈ 9`
- `ato_notice` → `fields = 24` (including null placeholders)

### 5.3 Extracted data

`GET /documents/{document_id}/extracted-data`

```json
{
  "doc_id": "…",
  "document_type": "id_100",
  "fields": [
    {
      "field_id": "…",
      "section_name": "id_100",
      "field_key": "full_legal_name",
      "field_label": "Full Legal Name",
      "raw_value": "Junhong ZHONG",
      "confidence": 0.94,
      "review_status": "pending"
    }
  ]
}
```

**Display value:** the review API currently places the preferred display string in each item’s `raw_value` (backend chooses normalised value when present, otherwise original raw). Treat that as what the Review form should show. Corrections still go through `PUT /fields/{field_id}/review` with `corrected_value`.

`section_name`:

- Licence → `id_100`
- NOA → `ato_notice`

---

## 6. Display and Review Rules

### 6.1 Normalisation

| Type | Rule | Example |
|------|------|---------|
| `date` | ISO `YYYY-MM-DD` | `08 JAN 1992` → `1992-01-08` |
| `money` | Decimal string, no `$` / commas | `$85,321` → `85321.00` |
| `identifier` | Digits stripped of spaces where applicable | TFN `748 219 356` → `748219356` |
| `enum` | `CR` / `DR` for NOA direction fields | |

### 6.2 NOA null placeholders

These keys are **always present** for `ato_notice`. When the notice has no separate amount line, `raw_value` / normalised storage is `null` (API display may also be `null`):

- `low_income_tax_offset`
- `non_refundable_tax_offsets`
- `other_liabilities`
- `payg_credits_and_entitlements`

Render an empty editable slot; do not hide the row if the product wants a fixed NOA form.

### 6.3 NOA amount + direction

Pairs such as result / outcome:

- `result_of_notice_amount` + `result_of_notice_direction` (`CR` refund / `DR` amount owing)
- `outcome_amount` + `outcome_direction`

Do not merge amount and direction into one control unless product asks.

### 6.4 Sensitive fields

NOA includes **`tfn`**. Restrict display / logging in the UI accordingly.

### 6.5 `id_100` scope

Current mapper targets **NSW Driver Licence** card layout only (not passport / multi-doc 100-point packs). Upload UX can still label the slot “100-pt ID”, but extracted keys are licence-oriented.

---

## 7. Frontend Checklist

- [ ] Ensure new-application upload sends `document_type=id_100` / `ato_notice` (UI labels already exist for both).
- [ ] After merge (or on this branch), Review page binds the keys in `ID_NOA_Field_Reference.md`.
- [ ] Handle `null` NOA money fields as empty inputs.
- [ ] Show `CR`/`DR` separately from money amounts.
- [ ] Keep sequential OCR triggering to avoid Azure 429.
- [ ] Do not rely on removed `id_100` keys (`document_number`, `driver_licence_*`, passport table layout).

---

## 8. Smoke / Verification Hints

```bash
# Backend unit tests
cd backend && .venv/bin/python -m pytest tests/test_normalization.py -q

# After a successful OCR job, inspect DB fields
.venv/bin/python tools/show_fields.py id_100
.venv/bin/python tools/show_fields.py ato_notice
```

Optional bypass E2E helper (local only): `backend/tools/e2e_id_noa_bypass.py` with `AUTH_DEMO_BYPASS=true`.

---

## 9. Contact

Questions on keys, null behaviour, or sample docs: backend owner on branch `feature/ocr-id-licence-ato-notice`.
