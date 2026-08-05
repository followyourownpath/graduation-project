# Rules Engine Phase 1 后端开发交接

> 负责人：后端开发者  
> 开始前必读：`RULES_ENGINE_PHASE1_MASTER_PLAN.md` 和 `RULES_ENGINE_PHASE1_DATABASE_HANDOFF.md`  
> 目标：基于 approved submission 执行冻结的 13 条规则，覆盖保存风险结果，对前端提供稳定 API。

## 1. 后端实施要求

1. 完整阅读两份前置文档，不得改变 13 条规则、分数公式或 API JSON 字段名。
2. 阅读现有：
   - `backend/app/__init__.py`
   - `backend/app/routes/review.py`
   - `backend/app/services/review.py`
   - `backend/app/services/ocr_pipeline.py`
   - `backend/app/normalization/*.py`
   - `backend/app/normalization/fact_find_mapping.json`
   - `backend/tests/conftest.py`
   - `backend/tests/test_review.py`
   - `docs/API_CONTRACT.md`
3. 使用现有 `requests + Supabase PostgREST` 风格，不在 Phase 1 引入 ORM、Celery、Redis 或新网络服务。
4. 规则核心必须是不发网络请求的纯 Python 函数，数据读写必须通过 repository/service 边界。
5. 保留现有错误格式 `{"error":{"code","message"}}`，不向客户端泄露 Supabase 或原始异常。

## 2. 交付文件

建议新增：

```text
backend/app/routes/rules_engine.py
backend/app/services/rules_engine.py
backend/app/rules/__init__.py
backend/app/rules/models.py
backend/app/rules/normalizers.py
backend/app/rules/resolvers.py
backend/app/rules/phase1.py
backend/app/rules/scoring.py
backend/tests/test_rules_engine_rules.py
backend/tests/test_rules_engine_service.py
backend/tests/test_rules_engine_routes.py
```

必须更新：

```text
backend/app/__init__.py
backend/app/services/review.py
backend/tests/test_review.py
docs/API_CONTRACT.md
```

如 Approval gate 在本 PR 同时加强，还需更新：

```text
backend/app/routes/review.py
backend/tests/test_review.py
```

## 3. 模块边界

### 3.1 `models.py`

定义内部数据结构，推荐 `dataclass`：

```python
@dataclass(frozen=True)
class FieldValue:
    field_id: str
    source_document_id: str
    field_key: str
    raw_value: str | None
    normalised_value: str | None
    applicant_number: int | None
    mapped_table: str | None
    mapped_column: str | None

    @property
    def comparison_value(self):
        return self.normalised_value if self.normalised_value is not None else self.raw_value


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    label: str
    status: str
    fact_find_field_keys: list[str]
    document_field_keys: list[str]
    fact_find_value: str | None
    document_value: str | None
    normalised_fact_find_value: str | None
    normalised_document_value: str | None
    comparison: dict
    message: str
```

### 3.2 `normalizers.py`

仅包含可测试的确定性函数：

```python
normalize_name(value) -> str | None
normalize_entity(value) -> str | None
normalize_address(value) -> NormalizedAddress | None
normalize_identifier(value) -> str | None
parse_iso_date(value) -> date | None
parse_money(value) -> Decimal | None
similarity(left, right) -> Decimal
```

不要直接复用 Review API 里伪造的 confidence。Approved 输入视为已经人工审核，Rules Engine 只使用最终值。

`similarity` 必须选择 Python 标准库可重现算法，例如 `difflib.SequenceMatcher`，并在测试中锁定输出。不得在 Phase 1 调用 LLM 或外部模糊匹配 API。

### 3.3 `resolvers.py`

将扁平 `extracted_field` 解析成规则输入：

```python
resolve_applicants(fact_find_fields)
resolve_addresses(fact_find_fields, applicant_number)
resolve_employments(fact_find_fields, applicant_number)
resolve_repayment_account(fact_find_fields)
resolve_savings_assets(fact_find_fields)
bind_document_to_applicant(document_type, fields, applicants)
```

优先结合 `field_key`、`mapped_table`、`mapped_column`、`applicant_number`解析，不要只依赖 UI label。

Fact Find 关键字段的现有 key 约定：

