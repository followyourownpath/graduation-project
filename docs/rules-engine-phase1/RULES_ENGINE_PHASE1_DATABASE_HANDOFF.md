# Rules Engine Phase 1 数据库开发交接

> 负责人：数据库开发者  
> 开始前必读：`RULES_ENGINE_PHASE1_MASTER_PLAN.md`  
> 目标：为每个 approved submission 持久化一份可覆盖的 Phase 1 风险评估。

## 1. 给 AI agent 的执行指令

1. 先阅读总体计划和以下现有文件：
   - `supabase/migrations/create_smartfinn_schema.sql`
   - `supabase/migrations/add_internal_staff_rls.sql`
   - `supabase/verification/verify_schema.sql`
   - `supabase/README.md`
2. 仅新增 Rules Engine Phase 1 需要的 migration、RLS 和 verification；不改 OCR 表、不实现 Flask/React。
3. 保留用户现有未提交文件，不重置工作区。
4. 不得将 `database-design/migrations/001_initial_schema.sql` 直接应用到 Supabase。它使用旧的 `applications/documents` 模型，与当前 `fact_find_submission/source_document` 不兼容。
5. 所有 SQL 必须可重新从空 Supabase 环境按 migration 顺序执行。

## 2. 交付文件

必须新增：

```text
supabase/migrations/add_rules_engine_phase1.sql
supabase/verification/verify_rules_engine_phase1.sql
```

必须更新：

```text
supabase/README.md
```

可选更新 `supabase/verification/verify_schema.sql`，将 `risk_assessment` 加入总表清单；但独立 verification 文件仍必须存在。

## 3. 目标表结构

仅新增一张表 `public.risk_assessment`。不新增规则定义表或历史表。13 条规则由后端代码版本管理，详细结果存在 `report_json`。

### 3.1 规范 SQL

AI agent 应以下列 SQL 为准实现；可增加注释，不得擅自改列名或枚举值。

```sql
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
  'Versioned Phase 1 report payload; shape is defined by docs/RULES_ENGINE_PHASE1_MASTER_PLAN.md.';

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
```

### 3.2 为什么不给 authenticated DELETE

Phase 1 的“覆盖旧评分”通过 upsert/update 完成，不需要删除记录。禁止普通 staff 删除评分可减少误操作；`service_role` 保留维护能力。

## 4. 数据不变式

数据库必须保证：

1. 一个 `fact_find_submission_id` 最多一条评分。
2. 完成评分的 `overall_risk_score` 必须等于四个文件分数之和。
3. 四个文件分数只能是 0 或 25。
4. 总分只能是 0/25/50/75/100。
5. `completed` 必须有分数、risk level 和 `assessed_at`。
6. `failed` 必须有非空 `error_message`。
7. 更新记录时 `updated_at` 自动变更。
8. 删除 submission 时评分自动 cascade 删除。

## 5. RLS 和权限要求

当前后端用用户 Supabase JWT 调用 PostgREST，因此 upsert 需要 authenticated 同时拥有：

- SELECT：upsert 冲突检测和返回记录。
- INSERT：首次评分。
- UPDATE：重新评分覆盖。

所有 authenticated policy 必须要求 `public.is_active_staff()`。不向 anon 暴露任何权限。

不要在数据库中推导或验证 `submission_status=approved`；这是后端业务前置条件，并且 PostgREST upsert 不应被复杂 trigger 绑定。

## 6. Verification SQL

`supabase/verification/verify_rules_engine_phase1.sql` 必须是只读验证，不留下业务数据。至少检查：

### 6.1 表、列和约束

```sql
select to_regclass('public.risk_assessment');

select column_name, data_type, is_nullable
from information_schema.columns
where table_schema = 'public'
  and table_name = 'risk_assessment'
order by ordinal_position;

select conname, pg_get_constraintdef(oid)
from pg_constraint
where conrelid = 'public.risk_assessment'::regclass
order by conname;
```

### 6.2 RLS 和 policy

```sql
select relrowsecurity
from pg_class
where oid = 'public.risk_assessment'::regclass;

select policyname, cmd, roles, qual, with_check
from pg_policies
where schemaname = 'public'
  and tablename = 'risk_assessment'
order by policyname;
```

### 6.3 索引和 trigger

```sql
select indexname, indexdef
from pg_indexes
where schemaname = 'public'
  and tablename = 'risk_assessment'
order by indexname;

select trigger_name, event_manipulation
from information_schema.triggers
where event_object_schema = 'public'
  and event_object_table = 'risk_assessment';
```

Verification 应用 `do $$ ... raise exception ... $$` 对缺少对象主动失败，不应只输出供人工观察。

## 7. 本地/共享环境验证顺序

1. 在新建或可抛弃 Supabase/Postgres 环境按现有顺序应用全部 migrations。
2. 应用 `add_rules_engine_phase1.sql`。
3. 运行现有 `verify_schema.sql`。
4. 运行 `verify_rules_engine_phase1.sql`。
5. 用 active staff JWT 或 Supabase SQL 测试 INSERT、SELECT、UPDATE。
6. 以同一 `fact_find_submission_id` 执行两次 upsert，确认总行数仍为 1。
7. 尝试插入 30 分、单文件 10 分或不合法 risk level，确认约束拒绝。
8. 尝试写入 `completed` 但缺少分数，确认约束拒绝。

## 8. 给后端的交接内容

Database PR 就绪后，向后端开发者提供：

- migration 文件和 commit hash。
- 已应用 migration 的 Supabase 环境名。
- 实际 REST resource：`/rest/v1/risk_assessment`。
- 确认 `on_conflict=fact_find_submission_id` 可用。
- 确认 authenticated active staff 可 select/insert/update。
- 一个合法 completed row 的样例 JSON。

合法 row 样例：

```json
{
  "fact_find_submission_id": "submission-uuid",
  "assessment_status": "completed",
  "overall_risk_score": 25,
  "risk_level": "lower",
  "id_score": 25,
  "payslip_score": 0,
  "bank_statement_score": 0,
  "noa_score": 0,
  "ruleset_version": "phase1-v1",
  "report_json": {"document_results": []},
  "assessed_by": "staff-user-uuid",
  "assessed_at": "2026-08-02T10:30:00Z",
  "error_message": null
}
```

## 9. 回滚说明

Supabase migration 应优先前向修复，不要在共享环境随意 drop。如在未有业务数据的演示环境必须回滚，手工顺序是：

```sql
drop trigger if exists risk_assessment_set_updated_at
  on public.risk_assessment;
drop function if exists public.set_risk_assessment_updated_at();
drop table if exists public.risk_assessment;
```

执行回滚前必须确认目标环境和数据可恢复性。

## 10. 数据库 Definition of Done

- [ ] migration 仅依赖当前正式 Supabase schema。
- [ ] 表名和列名与本文一致。
- [ ] `fact_find_submission_id` 唯一约束存在。
- [ ] 分数、risk level、completed/failed 完整性约束生效。
- [ ] 三个索引和 updated_at trigger 生效。
- [ ] RLS 开启，anon 无权限，active staff 可 select/insert/update。
- [ ] 同一 submission upsert 两次后只有一行。
- [ ] verification SQL 可自动发现缺失的表、列、policy、index 或 trigger。
- [ ] `supabase/README.md` 包含 migration 和验证方法。
- [ ] 已将 migration 状态和 REST resource 交接给后端开发者。
