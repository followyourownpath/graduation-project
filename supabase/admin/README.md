# Restricted Supabase Administration Scripts

These SQL files are operational administration helpers. Their source code is not a credential, so it can be version-controlled for review and reproducibility. The security boundary is who can access the hosted Supabase project, SQL Editor, database credentials, or trusted backend administration endpoints.

## Files

### `bootstrap_first_admin.sql`

- Purpose: establish the first active SmartFinn administrator after the corresponding user has been created in Supabase Auth.
- Normal usage: once per new environment.
- Effect: inserts or updates `public.staff_profile` with `role = admin` and `is_active = true`.
- Do not use it to add ordinary employees.

### `add_staff_member.sql`

- Purpose: add or update an existing Supabase Auth user in `public.staff_profile`.
- Allowed roles: `broker`, `analyst`, `reviewer`, and `admin`.
- Recommended default for general frontend testing: `analyst`.
- Use `admin` only when the employee genuinely needs employee-management, delete, or CRM field-mapping administration privileges.

## Required execution process

1. Confirm the person already exists under `Authentication -> Users`.
2. Confirm the exact email and intended SmartFinn role through an approved team channel.
3. Edit only the documented input variables in the relevant script.
4. Review the final SQL before execution.
5. Run it from the hosted Supabase SQL Editor or another trusted administrative environment.
6. Verify the returned `staff_profile` row and `is_active` status.
7. Remove any real email entered into a working copy before committing changes.

## Prohibited usage

- Do not place database passwords, API secret keys, or employee passwords in these files.
- Do not execute these scripts from the browser frontend.
- Do not convert these scripts into public or broadly executable RPC functions.
- Do not use the first-admin bootstrap script for routine onboarding.
- Do not grant `admin` solely to make testing easier.

## Repository controls

For a shared repository, use pull-request review and optionally `CODEOWNERS` for `supabase/admin/` and `supabase/migrations/`. `CODEOWNERS` controls review responsibility, not who can read the files.
