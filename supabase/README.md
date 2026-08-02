# SmartFinn Supabase

This directory contains the versioned database schema, restricted operational helpers, read-only verification queries, and manual access tests for SmartFinn.

## Directory layout

```text
supabase/
├── migrations/       Versioned database and Storage changes
├── admin/            Restricted manual administration helpers
├── verification/     Read-only schema and RLS checks
└── tests/manual/     Optional browser-based manual tests
```

## Migrations

The current migration files are:

1. `migrations/create_smartfinn_schema.sql`
2. `migrations/add_internal_staff_rls.sql`
3. `migrations/add_document_storage_and_intake_rpc.sql`
4. `migrations/add_ocr_response_storage.sql`
5. `migrations/add_rules_engine_phase1.sql` — `risk_assessment` table for Rules Engine Phase 1

Apply migrations in dependency order. Review their hosted-project status before running them: the initial schema and staff RLS migrations were originally executed manually in the Supabase SQL Editor, so the Supabase CLI migration history may not contain a matching baseline.

Do not run `supabase db push` against the existing hosted project until local and remote migration history have been compared and a baseline has been established.

## Administrative helpers

Files under `admin/` are manual, privileged operational tools. They are committed for auditability and reproducibility, but they are not migrations, browser code, API endpoints, or PostgreSQL RPC functions.

Only a trusted project/database administrator should execute them. See `admin/README.md` before use.

## Verification

Files under `verification/` contain read-only SQL checks. They do not create, update, or delete application data.

Rules Engine Phase 1 verification:

```bash
# After applying add_rules_engine_phase1.sql
psql "$DATABASE_URL" -f supabase/verification/verify_rules_engine_phase1.sql
```

REST resource for backend upserts: `/rest/v1/risk_assessment` with `on_conflict=fact_find_submission_id`.

Expected values for the original database and staff authorization setup were:

- 27 business tables
- 32 foreign keys
- 28 RLS-enabled public tables after adding `staff_profile`
- 110 RLS policies
- 0 anonymous public-table privileges
- at least 1 active administrator

Counts can increase when later migrations add tables or policies. Treat the migration-specific assertions as the source of truth for newer schema changes.

## Manual tests

`tests/manual/test_staff_access.html` verifies that anonymous access is rejected and that an authenticated active employee can read their profile and a standard business table.

The page is a local diagnostic tool and is not part of the production frontend.

## Security rules

- Never commit a database password, secret key, `service_role` key, access token, employee password, or populated `.env` file.
- Frontend code may use the project URL and Publishable key, with RLS enabled and tested.
- Secret/service-role credentials belong only in trusted backend environment variables.
- Creating an Auth user does not grant SmartFinn access; an active `staff_profile` is also required.
- Do not expose the admin SQL helpers as public RPC functions.
- Prefer pull-request review for changes under `migrations/` and `admin/`.

## Related documentation

See `../docs/backend-handoff.md` for the database model, RLS design, known limitations, and backend implementation notes.