```text
cover_form_date
applicant_1_full_name
applicant_2_full_name
applicant_{n}_current_address_street
applicant_{n}_current_address_suburb
applicant_{n}_current_address_state
applicant_{n}_current_address_postcode
applicant_{n}_previous_address_{sequence}_*
applicant_{n}_current_employment_employer_name
applicant_{n}_current_employment_start_date
applicant_{n}_secondary_employment_employer_name
applicant_{n}_secondary_employment_start_date
repayment_account_name
repayment_account_bsb
repayment_account_number
savings_term_deposit_{sequence}_value
```

实施前必须用 `fact_find_mapping.json` 确认实际 key；如与本文不同，在 resolver 中兼容真实 key 并同步更新文档，不得猜测一个新 key。

### 3.4 `phase1.py`

仅定义总体计划中的 13 条规则。推荐静态 registry：

```python
PHASE1_RULE_IDS = (
    "FF-ID-001", "FF-ID-002", "FF-ID-003",
    "FF-PS-001", "FF-PS-002", "FF-PS-003",
    "FF-BS-001", "FF-BS-002", "FF-BS-003", "FF-BS-004", "FF-BS-006",
    "FF-NOA-001", "FF-NOA-002",
)
```

测试必须断言 registry 长度恰好为 13，防止意外加入其他规则。

### 3.5 `scoring.py`

只负责聚合，不查数据库：

```python
score_document(rule_results) -> 0 | 25
score_assessment(document_results) -> 0 | 25 | 50 | 75 | 100
risk_level_for_score(score) -> low | lower | medium | higher | high
```

## 4. Supabase repository 实现

`SupabaseRulesEngineRepository` 建议放在 `services/rules_engine.py`，保持与现有 service 相同的 `_request/_require_ok` 风格。

### 4.1 必须提供的方法

```python
get_submission(token, submission_id)
get_application(token, application_id)
get_documents(token, submission_id)
get_latest_completed_job(token, document_id)
get_fields_for_job(token, job_id)
get_assessment(token, submission_id)
upsert_processing_assessment(token, submission_id, assessed_by)
complete_assessment(token, submission_id, payload)
fail_assessment(token, submission_id, error_message, assessed_by)
get_assessments_by_submission_ids(token, submission_ids)
```

### 4.2 字段查询必须包含

```text
id
source_document_id
section_name
applicant_number
field_key
field_label
raw_value
normalised_value
data_type
confidence
mapped_table
mapped_column
review_status
```

Rules Engine 不得通过现有 `GET /documents/{id}/extracted-data` 获取输入，因为该 Review API 为 UI 折叠了 raw/normalised 值，也没有返回 applicant 和 mapping 信息。

### 4.3 Upsert

PostgREST 请求要点：

```text
POST /rest/v1/risk_assessment?on_conflict=fact_find_submission_id
Prefer: resolution=merge-duplicates,return=representation
```

开始评分时先 upsert：

```json
{
  "fact_find_submission_id": "...",
  "assessment_status": "processing",
  "overall_risk_score": null,
  "risk_level": null,
  "id_score": null,
  "payslip_score": null,
  "bank_statement_score": null,
  "noa_score": null,
  "ruleset_version": "phase1-v1",
  "report_json": {},
  "assessed_by": "...",
  "assessed_at": null,
  "error_message": null
}
```

成功时 PATCH/UPSERT completed payload；异常时尽力将同一行写为 `failed`。不要先 DELETE 再 INSERT。

## 5. 评分 service 流程

`RulesEngineService.assess(token, submission_id, assessed_by)` 必须严格按以下顺序：

1. 验证 UUID。
2. 查询 submission；不存在返回 404。
3. 验证 `submission_status == approved`；否则 409 `submission_not_approved`。
4. 查询 submission 下的全部 source documents。
5. 对五种 Phase 1 document type 验证“恰好一份”；缺失或重复返回 409。
6. 查询每份文件最新 completed OCR job；缺失返回 409。
7. 查询五组 extracted fields。
8. 检查总体计划中的必需字段。缺失时 409，不得开始 processing row，避免覆盖一份旧的成功报告。
9. 所有前置条件通过后，upsert `processing`。
10. 解析 Fact Find applicants 和业务输入。
11. 逐文件绑定 applicant，执行对应规则。
12. 计算四个文件分数、总分和 risk level。
13. 构建冻结的 report JSON。
14. upsert `completed`。
15. 返回与 GET 完全相同的 API response。

一个重要要求：如果重新评分的新输入前置校验失败，不要覆盖旧的 completed report。只有真正开始规则执行后才更新评分行。

## 6. 规则实现要点

