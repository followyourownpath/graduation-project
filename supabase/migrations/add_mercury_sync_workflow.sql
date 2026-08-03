begin;

-- 1. 扩展 approved_fact_find_data 表
alter table public.approved_fact_find_data
  add column if not exists version integer not null default 1,
  add column if not exists source_hash text,
  add column if not exists schema_version text not null default '1';

-- 2. 扩展 crm_update_tracking 表
alter table public.crm_update_tracking
  add column if not exists approved_data_id uuid
    references public.approved_fact_find_data(id) on delete restrict,
  add column if not exists mapping_version text,
  add column if not exists correlation_id uuid default gen_random_uuid(),
  add column if not exists attempt_count integer not null default 0,
  add column if not exists next_attempt_at timestamptz,
  add column if not exists started_at timestamptz,
  add column if not exists completed_at timestamptz,
  add column if not exists last_error_code text,
  add column if not exists last_error_message text,
  add column if not exists payload_hash text;

-- 3. 新建 crm_update_item 表以追踪细分 CRM 对象操作
create table if not exists public.crm_update_item (
  id uuid primary key default gen_random_uuid(),
  crm_update_tracking_id uuid not null
    references public.crm_update_tracking(id) on delete cascade,
  sequence_number integer not null,
  entity_type text not null,          -- 'contact', 'opportunity', 'related_party', 'address', 'employment', 'income', 'asset', 'liability', 'extension'
  operation text not null,            -- 'create', 'update'
  local_reference text,               -- 本地主键或特定 key
  mercury_unique_id text,             -- CRM 唯一主键
  status text not null default 'pending', -- 'pending', 'completed', 'failed'
  attempt_count integer not null default 0,
  request_hash text,
  response_status integer,
  error_code text,
  error_message text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz default now()
);

-- 4. 索引优化
create index if not exists crm_update_item_tracking_idx
  on public.crm_update_item(crm_update_tracking_id, sequence_number);

-- 5. RLS 及安全配置
alter table public.crm_update_item enable row level security;

revoke all on table public.crm_update_item from anon;
grant select, insert, update, delete on table public.crm_update_item to authenticated, service_role;

create policy active_staff_select on public.crm_update_item for select to authenticated using (public.is_active_staff());
create policy active_staff_insert on public.crm_update_item for insert to authenticated with check (public.is_active_staff());
create policy active_staff_update on public.crm_update_item for update to authenticated using (public.is_active_staff()) with check (public.is_active_staff());
create policy admin_delete on public.crm_update_item for delete to authenticated using (public.is_staff_admin());

-- 6. 创建原子性审批并排队同步的任务 RPC 函数
create or replace function public.approve_submission_and_queue_crm_sync(
  p_submission_id uuid,
  p_approved_data_json jsonb,
  p_approved_by text,
  p_source_hash text,
  p_mapping_version text
)
returns table(approved_data_id uuid, tracking_id uuid)
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_crm_application_id uuid;
  v_version integer;
  v_approved_data_id uuid;
  v_tracking_id uuid;
begin
  -- A. 锁定 submission 并获取对应的 crm_application_id
  select crm_application_id
  into v_crm_application_id
  from public.fact_find_submission
  where id = p_submission_id
  for update;

  if not found then
    raise exception 'Submission not found' using errcode = 'P0002'; -- query_no_data
  end if;

  -- B. 计算版本号
  select coalesce(max(version), 0) + 1
  into v_version
  from public.approved_fact_find_data
  where fact_find_submission_id = p_submission_id;

  -- C. 冻结 approved 快照
  insert into public.approved_fact_find_data (
    fact_find_submission_id,
    approved_data_json,
    approval_status,
    approved_by,
    approved_at,
    version,
    source_hash,
    schema_version
  )
  values (
    p_submission_id,
    p_approved_data_json,
    'approved',
    p_approved_by,
    now(),
    v_version,
    p_source_hash,
    '1'
  )
  returning id into v_approved_data_id;

  -- D. 更新 submission 状态和同步状态
  update public.fact_find_submission
  set submission_status = 'approved',
      crm_sync_status = 'pending',
      updated_at = now()
  where id = p_submission_id;

  -- E. 创建 CRM 同步队列跟踪记录
  insert into public.crm_update_tracking (
    fact_find_submission_id,
    crm_application_id,
    approved_data_id,
    update_mode,
    update_status,
    updated_by,
    updated_at,
    mapping_version,
    attempt_count,
    created_at
  )
  values (
    p_submission_id,
    v_crm_application_id,
    v_approved_data_id,
    'writeback',
    'pending',
    p_approved_by,
    now(),
    p_mapping_version,
    0,
    now()
  )
  returning id into v_tracking_id;

  -- F. 记录审计事件
  insert into public.audit_event (
    fact_find_submission_id,
    crm_application_id,
    event_type,
    actor_type,
    actor_id,
    event_timestamp,
    event_details
  )
  values (
    p_submission_id,
    v_crm_application_id,
    'crm_update_required',
    'staff',
    p_approved_by,
    now(),
    jsonb_build_object(
      'approved_data_id', v_approved_data_id,
      'version', v_version,
      'tracking_id', v_tracking_id
    )
  );

  return query select v_approved_data_id, v_tracking_id;
end;
$$;

revoke all on function public.approve_submission_and_queue_crm_sync(uuid, jsonb, text, text, text) from public;
grant execute on function public.approve_submission_and_queue_crm_sync(uuid, jsonb, text, text, text) to authenticated;

commit;
