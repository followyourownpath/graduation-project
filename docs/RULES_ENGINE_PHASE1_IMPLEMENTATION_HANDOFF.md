# Rules Engine Phase 1 — Implementation Handoff

> Audience: developers and maintainers continuing SmartFinn work
> Status: **implemented in this repo** (DB migration + backend + frontend)  
> Spec source of truth (design): `../rules-engine-phase1/RULES_ENGINE_PHASE1_MASTER_PLAN.md`  
> Do **not** invent new rule IDs, score bands, or JSON field names.

## 1. What shipped

End-to-end Phase 1 risk scoring for approved submissions:

```text
Approve submission (5 docs ready)
  -> Rules Engine list (approved only)
  -> POST /risk-assessment (13 rules, sync)
  -> Upsert one risk_assessment row per submission
  -> Report UI: 0/25/50/75/100 + fail details
```

Four scored document buckets (+25 each if any rule fails):

| Upload `document_type` | Display | Score |
|---|---|---:|
| `id_100` | ID | 0 or 25 |
| `payslip` | Payslip | 0 or 25 |
| `bank_statement_3m` | Bank Statement | 0 or 25 |
| `ato_notice` | NOA | 0 or 25 |

`fact_find` is the comparison baseline only (not a fifth +25 bucket).

Risk levels (API lowercase): `low` / `lower` / `medium` / `higher` / `high` for scores `0/25/50/75/100`.

## 2. Required setup before testing

1. Apply migration (hosted Supabase SQL Editor or your migration process), **after** existing migrations:

```text
supabase/migrations/add_rules_engine_phase1.sql
```

2. Verify:

```text
supabase/verification/verify_rules_engine_phase1.sql
```

3. Run backend + frontend as usual (`backend` Flask, `frontend` Next.js). Point `NEXT_PUBLIC_API_URL` at the backend `/api/v1` base.

4. REST resource used by backend: `/rest/v1/risk_assessment` with  
   `on_conflict=fact_find_submission_id` and Prefer `resolution=merge-duplicates,return=representation`.

## 3. Key code map

### Database

| Path | Role |
|---|---|
| `supabase/migrations/add_rules_engine_phase1.sql` | Creates `public.risk_assessment` + RLS + indexes + updated_at trigger |
| `supabase/verification/verify_rules_engine_phase1.sql` | Fails if table/policies/indexes/trigger missing |
| `supabase/README.md` | Migration #5 listed |

### Backend rules (pure functions — no network)

| Path | Role |
|---|---|
| `backend/app/rules/models.py` | `FieldValue`, `RuleResult`, domain records |
| `backend/app/rules/normalizers.py` | name/entity/address/identifier/money/date + `similarity` |
| `backend/app/rules/resolvers.py` | Fact Find applicants, addresses, employments, repayment, savings; applicant binding |
| `backend/app/rules/phase1.py` | Exactly 13 rules (`PHASE1_RULE_IDS`) |
| `backend/app/rules/scoring.py` | Per-doc 0/25 and overall 0–100 + risk level |
| `backend/app/rules/readiness.py` | Shared Phase 1 readiness checks |

### Backend I/O + HTTP

| Path | Role |
|---|---|
| `backend/app/services/rules_engine.py` | Repository + `RulesEngineService.assess` / `get_assessment` / `validate_readiness` |
| `backend/app/routes/rules_engine.py` | `POST/GET /api/v1/submissions/<id>/risk-assessment` |
| `backend/app/services/review.py` | List/detail now attach `assessment_status`, `overall_risk_score`, `risk_level`, `assessed_at` (batch lookup) |
| `backend/app/routes/review.py` | Approving a submission runs readiness via rules engine service |
| `backend/app/__init__.py` | Registers blueprint + injects `rules_engine_service` |

### Frontend

| Path | Role |
|---|---|
| `frontend/src/app/(dashboard)/rules-engine/page.js` | Approved list, Start / Recalculate / View |
| `frontend/src/app/(dashboard)/rules-engine/[submissionId]/page.js` | Refreshable report |
| `frontend/src/components/rules-engine/*` | Score card, scale, document rows, rule table |
| `frontend/src/lib/risk-display.js` | **Only** place for risk colours/labels — no client scoring |
| `frontend/src/lib/api.js` | `getApprovedSubmissions`, `startRiskAssessment`, `getRiskAssessment` |
| `frontend/src/components/dashboard-shell.jsx` | Rules Engine nav + title mapping |
| Applications / Dashboard / Review / New upload pages | Real risk badges; Phase 1 one-file-per-type upload limit |

### Docs / tests