### 6.1 `FF-ID-001`, `FF-PS-001`, `FF-BS-001`, `FF-NOA-001`

这四条同时负责文件主体绑定。

- 先与 Applicant 1/2 分别计算。
- 最高分 >= 0.95 则匹配。
- 如两个 applicant 标准化后同名，非 Bank 文件无法唯一绑定：姓名规则可 pass，`matched_applicant_numbers=[1,2]`，其他 applicant-level 规则使用“任一完整 applicant 记录整体通过”，不得拼接两人的单个字段。
- Bank holder 包含额外联名持有人时允许通过。

### 6.2 `FF-ID-002`, `FF-NOA-002`

- 组装 Fact Find 当前和历史地址，保留每个原始 field key。
- 对每个候选地址比较，使用最高分。
- NOA address 为空时 `not_applicable`。
- ID address 是必需字段，缺失应在前置校验阻止。

### 6.3 `FF-ID-003`

- 日期必须严格解析；解析失败不得当作过期。
- 解析失败在 approved 输入中应视为 service error/incomplete，整次评分失败，不产生风险分。

### 6.4 `FF-PS-002`, `FF-PS-003`

- 对已绑定 applicant 的 current 和 secondary employment 记录计算 employer similarity。
- `FF-PS-002` 选择最高分的一整条 employment 记录并记录它的 key。
- `FF-PS-003` 必须使用同一条 employment 的 `start_date`，禁止另选其他 employer 的日期。

### 6.5 `FF-BS-002` 至 `FF-BS-004`

- repayment account 是 submission-level Fact Find 数据，不需 applicant 绑定。
- `FF-BS-004` 的遮盖账号依赖同一次运行中 `FF-BS-002` 和 `FF-BS-003` 的 pass 结果。
- 账号和 BSB 禁止模糊比较。

### 6.6 `FF-BS-006`

- 解析 savings/term deposit 候选记录。
- 无候选返回 `not_applicable`。
- 对每个候选计算差异，取最小差异的一条作为证据。
- savings 用 10% 阈值；term deposit 用 1 AUD 绝对阈值。
- 报告 comparison 必须写明选择类型、绝对差、比例差和阈值。

## 7. Flask API

### 7.1 Blueprint

```python
rules_engine_bp = Blueprint("rules_engine", __name__, url_prefix="/api/v1")
```

路由：

```text
POST /submissions/<submission_id>/risk-assessment
GET  /submissions/<submission_id>/risk-assessment
```

两者都使用 `@require_staff`。在 `create_app` 中注册 blueprint，并支持测试注入 `rules_engine_service=None`。

### 7.2 错误码

| HTTP | code | 条件 |
|---:|---|---|
| 400 | `invalid_submission_id` | 非 UUID |
| 404 | `submission_not_found` | submission 不存在 |
| 404 | `risk_assessment_not_found` | GET 时尚未评分 |
| 409 | `submission_not_approved` | 未 approved |
| 409 | `phase1_documents_missing` | 缺少必需文件 |
| 409 | `phase1_duplicate_document_type` | 同类文件多于一份 |
| 409 | `phase1_extraction_incomplete` | OCR job 未完成 |
| 409 | `phase1_required_fields_missing` | 必需字段缺失 |
| 502 | `risk_assessment_storage_failed` | Supabase 读写失败 |
| 500 | `risk_assessment_failed` | 未预期执行错误，不泄露内部异常 |

409 错误的 response 应在 `error.details` 中提供可操作的缺失项，例如：

```json
{
  "error": {
    "code": "phase1_required_fields_missing",
    "message": "The approved submission is missing fields required by Phase 1.",
    "details": {
      "bank_statement_3m": ["account_number"]
    }
  }
}
```

## 8. 扩展现有 Submission API

`SupabaseReviewService.list_submissions` 和 `get_submission` 目前把风险字段硬编码为 `None`。必须改为查询 `risk_assessment`。

列表场景：

1. 先查当页 submissions。
2. 用一次 PostgREST `fact_find_submission_id=in.(...)` 查评分，禁止逐行 N+1。
3. 按 submission id 映射。
4. 无评分行时：

```json
{
  "assessment_status": "not_started",
  "overall_risk_score": null,
  "risk_level": null,
  "assessed_at": null
}
```

5. 有行时返回实际列值。

Application detail 同样增加这四个字段。

## 9. Approval gate

业务假设是“approved 表示 OCR 已人工审核”，但当前 API 只改 submission status。本 Phase 1 至少必须保证：

