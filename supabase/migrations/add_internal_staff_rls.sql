begin;

create type public.staff_role as enum (
  'admin',
  'broker',
  'analyst',
  'reviewer'
);

create table public.staff_profile (
  user_id uuid primary key references auth.users(id) on delete cascade,
  full_name text,
  role public.staff_role not null default 'analyst',
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.staff_profile enable row level security;

create or replace function public.is_active_staff()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.staff_profile sp
    where sp.user_id = (select auth.uid())
      and sp.is_active
  );
$$;

create or replace function public.is_staff_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.staff_profile sp
    where sp.user_id = (select auth.uid())
      and sp.is_active
      and sp.role = 'admin'::public.staff_role
  );
$$;

revoke all on function public.is_active_staff() from public;
revoke all on function public.is_staff_admin() from public;
grant execute on function public.is_active_staff() to authenticated, service_role;
grant execute on function public.is_staff_admin() to authenticated, service_role;

revoke all on table public.staff_profile from anon;
grant select, insert, update, delete on table public.staff_profile to authenticated, service_role;

create policy staff_profile_read_own_or_admin
on public.staff_profile
for select
to authenticated
using (user_id = (select auth.uid()) or public.is_staff_admin());

create policy staff_profile_admin_insert
on public.staff_profile
for insert
to authenticated
with check (public.is_staff_admin());

create policy staff_profile_admin_update
on public.staff_profile
for update
to authenticated
using (public.is_staff_admin())
with check (public.is_staff_admin());

create policy staff_profile_admin_delete
on public.staff_profile
for delete
to authenticated
using (public.is_staff_admin());

do $$
declare
  table_name text;
  standard_tables text[] := array[
    'crm_application',
    'fact_find_submission',
    'crm_application_snapshot',
    'source_document',
    'document_page',
    'ocr_extraction_job',
    'extracted_field',
    'extracted_table',
    'extracted_table_cell',
    'applicant',
    'applicant_dependant',
    'applicant_address',
    'applicant_employment',
    'loan_requirements',
    'repayment_account',
    'property_asset',
    'financial_asset',
    'vehicle_asset',
    'other_asset',
    'liability',
    'monthly_expense',
    'customer_consent',
    'field_review',
    'approved_fact_find_data',
    'crm_update_tracking'
  ];
begin
  foreach table_name in array standard_tables loop
    execute format('revoke all on table public.%I from anon', table_name);
    execute format(
      'grant select, insert, update, delete on table public.%I to authenticated, service_role',
      table_name
    );

    execute format(
      'create policy active_staff_select on public.%I for select to authenticated using (public.is_active_staff())',
      table_name
    );
    execute format(
      'create policy active_staff_insert on public.%I for insert to authenticated with check (public.is_active_staff())',
      table_name
    );
    execute format(
      'create policy active_staff_update on public.%I for update to authenticated using (public.is_active_staff()) with check (public.is_active_staff())',
      table_name
    );
    execute format(
      'create policy admin_delete on public.%I for delete to authenticated using (public.is_staff_admin())',
      table_name
    );
  end loop;
end;
$$;

revoke all on table public.audit_event from anon;
grant select, insert on table public.audit_event to authenticated;
grant all on table public.audit_event to service_role;

create policy audit_event_staff_select
on public.audit_event
for select
to authenticated
using (public.is_active_staff());

create policy audit_event_staff_insert
on public.audit_event
for insert
to authenticated
with check (public.is_active_staff());

revoke all on table public.crm_field_mapping from anon;
grant select, insert, update, delete on table public.crm_field_mapping to authenticated, service_role;

create policy crm_field_mapping_staff_select
on public.crm_field_mapping
for select
to authenticated
using (public.is_active_staff());

create policy crm_field_mapping_admin_insert
on public.crm_field_mapping
for insert
to authenticated
with check (public.is_staff_admin());

create policy crm_field_mapping_admin_update
on public.crm_field_mapping
for update
to authenticated
using (public.is_staff_admin())
with check (public.is_staff_admin());

create policy crm_field_mapping_admin_delete
on public.crm_field_mapping
for delete
to authenticated
using (public.is_staff_admin());

commit;
