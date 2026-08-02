-- Read-only verification for Rules Engine Phase 1.
-- Fails loudly if required objects are missing.

do $$
begin
  if to_regclass('public.risk_assessment') is null then
    raise exception 'missing table public.risk_assessment';
  end if;
end $$;

do $$
declare
  missing text;
begin
  select string_agg(required.column_name, ', ')
  into missing
  from (
    values
      ('id'),
      ('fact_find_submission_id'),
      ('assessment_status'),
      ('overall_risk_score'),
      ('risk_level'),
      ('id_score'),
      ('payslip_score'),
      ('bank_statement_score'),
      ('noa_score'),
      ('ruleset_version'),
      ('report_json'),
      ('assessed_by'),
      ('assessed_at'),
      ('error_message'),
      ('created_at'),
      ('updated_at')
  ) as required(column_name)
  left join information_schema.columns c
    on c.table_schema = 'public'
   and c.table_name = 'risk_assessment'
   and c.column_name = required.column_name
  where c.column_name is null;

  if missing is not null then
    raise exception 'risk_assessment missing columns: %', missing;
  end if;
end $$;

do $$
begin
  if not exists (
    select 1
    from pg_class
    where oid = 'public.risk_assessment'::regclass
      and relrowsecurity
  ) then
    raise exception 'RLS is not enabled on public.risk_assessment';
  end if;
end $$;

do $$
declare
  missing text;
begin
  select string_agg(required.policyname, ', ')
  into missing
  from (
    values
      ('risk_assessment_active_staff_select'),
      ('risk_assessment_active_staff_insert'),
      ('risk_assessment_active_staff_update')
  ) as required(policyname)
  left join pg_policies p
    on p.schemaname = 'public'
   and p.tablename = 'risk_assessment'
   and p.policyname = required.policyname
  where p.policyname is null;

  if missing is not null then
    raise exception 'risk_assessment missing policies: %', missing;
  end if;
end $$;

do $$
declare
  missing text;
begin
  select string_agg(required.indexname, ', ')
  into missing
  from (
    values
      ('risk_assessment_status_idx'),
      ('risk_assessment_score_idx'),
      ('risk_assessment_assessed_at_idx')
  ) as required(indexname)
  left join pg_indexes i
    on i.schemaname = 'public'
   and i.tablename = 'risk_assessment'
   and i.indexname = required.indexname
  where i.indexname is null;

  if missing is not null then
    raise exception 'risk_assessment missing indexes: %', missing;
  end if;
end $$;

do $$
begin
  if not exists (
    select 1
    from information_schema.triggers
    where event_object_schema = 'public'
      and event_object_table = 'risk_assessment'
      and trigger_name = 'risk_assessment_set_updated_at'
  ) then
    raise exception 'missing trigger risk_assessment_set_updated_at';
  end if;
end $$;

select 'risk_assessment verification passed' as status;
