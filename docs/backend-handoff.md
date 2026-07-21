# SmartFinn Backend Handoff

Last updated: 2026-07-19 (Australia/Sydney)

## 1. Purpose

This document hands the completed Supabase database foundation to the backend implementation phase. It is intended for developers, teammates, and new Codex chats working in the same repository.

No Supabase URL, API key, database password, employee password, email address, access token, or other credential is stored in this document or in the committed SQL templates.

## 2. Current status

The initial Supabase database and internal-staff authorization model have been created and tested successfully.

- The Supabase project already exists.
- Both migrations were applied manually through the Supabase SQL Editor.
- The base schema contains 27 business tables.
- `public.staff_profile` adds one authorization table, for 28 public tables total.
- The schema has 32 foreign keys.
- All 28 public tables have Row Level Security (RLS) enabled.
- The internal-staff model has 110 RLS policies.
- The `anon` database role has no public-table privileges.
- One active administrator has been created in `staff_profile`.
- Real login and Data API tests passed:
  - unauthenticated access was rejected;
  - employee email/password login succeeded;
  - the active administrator profile was readable;
  - the authenticated administrator could read `crm_application`.

Latest verification values:

| Check | Value |
|---|---:|
| Business tables found | 27 |
| Business tables missing | 0 |
| Foreign keys | 32 |
| Public tables after staff authorization | 28 |
| RLS-enabled public tables | 28 |
| RLS policies | 110 |
| Anonymous table privileges | 0 |
| Active administrators | 1 |

## 3. Source files

### Required migrations

- `supabase/migrations/create_smartfinn_schema.sql`
  - Creates the 27 business tables.
  - Creates primary keys, foreign keys, indexes, and UUID defaults.
  - Uses `timestamptz` for timestamp fields.
  - Enables RLS on every business table.
- `supabase/migrations/add_internal_staff_rls.sql`
  - Creates `public.staff_role`.
  - Creates `public.staff_profile` linked to `auth.users`.
  - Creates staff/admin helper functions.
  - Revokes anonymous table access.
  - Grants authenticated access through RLS policies.
- `supabase/migrations/add_document_storage_and_intake_rpc.sql`
  - Creates the private source-document bucket and its staff RLS policies.
  - Adds the transactional application-intake RPC.
- `supabase/migrations/add_ocr_response_storage.sql`
  - Creates the private OCR-response bucket and its staff RLS policies.

### Setup and verification helpers

- `supabase/bootstrap_first_admin.sql`
  - One-time bootstrap script for the first administrator.
  - Finds an existing Supabase Auth user by email.
  - Inserts or updates its `staff_profile` row with `role = admin` and `is_active = true`.
  - Must not be used for ordinary employees because it always assigns administrator privileges.
- `supabase/verify_schema.sql`
  - Read-only validation for the 27-table business schema.
- `supabase/verify_internal_staff_rls.sql`
  - Read-only validation for staff profiles, policies, RLS, anonymous access, and active administrators.
- `supabase/test_staff_access.html`
  - Optional manual diagnostic page used to test anonymous rejection, Auth login, staff-profile access, and business-table access.
  - It is not part of the production application and is not deployed by Supabase migrations.
  - It does not persist credentials, but it should be moved under a manual-test/tools directory or omitted from production packaging.

## 4. Data model summary

### CRM and submissions

- `crm_application`
- `fact_find_submission`
- `crm_application_snapshot`

`fact_find_submission` is the main aggregate root for most Fact Find data. Its `crm_application_id` refers to the internal UUID `crm_application.id`. The text field `crm_application.crm_application_id` stores the external CRM identifier.

### Documents and extraction

- `source_document`
- `document_page`
- `ocr_extraction_job`
- `extracted_field`
- `extracted_table`
- `extracted_table_cell`

This group supports uploaded source files, page-level content, OCR jobs, extracted scalar fields, detected tables, and table cells.

### Applicants

- `applicant`
- `applicant_dependant`
- `applicant_address`
- `applicant_employment`

### Loan, assets, liabilities, and expenses

- `loan_requirements`
- `repayment_account`
- `property_asset`
- `financial_asset`
- `vehicle_asset`
- `other_asset`
- `liability`
- `monthly_expense`

`loan_requirements`, `repayment_account`, and `customer_consent` have unique submission foreign keys, enforcing at most one row per submission.

### Consent, review, approval, CRM updates, and audit

- `customer_consent`
- `field_review`
- `approved_fact_find_data`
- `crm_update_tracking`
- `audit_event`
- `crm_field_mapping`

`approved_fact_find_data` remains one-to-many with a submission so it can support approval history or versions. `audit_event` has nullable references and uses `ON DELETE SET NULL` to retain audit rows if a referenced business object is removed.

