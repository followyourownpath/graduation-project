# Workstream 3: Data Modelling and Database Design

> **Owner:** Yang Shu (Shuyang) — Solution Architect  
> **Based on:** Internship Guide §8, client scope Task i/ii, SmartFINN tech stack (Self-hosted Supabase / PostgreSQL)  
> **Status:** MVP draft — pending review by Alan (field definitions), Haomiao (OCR mapping), Jiawen (validation rules)

---

## 1. Objective

Complete the database structure design before backend implementation begins, ensuring:

- Task i (data capture) has tables to write to
- Task ii (verification and checks) can store results and flag discrepancies
- Task iii (Dashboard) can rank applications by `overall_confidence_pct`

---

## 2. Deliverables

| Deliverable | File Location |
|-------------|---------------|
| Entity Relationship Diagram (ERD) | `ERD.drawio` → export as `ERD.png` |
| Database schema document | This document §4–§6 |
| Table relationship explanation | This document §3 |
| Field list for each table | This document §5 |
| Sample extracted data JSON | `samples/sample-extracted-data-payslip.json` |
| Migration plan | This document §7 + `migrations/001_initial_schema.sql` |
| Database naming convention | This document §8 |

---

## 3. Table Relationship Explanation

### 3.1 Relationships Required by the Internship Guide

| Relationship | Cardinality | Implementation |
|--------------|-------------|----------------|
| One client → many applications | 1 : N | `applications.client_id` → `clients.id` |
| One application → many documents | 1 : N | `documents.application_id` → `applications.id` |
| One document → one extracted data record | 1 : 1 | `extracted_data.document_id` UNIQUE |
| One document → one fraud result | 1 : 1 | `fraud_results.document_id` UNIQUE |
| One application → many alerts | 1 : N | `alerts.application_id` → `applications.id` |
| One alert → many status history records | 1 : N | `alert_status_history.alert_id` → `alerts.id` |

### 3.2 Extended Relationships (Supporting MVP Implementation)

| Relationship | Description |
|--------------|-------------|
| `extracted_data` → `extracted_field_values` (1:N) | Per guide: searchable fields in columns, flexible OCR in JSON; parent record holds JSON, child table holds indexable fields |
| `validation_rules` → `verification_results` (1:N) | Rule execution writes verification results (Task ii) |
| `validation_rules` → `alerts` (1:N) | Failed validation may generate alerts |
| `documents` → `alerts` (1:N, optional) | Alerts may be linked to a specific document |

### 3.3 Out-of-Scope Entities (OOS — Not Created in Migration 001)

| Entity | Reason |
|--------|--------|
| `users` | RBAC not in MVP (scope Task iv) |
| `roles` | Same as above |
| `reports` | Marked OOS in internship guide |
| `audit_logs` | Marked OOS in guide; append-only table may be added in a later phase |
| `notifications` | Marked OOS in internship guide |

---

## 4. Entity Overview and Scope Mapping

```
clients
  └── applications (loan_type, confidence, risk_score)
        ├── documents (pdf/jpeg/png/docx)
        │     ├── extracted_data (JSONB + 1:1)
        │     │     └── extracted_field_values (searchable columns)
        │     └── fraud_results (1:1)
        ├── verification_results (Task ii)
        └── alerts
              └── alert_status_history

validation_rules (rule configuration, seed data)
```

| Entity | Task i | Task ii | Task iii |
|--------|--------|---------|----------|
| clients | ✅ | | |
| applications | ✅ | ✅ | ✅ ranking |
| documents | ✅ | | |
| extracted_data | ✅ | | |
| extracted_field_values | ✅ | ✅ comparison source | |
| fraud_results | | ✅ | |
| validation_rules | | ✅ | |
| verification_results | | ✅ | |
| alerts | | ✅ | ✅ display |
| alert_status_history | | ✅ | |

---

## 5. Field List per Table

### 5.1 `clients` — Client

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Primary key |
| full_name | VARCHAR(200) | NOT NULL | Full name |
| date_of_birth | DATE | | Date of birth |
| email_masked | VARCHAR(100) | | Masked email |
| phone_masked | VARCHAR(30) | | Masked phone |
| address_line | VARCHAR(300) | | Street address |
| state | VARCHAR(50) | | State |
| postcode | VARCHAR(10) | | Postcode |
| created_at | TIMESTAMPTZ | NOT NULL | Created timestamp |
| updated_at | TIMESTAMPTZ | NOT NULL | Updated timestamp |