| Path | Role |
|---|---|
| `docs/API_CONTRACT.md` | Contract including risk-assessment endpoints |
| `docs/RULES_ENGINE_PHASE1_IMPLEMENTATION_HANDOFF.md` | This file |
| `backend/tests/test_rules_engine_*.py` | Rules, service, routes |
| `frontend/tests/risk-display.test.mjs` | Display helpers |

## 4. API quick reference

Auth: `Authorization: Bearer <supabase staff JWT>` on all endpoints below.

```http
GET  /api/v1/submissions?status=approved
POST /api/v1/submissions/{submission_id}/risk-assessment
GET  /api/v1/submissions/{submission_id}/risk-assessment
```

Submission list/detail extra fields:

```json
{
  "assessment_status": "not_started",
  "overall_risk_score": null,
  "risk_level": null,
  "assessed_at": null
}
```

`assessment_status` values: `not_started` | `processing` | `completed` | `failed`.  
`not_started` is derived when no DB row exists — do not insert that value.

Common 409 codes from assessment / approval:

- `submission_not_approved`
- `phase1_documents_missing`
- `phase1_duplicate_document_type`
- `phase1_extraction_incomplete`
- `phase1_required_fields_missing`

Error shape:

```json
{
  "error": {
    "code": "phase1_required_fields_missing",
    "message": "...",
    "details": { "bank_statement_3m": ["account_number"] }
  }
}
```

Full report JSON field names are frozen in the master plan §8.4. Frontend must render API values only.

## 5. Rules registry (do not expand in Phase 1)

```text
FF-ID-001, FF-ID-002, FF-ID-003
FF-PS-001, FF-PS-002, FF-PS-003
FF-BS-001, FF-BS-002, FF-BS-003, FF-BS-004, FF-BS-006
FF-NOA-001, FF-NOA-002
```

Exactly **13** rules. Tests assert registry length. Adding rules is a new phase + contract change.

## 6. Hard constraints for follow-up agents

1. Prefer `normalised_value` over `raw_value` for comparisons (`FieldValue.comparison_value`).
2. Bind each document to applicant(s) via subject name once; do not mix Applicant 1/2 field-by-field.
3. Recalculate **upserts** the same submission row — never DELETE+INSERT; never leave multiple rows.
4. If readiness fails before execution starts, **do not** overwrite a previous completed report.
5. Frontend must not compute similarity, document scores, or overall scores.
6. Do not apply `database-design/migrations/001_initial_schema.sql` to Supabase — incompatible legacy model.
7. Mask account numbers in UI; never log TFNs or full account numbers.

## 7. Verification commands

Backend:

```bash
cd backend
python -m compileall app tests
python -m pytest -q
```

Frontend:

```bash
cd frontend
npm test
npm run lint
npm run build
```

Manual smoke (after migration + approved fixture submission):

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/submissions/<uuid>/risk-assessment

curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/submissions/<uuid>/risk-assessment
```

## 8. Suggested next work (out of Phase 1)

- Remaining ~39 rules from broader rules catalogue.
- Cross-document rules that do **not** use Fact Find (e.g. Payslip ↔ Bank).
- Assessment history (Phase 1 is overwrite-only).
- Async assessment queue if rule set becomes large.
- Lender-specific thresholds / rule editor.

Any of the above requires updating the master plan and API contract **before** coding.

## 9. Definition of Done checklist (current)

- [x] `risk_assessment` migration + verification SQL
- [x] 13 pure rules + scoring + readiness
- [x] POST/GET risk-assessment APIs with staff auth
- [x] Submission list/detail expose real assessment fields
- [x] Approval path checks Phase 1 readiness
- [x] Rules Engine list + report UI
- [x] Dashboard / Applications risk display fixed (null ≠ Low Risk)
- [x] One file per Phase 1 document type on upload
- [x] Backend pytest green; frontend test/lint/build green
- [x] `docs/API_CONTRACT.md` updated
- [ ] Shared Supabase: migration applied in team environment (ops step)
- [ ] Provide teammates with sample approved submission IDs for E2E demo

## 10. Contact / ownership hints

| Area | Typical owner in W19B-BREAD |
|---|---|
| DB migration / RLS | Solution Architect / DB lead |
| Rules + Flask APIs | Backend |
| Rules Engine UI | Frontend / Scrum Master |
| OCR field keys for ID/NOA/Payslip/Bank | AI/OCR + existing normalisation modules |

When blocked by missing OCR fields, inspect `extracted_field` for the latest completed `ocr_extraction_job` — do not invent field keys. Fact Find keys live in `backend/app/normalization/fact_find_mapping.json`.