- `PUT /submissions/{id}/status` 改为 approved 前，检查五类文件恰好一份。
- 检查每份 OCR 已 completed。
- 检查 Phase 1 必需字段存在。
- 不要要求 NOA address 或 savings asset 必须存在，它们可以 N/A。

为避免 Approval route 与 Rules Engine 重复两套校验，将检查封装为可复用的 `validate_phase1_readiness(...)`。Rules Engine POST 仍必须再调一次以防止绕过。

## 10. 测试计划

### 10.1 Normalizer tests

至少覆盖：

- `MR Alice J. Smith` vs `ALICE J SMITH`。
- 标点、连字符、多空格。
- 不同姓不得因去词而相同。
- `Example Pty. Ltd.` vs `EXAMPLE`。
- `ST` vs `STREET`、街道号不同、postcode 不同。
- BSB 去连字符保留前导零。
- Decimal 金额和零基准。
- 日期解析失败。

### 10.2 13 条规则测试

每条至少：

- 1 个 pass case。
- 1 个 fail case。
- 有条件分支时增加 N/A/incomplete case。

额外必须覆盖：

- Applicant 2 的 Payslip 匹配 Applicant 2，而不是 mapper 默认的 1。
- 一份文件的姓名匹配 Applicant 1，其他字段不得借用 Applicant 2 通过。
- 联名 Bank holder 包含两个 applicant。
- 遮盖 account number 在 name/BSB 不通过时不得单独通过。
- 没有 savings asset 时 `FF-BS-006=not_applicable`。
- NOA 无 address 时 `FF-NOA-002=not_applicable`。

### 10.3 Scoring tests

- 13 条全 pass -> 0/low。
- 同一 ID 两条 fail -> ID 仍只 25，总分 25/lower。
- ID + Payslip fail -> 50/medium。
- 三类 fail -> 75/higher。
- 四类 fail -> 100/high。
- `not_applicable` 和 `incomplete` 不加分。

### 10.4 Service/repository tests

- 未 approved -> 409，不写 assessment。
- 缺文件/重复文件/OCR 未完成/必需字段缺失 -> 409。
- 首次评分创建 row。
- 第二次评分覆盖 row，id 可保持或变化，但同 submission 总行数必须为 1。
- 规则异常 -> assessment failed 且 API 不泄露栈追踪。
- GET 无记录 -> 404。
- list submissions 用批量查询并返回真实分数。

### 10.5 Route/auth tests

- 无 Bearer token -> 401。
- 非 UUID -> 400。
- POST/GET 响应 shape 与总体计划一致。
- report 中 4 个 document results 都存在，规则总数恰好 13。

## 11. 命令级验证

在 `backend` 下执行：

```bash
python -m compileall app tests
python -m pytest -q
```

如共享 Supabase 已应用 migration，再用一个 approved 测试 submission 做 smoke test：

```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/v1/submissions/<uuid>/risk-assessment

curl \
  -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/v1/submissions/<uuid>/risk-assessment
```

不要在命令、日志或 test snapshot 中输出 TFN、完整账号或 Supabase token。

## 12. 给前端的交接内容

Backend PR 完成时必须提供：

- 可访问的 backend base URL。
- 一个 approved + not_started submission ID。
- 一个 completed 0 分 submission ID。
- 一个 completed 25/50 分 submission ID。
- 一个 readiness 409 submission ID。
- `docs/API_CONTRACT.md` 已更新的 endpoint 和完整 JSON。
- 明确说明 API risk level 使用 lowercase code，前端负责显示文案。

## 13. 后端 Definition of Done

- [ ] 只注册 13 条规则，规则 ID 与总体计划一致。
- [ ] 标准化、resolver、rule、scoring 都与数据库 IO 解耦。
- [ ] 人工修正后的 `normalised_value` 优先参与比较。
- [ ] Applicant 1/2 按文件主体动态绑定，不依赖写死的 applicant number。
- [ ] 实现 POST/GET risk-assessment 并使用 `@require_staff`。
- [ ] 重新评分 upsert 覆盖，不删除后重建。
- [ ] Submission list/detail 不再返回硬编码 null risk fields。
- [ ] Approval 和 assessment 共用 readiness validator。
- [ ] 错误码和 JSON 契约稳定。
- [ ] 所有新测试和现有 backend pytest 通过。
- [ ] `docs/API_CONTRACT.md` 已与实现同步。
- [ ] 已向前端提供联调环境和样例 submission。