### 5.2 `applications` — Loan Application

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Primary key |
| client_id | UUID | FK → clients | Client |
| loan_type | loan_type ENUM | NOT NULL | Loan type |
| loan_amount | NUMERIC(14,2) | | Loan amount |
| declared_annual_income | NUMERIC(14,2) | | Declared annual income |
| property_address | VARCHAR(500) | | Property address |
| status | application_status ENUM | NOT NULL | Application status |
| overall_confidence_pct | NUMERIC(5,2) | 0–100 | **Task iii ranking field** |
| risk_score | NUMERIC(5,2) | 0–100 | Risk score (computed by Jiawen's rules) |
| risk_level | risk_level ENUM | | low / medium / high |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**loan_type enum values:** `home_loan` | `investment_loan` | `personal_loan` | `commercial_loan` | `refinance`

### 5.3 `documents` — Uploaded Document

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| application_id | UUID | FK → applications | |
| file_name | VARCHAR(255) | NOT NULL | Original filename |
| file_type | file_type ENUM | NOT NULL | pdf / jpeg / png / docx |
| document_category | document_category ENUM | NOT NULL | payslip / bank_statement / id_document, etc. |
| storage_path | VARCHAR(500) | NOT NULL | Supabase Storage path |
| file_size_bytes | BIGINT | | File size |
| ocr_status | ocr_status ENUM | NOT NULL | pending → processing → completed / failed |
| is_mandatory | BOOLEAN | NOT NULL | Whether required (determined by Workstream 2 matrix) |
| uploaded_at | TIMESTAMPTZ | NOT NULL | |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL | |

### 5.4 `extracted_data` — OCR Extraction Master Record (1:1 per document)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| document_id | UUID | FK UNIQUE → documents | One-to-one |
| raw_ocr_json | JSONB | | Raw Azure OCR response |
| normalized_fields | JSONB | | Structured JSON after OpenAI normalisation |
| avg_confidence_pct | NUMERIC(5,2) | 0–100 | Average confidence for this document |
| extraction_status | extraction_status ENUM | NOT NULL | pending / completed / partial / failed |
| extracted_at | TIMESTAMPTZ | | Extraction completion time |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL | |

### 5.5 `extracted_field_values` — Searchable Field Rows

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| extracted_data_id | UUID | FK → extracted_data | |
| field_name | VARCHAR(100) | NOT NULL | Normalised field name, e.g. `employer_name` |
| field_value | TEXT | | Field value |
| confidence_pct | NUMERIC(5,2) | 0–100 | Per-field confidence |
| source | field_source ENUM | NOT NULL | ocr / openai / manual |
| created_at | TIMESTAMPTZ | NOT NULL | |

### 5.6 `fraud_results` — Fraud Detection Result (1:1 per document)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| document_id | UUID | FK UNIQUE → documents | |
| fraud_status | fraud_status ENUM | NOT NULL | clean / suspicious / confirmed_fraud / inconclusive |
| severity | severity_level ENUM | NOT NULL | low / moderate / critical |
| reason | TEXT | | Reason description |
| confidence_pct | NUMERIC(5,2) | | Fraud detection confidence |
| recommendation | TEXT | | e.g. "Manual review required" |
| raw_response | JSONB | | Raw Fortiro / Mock API response |
| checked_at | TIMESTAMPTZ | | |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL | |

### 5.7 `validation_rules` — Validation Rule Configuration

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| rule_code | VARCHAR(50) | UNIQUE NOT NULL | e.g. `NAME_MATCH` |
| rule_name | VARCHAR(200) | NOT NULL | |
| description | TEXT | | |
| severity | severity_level ENUM | NOT NULL | |
| loan_types | loan_type[] | | Applicable loan types; NULL = all |
| is_active | BOOLEAN | NOT NULL | |
| rule_config | JSONB | | Rule parameters (thresholds, etc.) |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL | |

### 5.8 `verification_results` — Verification Execution Results (Task ii)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| application_id | UUID | FK → applications | |
| validation_rule_id | UUID | FK → validation_rules | Nullable |
| check_type | check_type ENUM | NOT NULL | tool_api / abr / cross_document / mock |
| field_name | VARCHAR(100) | | Field under verification |
| expected_value | TEXT | | Expected value |
| actual_value | TEXT | | Actual value |
| passed | BOOLEAN | NOT NULL | Whether check passed |
| verified_at | TIMESTAMPTZ | NOT NULL | |
| created_at | TIMESTAMPTZ | NOT NULL | |

### 5.9 `alerts` — Alert

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| application_id | UUID | FK → applications | |
| document_id | UUID | FK → documents | Nullable |
| validation_rule_id | UUID | FK → validation_rules | Nullable |
| alert_type | alert_type ENUM | NOT NULL | name_mismatch / income_mismatch, etc. |
| severity | severity_level ENUM | NOT NULL | |
| title | VARCHAR(200) | NOT NULL | |
| description | TEXT | | |
| field_name | VARCHAR(100) | | |
| status | alert_status ENUM | NOT NULL | open / in_review / resolved / escalated |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL | |

### 5.10 `alert_status_history` — Alert Status History

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| alert_id | UUID | FK → alerts | |
| from_status | alert_status | | Status before change |
| to_status | alert_status | NOT NULL | Status after change |
| changed_by | VARCHAR(100) | NOT NULL | Actor identifier (no users table in MVP) |
| notes | TEXT | | Review notes |
| changed_at | TIMESTAMPTZ | NOT NULL | Append-only; never updated |

---

## 6. Database Design Standards (Per Internship Guide §8)

| Standard | Implementation |
|----------|----------------|
| Clear table names | Lowercase, plural, snake_case; `applications` instead of `loan_applications` |
| Primary / foreign keys | All UUID with explicit FK constraints |
| Timestamps | All main tables include `created_at`, `updated_at` |
| Status enums | PostgreSQL ENUM types |
| Flexible OCR results | `extracted_data.raw_ocr_json`, `normalized_fields` as JSONB |
| Searchable fields | `extracted_field_values` as separate columns with indexes |
| Append-only audit logs | `alert_status_history` is INSERT-only; `audit_logs` deferred to Phase 2 |
| Avoid unnecessary sensitive data | `email_masked`, `phone_masked`; no full account numbers stored |

### JSON Columns vs Normal Columns — Decision Matrix

| Data | Storage | Rationale |
|------|---------|-----------|
| Raw Azure OCR response | `raw_ocr_json` JSONB | Structure varies by model; not queried directly |
| OpenAI normalised output | `normalized_fields` JSONB | Flexible field extension |
| Fields used for comparison / search | `extracted_field_values` columns | Supports indexes, JOINs, Dashboard aggregation |
| Raw fraud API response | `fraud_results.raw_response` JSONB | Debugging |
| Rule parameters | `validation_rules.rule_config` JSONB | Future configurability |

---

## 7. Migration Plan

### 7.1 Migration Files

| Order | File | Contents |
|-------|------|----------|
| 001 | `migrations/001_initial_schema.sql` | Enums, 10 MVP tables, indexes, triggers, default validation rule seeds |
| 002 | (Sprint 2 planned) `002_add_audit_logs.sql` | Minimal audit logging if required by client |
| 003 | (Sprint 3 planned) `003_dashboard_views.sql` | Dashboard aggregation views |

### 7.2 Execution

```bash
# Run inside the Supabase PostgreSQL container
psql -U postgres -d smartfinn -f migrations/001_initial_schema.sql
```

### 7.3 Rollback Strategy

- **Development:** `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` then re-run 001
- **Production / demo:** Pair each migration with a `down` script (from 002 onwards)

### 7.4 Supabase Integration

- Tables hosted on self-hosted Supabase PostgreSQL
- Files stored in Supabase Storage; `documents.storage_path` holds the bucket path
- Node.js DAL accesses data via `@supabase/supabase-js`

---

## 8. Database Naming Convention

| Category | Convention | Example |
|----------|------------|---------|
| Table names | Lowercase plural, snake_case | `clients`, `extracted_field_values` |
| Primary key | Always `id`, UUID | `id UUID PRIMARY KEY` |
| Foreign key columns | `{singular_table}_id` | `client_id`, `application_id` |
| Enum types | `{meaning}_type` or `{meaning}_status` | `loan_type`, `ocr_status` |
| Timestamps | `created_at`, `updated_at` | All main entity tables |
| Booleans | `is_` prefix | `is_mandatory`, `is_active` |
| Indexes | `idx_{table}_{column}` | `idx_applications_confidence` |
| Triggers | `trg_{table}_{action}` | `trg_applications_updated_at` |
| Rule codes | UPPER_SNAKE_CASE | `NAME_MATCH`, `ABR_ENTITY` |
| OCR field names | Lowercase snake_case, normalised | `employer_name`, `gross_income` |

---

## 9. Sample Extracted Data JSON

See `samples/sample-extracted-data-payslip.json`.

**Write flow:**

1. n8n WF1 completes OCR → insert into `extracted_data` (`raw_ocr_json` + `normalized_fields`)
2. Iterate `normalized_fields` → batch insert into `extracted_field_values`
3. Compute `avg_confidence_pct` → update `extracted_data`
4. Aggregate confidence across all documents → update `applications.overall_confidence_pct`

---

## 10. Open Items for Team Confirmation

| Question | Owner | Status |
|----------|-------|--------|
| Loan type × mandatory documents → `documents.is_mandatory` logic | Alan + Jiawen | Pending Workstream 2 matrix |
| Final OCR field name list → `extracted_field_values.field_name` | Haomiao | Pending OCR mapping document |
| Risk scoring formula → when to compute `applications.risk_score` | Jiawen | Pending matching rules document |
| API path: `/applications` vs `/cases` | Huaiyu + Shuyang | Recommend standardising on `/applications` |
| Whether to include minimal `audit_logs` in MVP | Alan + client | Currently OOS |

---

## 11. Review and Next Steps

- [ ] Alan confirms `applications` business fields are complete
- [ ] Haomiao confirms OCR JSON structure and `normalized_fields` format
- [ ] Huaiyu confirms DAL / Repository mapping to tables
- [ ] Jiawen confirms seed `validation_rules` cover the matching rules draft
- [ ] Jerry confirms Dashboard query fields (`overall_confidence_pct`, `risk_level`, alerts count)

**Export ERD:** Open `ERD.drawio` in Draw.io → Export PNG → embed in Proposal / TSD.