## 5. Authentication and authorization

Supabase Auth and application authorization are separate layers:

1. `auth.users` authenticates a person and issues a JWT after login.
2. `public.staff_profile` determines whether that authenticated user is approved internal staff.
3. RLS policies check the authenticated user's ID through `auth.uid()` and the active staff profile.

Supported staff roles:

- `admin`
- `broker`
- `analyst`
- `reviewer`

Current permissions:

| Operation | Active staff | Admin |
|---|---:|---:|
| Read standard business tables | Yes | Yes |
| Insert standard business data | Yes | Yes |
| Update standard business data | Yes | Yes |
| Delete standard business data | No | Yes |
| Read own staff profile | Yes | Yes |
| Manage staff profiles | No | Yes |
| Read CRM field mappings | Yes | Yes |
| Modify CRM field mappings | No | Yes |
| Read and insert audit events | Yes | Yes |
| Update or delete audit events | No | No |

All active staff currently have organization-wide access to all business records. There is no branch-, broker-, or record-owner-level isolation yet.

The Supabase `service_role`/secret key bypasses RLS. It must only be used by trusted backend services and must never appear in browser code, mobile code, committed `.env` files, logs, screenshots, or chat messages.

## 6. Adding employees

Creating a user in `Authentication -> Users` only creates an authentication identity. It does not grant SmartFinn data access.

Every employee needs both:

1. an `auth.users` identity; and
2. an active `public.staff_profile` row with the intended role.

`bootstrap_first_admin.sql` is only for establishing the first administrator. Subsequent employees should be added by an administrator through a dedicated admin endpoint/UI or a separate role-aware administration script. Do not reuse the bootstrap script for ordinary employees.

## 7. Important migration-history warning

The two migrations were executed manually in the hosted Supabase SQL Editor. This creates the database objects but may not add matching entries to the Supabase CLI migration-history table.

Consequences:

- Do not immediately run `supabase db push` against the existing hosted project with these migration files.
- The CLI may try to apply them again and fail because the types, tables, or policies already exist.
- Before adopting the Supabase CLI workflow, create/repair a migration baseline and confirm local/remote migration status.
- After the baseline is established, all future schema changes should be new timestamped migrations committed to Git.

## 8. Known limitations and decisions still required

- Most status fields are currently `text`; allowed values have not been formalized as enums or check constraints.
- `updated_at` columns have defaults but no automatic update triggers.
- Monetary `numeric` fields do not yet specify precision/scale or non-negative checks.
- OCR confidence fields do not yet enforce a valid range.
- Business-required fields and `NOT NULL` rules are intentionally conservative and need domain review.
- Supabase Storage buckets and object policies have not been created.
- `storage_uri`, rendered page images, and OCR raw-response files are currently only represented by URI fields.
- Email invitation Site URL and Redirect URL configuration still needs production setup.
- There is no backend API, frontend application, admin employee-management UI, or automated test suite yet.
- There is no branch/broker ownership isolation; every active staff member can currently read and modify all standard business records.
- `customer_consent` has fixed `applicant_1_signed` and `applicant_2_signed` fields, which will not scale cleanly beyond two applicants.
- `crm_field_mapping` is configuration-driven and has no direct foreign-key relationship to business columns.

## 9. Recommended backend implementation order

1. Establish the Git repository and Supabase CLI migration baseline.
2. Choose and scaffold the backend framework/runtime.
3. Add environment-variable handling for the Supabase URL and server-only secret key.
4. Implement authentication middleware that validates Supabase user JWTs.
5. Implement staff-profile and role checks for protected administrative operations.
6. Add a safe employee-management endpoint/UI so admins can assign `broker`, `analyst`, `reviewer`, or `admin` roles.
7. Define request/response validation and service layers for applications, submissions, applicants, assets, liabilities, and expenses.
8. Create Supabase Storage buckets and policies for source documents, rendered pages, and OCR responses.
9. Implement the document/OCR pipeline and persistence into extraction tables.
10. Implement review, approval, CRM mapping, CRM update tracking, and audit-event workflows.
11. Add domain constraints, status definitions, `updated_at` triggers, and indexes based on real query patterns.
12. Add automated database, RLS, API, and integration tests before production deployment.

## 10. Suggested prompt for a new backend chat

> Read `docs/backend-handoff.md` and both files under `supabase/migrations/` before making changes. Treat the hosted Supabase schema and RLS migrations as already applied manually. Inspect the repository, propose a backend architecture and phased implementation plan, and do not expose or commit any Supabase secrets. Preserve the existing database and create new migrations for future schema changes.
