begin;

create table public.risk_assessment (
  id uuid primary key default gen_random_uuid(),

  fact_find_submission_id uuid not null unique
    references public.fact_find_submission(id) on delete cascade,

  assessment_status text not null default 'processing'
    check (assessment_status in ('processing', 'completed', 'failed')),

  overall_risk_score smallint
    check (overall_risk_score in (0, 25, 50, 75, 100)),

  risk_level text
    check (risk_level in ('low', 'lower', 'medium', 'higher', 'high')),

  id_score smallint
    check (id_score in (0, 25)),

  payslip_score smallint
    check (payslip_score in (0, 25)),

  bank_statement_score smallint
    check (bank_statement_score in (0, 25)),

  noa_score smallint
    check (noa_score in (0, 25)),

  ruleset_version text not null default 'phase1-v1',
  report_json jsonb not null default '{}'::jsonb,

  assessed_by text,
  assessed_at timestamptz,
  error_message text,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  check (
    assessment_status <> 'completed'
    or (
      overall_risk_score is not null
      and risk_level is not null
      and id_score is not null
      and payslip_score is not null
      and bank_statement_score is not null
      and noa_score is not null
      and assessed_at is not null
      and overall_risk_score =
        id_score + payslip_score + bank_statement_score + noa_score
    )
  ),

  check (
    assessment_status <> 'failed'
    or nullif(btrim(error_message), '') is not null
  )
);

comment on table public.risk_assessment is
  'Latest overwrite-only Rules Engine assessment for one Fact Find submission.';

comment on column public.risk_assessment.report_json is
  'Versioned Phase 1 report payload; shape is defined by RULES_ENGINE_PHASE1_MASTER_PLAN.';

create index risk_assessment_status_idx
  on public.risk_assessment(assessment_status);

create index risk_assessment_score_idx
  on public.risk_assessment(overall_risk_score desc)
  where assessment_status = 'completed';

create index risk_assessment_assessed_at_idx
  on public.risk_assessment(assessed_at desc);

create or replace function public.set_risk_assessment_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger risk_assessment_set_updated_at
before update on public.risk_assessment
for each row execute function public.set_risk_assessment_updated_at();

alter table public.risk_assessment enable row level security;

revoke all on table public.risk_assessment from anon;
grant select, insert, update on table public.risk_assessment
  to authenticated, service_role;
grant delete on table public.risk_assessment to service_role;

create policy risk_assessment_active_staff_select
on public.risk_assessment
for select
to authenticated
using (public.is_active_staff());

create policy risk_assessment_active_staff_insert
on public.risk_assessment
for insert
to authenticated
with check (public.is_active_staff());

create policy risk_assessment_active_staff_update
on public.risk_assessment
for update
to authenticated
using (public.is_active_staff())
with check (public.is_active_staff());

commit;
