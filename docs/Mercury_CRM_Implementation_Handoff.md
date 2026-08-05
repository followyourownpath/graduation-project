# Mercury CRM 自动回传实施交接文档

> 面向读者：后续接手开发的开发人员、后端/前端实习生、测试人员
> 项目：SmartFINN AI Mortgage Application Automation  
> 文档日期：2026-08-02  
> 当前状态：**可以开始开发；尚未实现 Mercury 写回**  
> 配套调研：[Mercury_CRM_Writeback_Integration_Assessment.md](./Mercury_CRM_Writeback_Integration_Assessment.md)

---

## 0. 给接手者的 5 分钟说明

这个功能要解决的业务问题是：经纪人原来需要花约 1–1.5 小时，把客户 Fact Find 中的信息手工录入 Mercury CRM。SmartFINN 已经能上传文件、OCR 提取字段并允许工作人员修改。下一步是在工作人员点击 **Approve** 后，把最终确认的数据自动写进 Connective Mercury Nexus CRM。

当前代码中的 Approve **只修改本地状态**，没有调用 Mercury。你需要补齐以下链路：

```text
OCR/AcroForm 字段
  → 人工审核后的最终值
  → approved_data_json 不可变快照
  → Mercury payload 转换
  → 后台同步任务
  → Mercury POST/PUT
  → 保存 Mercury uniqueId
  → GET 回读验证
  → UI 显示同步成功或失败
```

第一次接手时不要直接从 UI 点 Approve 并期待 CRM 被写入；这条链路还不存在。

### 0.1 已经确认的关键 API 行为

- Mercury API 使用 Swagger 2.0，Host 为 `https://apis.connective.com.au`。
- Base path 为 `/mercury/v1`。
- Token 在 URL path，API Key 在 `x-api-key` header。
- 创建资源使用 POST，更新资源使用 PUT。
- Opportunity PUT 支持部分字段更新。
- 嵌套对象带 `uniqueId` 表示更新；不带表示创建；`isDeleted: true` 表示软删除。
- Living Expenses 和 Other Income 的 PUT 是 **整组替换**，必须先 GET、合并、再 PUT 完整列表。
- 当前 CRM 账号是测试账号，可以用于受控集成测试。
- 客户确认使用项目提供的旧版 Swagger，版本旧本身不是阻塞项。

### 0.2 Definition of Done（完成定义）

只有全部满足以下条件，功能才算完成：

- [ ] Approve 会生成一份不可变的 approved data snapshot。
- [ ] Approve 不直接阻塞等待所有 Mercury 请求，而是可靠地排队同步。
- [ ] 单申请人与双申请人都能创建/更新 Mercury Contact。
- [ ] 能创建 Opportunity 并保存返回的 Mercury `uniqueId`。
- [ ] 能建立 Primary/Secondary Applicant related parties。
- [ ] 至少支持 Address、Employment、Income、Asset、Liability。
- [ ] Living Expenses/Other Income 使用 GET-merge-PUT，不丢失已有行。
- [ ] 重试不会创建重复记录。
- [ ] 写入后执行 GET 回读并核对关键字段。
- [ ] UI 能显示 Pending/In Progress/Completed/Failed。
- [ ] API Key、Token、客户 PII 不进入 Git 或普通日志。
- [ ] 单元测试、后端测试、前端测试和测试账号 E2E 均通过。

---

## 1. 开发前必须阅读

按以下顺序阅读，不要只看本文件就开始写代码：

1. `docs/Mercury_CRM_Writeback_Integration_Assessment.md`
2. `docs/API_CONTRACT.md`
3. `docs/backend-handoff.md`
4. `docs/FactFind_Frontend_Handoff.md`
5. `backend/app/normalization/fact_find_mapping.json`
6. `backend/app/normalization/fact_find.py`
7. `backend/app/services/ocr_pipeline.py`
8. `backend/app/services/review.py`
9. `backend/app/routes/review.py`
10. `frontend/src/app/(dashboard)/application/[id]/page.js`
11. `supabase/migrations/create_smartfinn_schema.sql`

外部/客户资料：

- `/Users/liujiaqi/Documents/2026T2/COMP9900/UNSW/new/mercury-factfind-field-mapping.html`
- `/Users/liujiaqi/Documents/2026T2/COMP9900/UNSW/2. Data Modeling/Smartfinn Fact Find Field Mapping Matrix.docx`
- `/Users/liujiaqi/Documents/2026T2/COMP9900/UNSW/2. Data Modeling/Data Model Specification.docx`

官方 Connective 页面：

- Swagger：https://wiki.connective.com.au/en/articles/640-mercury-connect-api-swagger-2-0-update
- Opportunity CRUD：https://wiki.connective.com.au/en/articles/663-managing-opportunities-via-the-mercury-api
- Person POST 示例：https://wiki.connective.com.au/en/articles/24580-how-to-create-a-person-record-via-an-api-post-payload
- Opportunity POST 示例：https://wiki.connective.com.au/en/articles/25091-how-to-create-an-opportunity-record-via-an-api-post-payload
- Living Expenses：https://wiki.connective.com.au/en/articles/641-nexus-financials-living-expenses-endpoint
- Other Income：https://wiki.connective.com.au/en/articles/644-nexus-financials-other-income-endpoint
- Related Parties：https://wiki.connective.com.au/en/articles/658-managing-related-parties-via-the-mercury-api
- Assets：https://wiki.connective.com.au/en/articles/661-managing-assets
- Liabilities：https://wiki.connective.com.au/en/articles/659-managing-liabilities

### 1.1 资料优先级

资料冲突时按以下优先级处理：

1. 客户明确确认的测试账号实际行为。
2. Connective 官方 Wiki 的较新文章和示例。
3. 客户确认使用的 Swagger YAML。
4. 本地 `mercury-factfind-field-mapping.html`。
5. 团队推断。

任何“团队推断”都必须写成测试，并在测试账号验证后才能标记为 Confirmed。

---

## 2. 当前系统到底做到了哪里

### 2.1 已有能力

- Flask 后端和 Next.js 前端。
- Supabase Auth、Postgres、Storage。
- 上传 Fact Find 和支持文件。
- 电子 Fact Find 使用 AcroForm 直接读取。
- 扫描件使用 Azure Document Intelligence。
- `extracted_field` 保存 raw/normalised value、confidence、field key、目标表/列。
- 前端可以编辑字段，`field_review` 保存人工更正。
- 前端有 Approve/Reject 按钮。
- 数据库已经有：
  - `approved_fact_find_data`
  - `crm_field_mapping`
  - `crm_update_tracking`
  - `audit_event`

### 2.2 当前 Approve 的实际逻辑

前端调用：

```http
PUT /api/v1/submissions/{submission_id}/status
Content-Type: application/json

{"status":"approved"}
```

后端只做：

```text
PATCH fact_find_submission
SET submission_status = 'approved'
```

当前缺少：approved snapshot、Mercury mapping、同步任务、HTTP client、重试、回读验证和 UI sync status。

### 2.3 当前 OCR 数据的限制

OCR pipeline 主要写 `extracted_field`，尚未完整写入 applicant、employment、asset、liability 等规范化业务表。因此第一版不要假设业务表已经完整。

建议第一版 approved snapshot builder 直接从 `extracted_field + field_review` 聚合；第二阶段再补完整 normalised business tables。

### 2.4 哪些文档数据应该回传

第一版 CRM 回传的数据源是 **审核后的 Fact Find**。

- Fact Find：客户声明数据，允许回传。
- Payslip/Bank Statement/ID/ATO Notice：主要用于验证，不应默认覆盖 CRM 声明字段。
- 如果支持文件与 Fact Find 冲突，先提示人工复核；只有人工选择的最终值才进入 approved snapshot。

---

## 3. 推荐总体架构

```text
┌────────────────────┐
│ Review Page        │
│ Approve            │
└─────────┬──────────┘
          │ PUT status=approved
          ▼
┌──────────────────────────────┐
│ Approval Service / DB RPC    │
│ 1. validate                 │
│ 2. freeze approved snapshot │
│ 3. queue crm sync           │
└─────────┬────────────────────┘
          │ durable pending row
          ▼
┌──────────────────────────────┐
│ CRM Worker                  │
│ claim → build plan → sync   │
└─────────┬────────────────────┘
          ▼
┌──────────────────────────────┐
│ Mercury Client              │
│ Contact / Opportunity / ... │
└─────────┬────────────────────┘
          ▼
┌──────────────────────────────┐
│ Read-back Verification      │
│ tracking + audit + UI       │
└──────────────────────────────┘
```

### 3.1 为什么要后台任务

一次申请可能需要十几次 Mercury API 调用。把所有请求放在 Approve HTTP 请求里会导致：

- 用户等待时间过长。
- 网络失败导致 Approve 看似失败，但部分 CRM 对象已经创建。
- 浏览器刷新后无法恢复。
- 不能可靠重试。

所以 Approve 只负责“批准并排队”；worker 负责真正同步。

### 3.2 审批状态与同步状态必须分开

建议 UI 组合显示：

```text
Approved / CRM Pending
Approved / CRM In Progress
Approved / CRM Completed
Approved / CRM Failed
```

Mercury 失败不能撤销人工审批。

---

## 4. 建议文件结构

新增：

```text
backend/app/integrations/
  __init__.py
  mercury/
    __init__.py
    client.py               # HTTP、认证、timeout、错误映射
    errors.py               # MercuryError 类型
    payloads.py             # Contact/Opportunity/... builder
    normalizers.py          # date/name/phone/money/enum
    mappings.py             # field_key 到 Mercury 字段映射
    sync_plan.py            # approved snapshot → operations
    sync_service.py         # 执行顺序、保存 IDs、回读验证
    extension_merge.py      # livingExpense/otherIncome GET-merge-PUT

backend/app/services/
  approval.py               # 审批校验、snapshot、queue
  crm_repository.py         # Supabase tracking/audit 数据访问

backend/app/workers/
  __init__.py
  mercury_sync.py           # pending job worker

backend/app/routes/
  crm.py                    # 查询状态、手动重试（不接收密钥）

backend/app/integrations/mercury/mappings/
  v1.json                   # 版本化出站 mapping

backend/tests/
  test_mercury_client.py
  test_mercury_payloads.py
  test_mercury_sync_service.py
  test_approval.py
  test_crm_routes.py
  integration/test_mercury_test_account.py

supabase/migrations/
  <timestamp>_add_mercury_sync_workflow.sql
```

修改：

```text
backend/app/config.py
backend/.env.example
backend/app/__init__.py
backend/app/services/review.py
backend/app/routes/review.py
frontend/src/lib/api.js
frontend/src/app/(dashboard)/application/[id]/page.js
docker-compose.prod.yml（main 合并部署分支后）
docs/API_CONTRACT.md
```

不要把 Mercury 逻辑塞进 `review.py` 一个大函数。路由只做认证、输入校验和调用 service。

---

## 5. 配置与安全开关

### 5.1 环境变量

在 `backend/app/config.py` 和 `backend/.env.example` 增加：

```dotenv
MERCURY_ENABLED=false
MERCURY_ALLOW_WRITES=false
MERCURY_DRY_RUN=true
MERCURY_BASE_URL=https://apis.connective.com.au/mercury/v1
MERCURY_API_TOKEN=
MERCURY_API_KEY=
MERCURY_TIMEOUT_SECONDS=20
MERCURY_MAX_ATTEMPTS=5
MERCURY_TEST_RECORD_PREFIX=SMARTFINN-TEST-
MERCURY_WORKER_POLL_SECONDS=5
```

含义：

- `MERCURY_ENABLED`：是否加载 Mercury 功能。
- `MERCURY_ALLOW_WRITES`：是否允许 POST/PUT；默认 false。
- `MERCURY_DRY_RUN`：只生成 payload，不发送。
- `MERCURY_TEST_RECORD_PREFIX`：测试阶段只允许操作带此前缀的 Opportunity。

### 5.2 写保护

测试阶段发送 POST/PUT 前必须同时满足：

```python
MERCURY_ENABLED is True
MERCURY_ALLOW_WRITES is True
MERCURY_DRY_RUN is False
```

更新已有 Opportunity 时，还必须确认：

```text
opportunityName 以 MERCURY_TEST_RECORD_PREFIX 开头
```

如果不满足，client 抛出 `mercury_write_blocked`，不能发送请求。

### 5.3 日志规则

禁止记录：

- API Key
- API Token
- 完整 URL（Token 在 path 中）
- 客户完整 DOB、地址、证件号、银行账号
- 未脱敏的完整 payload/response

允许记录：

```text
operation_id
entity_type
local_id
mercury_unique_id
HTTP status
duration_ms
attempt_number
sanitised error code
request payload hash
```

---

## 6. 数据库迁移设计

不要编辑已执行的旧 migration；新增 migration。

### 6.1 扩展 crm_update_tracking

建议增加：

```sql
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
```

建议状态：

```text
not_started
pending
in_progress
completed
failed_retryable
failed_permanent
cancelled
not_required
```

### 6.2 新增 crm_update_item

一次同步会处理多个 Mercury 对象，只有总表不够排错。

```sql
create table public.crm_update_item (
  id uuid primary key default gen_random_uuid(),
  crm_update_tracking_id uuid not null
    references public.crm_update_tracking(id) on delete cascade,
  sequence_number integer not null,
  entity_type text not null,
  operation text not null,
  local_reference text,
  mercury_unique_id text,
  status text not null default 'pending',
  attempt_count integer not null default 0,
  request_hash text,
  response_status integer,
  error_code text,
  error_message text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz default now()
);

create index crm_update_item_tracking_idx
  on public.crm_update_item(crm_update_tracking_id, sequence_number);
```

不要保存明文敏感 payload；需要调试时保存脱敏摘要或存入受限 storage。

### 6.3 approved snapshot 必须不可变

`approved_fact_find_data` 创建后不能 UPDATE。需要修改时创建新版本。

建议增加：

```sql
alter table public.approved_fact_find_data
  add column if not exists version integer,
  add column if not exists source_hash text,
  add column if not exists schema_version text default '1';
```

同一 submission 的 version 必须递增。

### 6.4 原子审批 RPC

理想实现是 Supabase/Postgres RPC：

```text
approve_submission_and_queue_crm_sync(
  submission_id,
  approved_data_json,
  approved_by,
  source_hash,
  mapping_version
)
```

同一个事务内：

1. 锁定 submission。
2. 拒绝重复审批或生成新 approval version。
3. 插入 approved snapshot。
4. 更新 submission_status=approved。
5. 插入 crm_update_tracking(status=pending)。
6. 插入 audit_event。
7. 返回 approval_id、tracking_id。

不要用四个互不相关的 HTTP 请求完成以上动作，否则中途失败会产生半完成状态。

---

## 7. Approved Data Snapshot 契约

### 7.1 推荐 JSON 结构

```json
{
  "schema_version": "1",
  "submission_id": "local-submission-uuid",
  "approved_at": "2026-08-02T10:00:00Z",
  "approved_by": "staff-user-uuid",
  "opportunity": {
    "local_application_id": "local-application-uuid",
    "mercury_opportunity_id": null,
    "opportunity_name": "SMARTFINN-TEST-John-Citizen",
    "amount": 650000,
    "transaction_type": "Loan",
    "transaction_subtype": "Purchase",
    "status": "Lead",
    "loan_term_years": 30,
    "lmi": 0,
    "objectives": "Purchase owner occupied property"
  },
  "applicants": [
    {
      "applicant_number": 1,
      "mercury_person_id": null,
      "title": "Mr",
      "first_name": "John",
      "middle_name": null,
      "last_name": "Citizen",
      "date_of_birth": "1990-04-22",
      "mobile": "0400111222",
      "email": "john@example.test",
      "marital_status": "Single",
      "addresses": [],
      "employments": [],
      "incomes": []
    }
  ],
  "assets": [],
  "liabilities": [],
  "living_expenses": [],
  "other_income": [],
  "provenance": {
    "fact_find_document_id": "document-uuid",
    "field_count": 264,
    "corrected_field_count": 3,
    "mapping_version": "mercury-v1"
  }
}
```

### 7.2 值选择规则

每个 field_key 按以下规则选值：

1. 有 approved/corrected review 时，使用 `corrected_value`。
2. confirmed 时，使用 `normalised_value`。
3. case-level Approve 明确允许高置信度字段时，可使用 `normalised_value`，同时在 provenance 标记 `accepted_by_case_approval`。
4. rejected 字段不能进入 snapshot。
5. raw value 只用于展示和审计，不能直接回传。

### 7.3 审批前校验

至少检查：

- OCR job 全部结束，不能还在 processing。
- Fact Find 存在且不是空表。
- Applicant 1 有可解析的姓名。
- 新建 Opportunity 有 name 和 amount。
- email/phone/date/money 格式合法。
- 没有 rejected 必填字段。
- 没有 unresolved discrepancy。
- 对测试账号写入时 Opportunity 名称有测试前缀。

校验失败返回结构化错误：

```json
{
  "error": {
    "code": "approval_validation_failed",
    "message": "Application cannot be approved for CRM sync.",
    "details": [
      {"field_key":"applicant_1_full_name","reason":"required"}
    ]
  }
}
```

---

## 8. Mercury Client 实现规范

### 8.1 基本请求

```python
class MercuryClient:
    def __init__(self, base_url, token, api_key, timeout_seconds):
        ...

    def request(self, method, path, *, json=None):
        url = f"{base_url}/{token}/{path.lstrip('/')}"
        headers = {
            "x-api-key": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        ...
```

生产日志不能输出拼好 Token 的 URL。

### 8.2 对外方法

```python
search_opportunities(...)
get_opportunity(opportunity_id)
create_opportunity(payload)
update_opportunity(opportunity_id, payload)

search_contacts(...)
get_contact(person_id)
create_contact(payload)
update_contact(person_id, payload)

create_related_party(opportunity_id, payload)
update_related_party(opportunity_id, related_party_id, payload)

create_address(person_id, payload)
update_address(person_id, address_id, payload)

create_employment(person_id, payload)
update_employment(person_id, employment_id, payload)

create_income(person_id, payload)
update_income(person_id, income_id, payload)

create_asset(opportunity_id, payload)
update_asset(opportunity_id, asset_id, payload)

create_liability(opportunity_id, payload)
update_liability(opportunity_id, liability_id, payload)

get_extension(opportunity_id, key)
create_extension(opportunity_id, key, payload)
update_extension(opportunity_id, key, payload)
```

### 8.3 成功响应

POST 通常返回：

```json
{"status":200,"uniqueId":"resource-uuid"}
```

Opportunity 官方示例可能返回：

```json
{"uniqueId":"resource-uuid","emailId":""}
```

client 应统一解析 `uniqueId`，缺失时抛 `mercury_invalid_response`。

### 8.4 错误分类

| HTTP | 分类 | 默认处理 |
| ---: | --- | --- |
| 400 | permanent | payload 错误，不自动重试 |
| 401/403 | permanent/config | 凭据或权限问题，停止任务 |
| 404 | permanent | ID 错误；先检查是否可重新查询 |
| 409 | conditional | 防重/冲突；GET 检查资源是否已创建 |
| 429 | retryable | 指数退避，尊重 Retry-After |
| 500/502/503/504 | retryable | 指数退避 |
| timeout/network | retryable | 在防重条件下重试 |

退避建议：

```text
5s, 15s, 45s, 2m, 5m
```

不要在一次 HTTP 请求内部无限重试。

---

## 9. Payload Builder 具体规则

所有 builder 都必须是纯函数：输入 approved data，输出 JSON；不能自己调用网络。

### 9.1 Person/Contact

官方起始示例：

```json
{
  "isDeleted": false,
  "firstName": "Joe",
  "lastName": "Connective",
  "middleName": "James",
  "title": "Mr",
  "dateOfBirth": "2000-04-22T00:00:00.000Z",
  "addresses": [],
  "contactMethods": [
    {"contactMethod":"Mobile","content":"0400111222"},
    {"contactMethod":"Email 1","content":"joe@example.test"}
  ]
}
```

注意：

- 不要把 `full_name` 原样塞进 `firstName`。
- 单词姓名或无法可靠拆分的姓名必须要求人工确认。
- DOB 转成官方示例 ISO UTC 格式。
- 联系方式优先使用 `contactMethods`。
- Swagger 的 title enum：Dr/Miss/Ms/Mr/Mrs/Prof/Rev。
- 更新 Contact 第一版使用“仅变化字段”的 PUT，并通过测试账号验证；如果某个字段不接受部分更新，记录实体级例外，不要全局改成 GET 对象原样回写。

### 9.2 Opportunity

官方最小示例：

```json
{"opportunityName":"SMARTFINN-TEST-John","amount":"350000"}
```

建议第一版创建：

```json
{
  "isDeleted": false,
  "transactionType": "Loan",
  "opportunityName": "SMARTFINN-TEST-John",
  "amount": 350000,
  "status": "Lead",
  "tranxType": "Purchase",
  "notePadText": "Created by SmartFINN from approved Fact Find"
}
```

Opportunity PUT 明确支持部分更新：

```json
{"amount":600000,"lmi":12000,"loanTerm":30}
```

### 9.3 Related Party

先创建/找到 Contact，再关联：

```json
{
  "personID": "mercury-person-uuid",
  "relationship": "Primary applicant"
}
```

Applicant 2：

```json
{
  "personID": "second-person-uuid",
  "relationship": "Secondary applicant"
}
```

字符串大小写以测试账号实际接受值为准；mapping 文件统一维护，不要散落硬编码。

### 9.4 Address

```json
{
  "streetName": "Collins",
  "streetNumber": "555",
  "streetType": "Street",
  "city": "MELBOURNE",
  "state": "VIC",
  "postcode": "3000",
  "country": "Australia",
  "type": "Home",
  "addressBlock": "555 Collins Street\nMELBOURNE VIC 3000"
}
```

保留 postcode 为 string，不能转 integer。

### 9.5 Employment/Income

Employment 关键字段：

```text
employerName
employmentBasis
employmentStatus
employmentType
jobTitle
startDate
endDate
personId
address
```

Income 示例结构：

```json
{
  "personID": "person-uuid",
  "amount": 120000,
  "type": "Salary",
  "frequency": "Annual"
}
```

不要把 annual salary 与 monthly amount 混淆。先统一内部 annual/monthly 语义，再转换到 Mercury frequency。

### 9.6 Asset/Liability

Asset 示例：

```json
{"name":"Motor Vehicle","type":"vehicle","value":25000}
```

Liability 示例：

```json
{
  "name":"Credit Card",
  "type":"account",
  "value":8500,
  "limit":15000,
  "institution":"CBA",
  "accountRepayment":350,
  "accountRepaymentFrequency":"monthly"
}
```

更新时带 Mercury `uniqueId`；新建时不要自行伪造普通 entity ID。

### 9.7 Living Expenses/Other Income（最容易写错）

外层对象：

```json
{
  "uniqueId": "extension-uuid",
  "parentId": "opportunity-uuid",
  "parentType": "loan",
  "key": "livingExpense",
  "value": "[]"
}
```

`value` 是 **JSON 字符串**，不是直接 array。

正确算法：

```text
GET extension
→ JSON.parse(response.value)
→ 按 line uniqueId 或稳定业务键合并
→ 保留所有未删除的现有行
→ JSON.stringify(完整数组)
→ PUT extension
```

PUT 会替换全部现有条目，禁止只发送新增行。

行示例：

```json
{
  "uniqueId": "line-uuid",
  "amount": "1000.00",
  "type": "Clothing & Personal Care",
  "frequency": "Monthly",
  "splits": [
    {"personId":"person-1","percent":60},
    {"personId":"person-2","percent":40}
  ]
}
```

Other Income 使用同一结构，只把 key 改为 `otherIncome`。

---

## 10. 同步计划与执行顺序

### 10.1 新申请（没有 Mercury IDs）

```text
1. Create Applicant 1 Contact
2. Save Applicant 1 person uniqueId
3. Create Applicant 2 Contact（如有）
4. Save Applicant 2 person uniqueId
5. Create Opportunity
6. Save Opportunity uniqueId 到 crm_application.crm_application_id
7. Create Primary related party
8. Create Secondary related party（如有）
9. Create/verify addresses
10. Create employments
11. Create incomes
12. Create assets
13. Create liabilities
14. GET/create/PUT livingExpense extension
15. GET/create/PUT otherIncome extension
16. GET Opportunity + Contacts 回读验证
17. Mark completed
```

### 10.2 已有 Mercury Opportunity

```text
1. GET Opportunity
2. GET related parties
3. Resolve Applicant person IDs
4. GET Contacts and child collections
5. Diff current CRM vs approved snapshot
6. Generate only necessary creates/updates
7. Execute with uniqueId upsert
8. GET-merge-PUT extensions
9. Read back
10. Mark completed
```

### 10.3 防重复策略

- 一次 approval version 只能有一个 active sync job。
- 创建前先检查 tracking 中是否已有返回 ID。
- 网络 timeout 后，不要盲目重复 POST；先通过已知 ID、external reference 或搜索确认是否创建成功。
- Opportunity name 使用稳定测试前缀和 local application ID，例如：

```text
SMARTFINN-TEST-{local_application_id}
```

- request hash 相同且 item 已 completed 时跳过。

---

## 11. Worker 设计

### 11.1 MVP 方案

使用独立 Python worker 进程轮询 `crm_update_tracking`：

```bash
python -m app.workers.mercury_sync
```

生产 Compose 增加 `crm-worker` service，使用同一 backend image，但 command 不同。

### 11.2 Job claim

一个 worker 时可先用乐观更新：

```text
SELECT pending job
PATCH status=in_progress WHERE id=? AND status=pending
只有更新成功的 worker 才执行
```

如果未来多 worker，改成 Postgres RPC + `FOR UPDATE SKIP LOCKED`。

### 11.3 Worker 崩溃恢复

启动时把超过阈值仍为 `in_progress` 的 job 重置为 `failed_retryable`，例如 10 分钟无更新。

### 11.4 停机

worker 收到 SIGTERM 时：

- 不再 claim 新 job。
- 当前 HTTP 请求完成后保存状态。
- 在容器 stop grace period 内退出。

---

## 12. SmartFINN 内部 API 契约

### 12.1 Approve

保留：

```http
PUT /api/v1/submissions/{id}/status
```

成功响应扩展为：

```json
{
  "message": "Application approved and CRM sync queued.",
  "submission_status": "approved",
  "crm_sync": {
    "tracking_id": "uuid",
    "status": "pending"
  }
}
```

### 12.2 查询同步状态

```http
GET /api/v1/submissions/{id}/crm-sync
```

```json
{
  "status": "in_progress",
  "attempt_count": 1,
  "started_at": "2026-08-02T10:01:00Z",
  "completed_at": null,
  "last_error": null,
  "items": [
    {"entity_type":"contact","status":"completed"},
    {"entity_type":"opportunity","status":"in_progress"}
  ]
}
```

### 12.3 手动重试

```http
POST /api/v1/submissions/{id}/crm-sync/retry
```

只允许：

- admin/reviewer。
- 当前状态是 failed_retryable 或明确允许重试的 failed_permanent。
- 不重新执行 completed item。

### 12.4 Dry-run preview

开发阶段建议增加：

```http
GET /api/v1/submissions/{id}/crm-sync/preview
```

返回脱敏后的 sync plan，不发送 Mercury 请求。生产可限制为 admin。

---

## 13. 前端改动

### 13.1 Approve 前

- 显示确认弹窗。
- 告知用户 Approve 后会开始 CRM 同步。
- 如果有未解决字段，禁止批准并显示字段列表。

### 13.2 Approve 后

不要立即跳回列表并丢失状态。至少显示：

```text
Application approved
CRM sync queued
```

随后可以跳转列表，但列表和详情都要展示 sync badge。

### 13.3 状态轮询

对 pending/in_progress 每 3–5 秒轮询；completed/failed 停止。

### 13.4 失败 UI

显示可理解信息：

```text
CRM sync failed: Mercury rejected the Opportunity payload.
No local approval data was lost.
```

不要向前端返回 Mercury 原始 PII response 或 credentials。

---

## 14. 测试计划

### 14.1 Unit tests

必须覆盖：

- 姓名、日期、电话、金额 normalizer。
- 每个 payload builder。
- enum mapping。
- 空值 omit。
- Applicant 1/2 linking。
- Living Expense string encode/decode。
- extension merge 保留已有行。
- update 带 uniqueId、create 不带 uniqueId。
- error retry classification。
- secret redaction。

### 14.2 Client tests

使用 mock HTTP，不访问真实 API：

- header 正确。
- URL 正确但日志不暴露 Token。
- timeout 转 MercuryError。
- 400 不重试。
- 429/5xx 标记 retryable。
- create response 解析 uniqueId。
- invalid JSON/缺 uniqueId 报错。

### 14.3 Service tests

用 fake Mercury client：

- 新建单申请人完整顺序。
- 双申请人顺序。
- 中途失败保存 item 状态。
- retry 跳过 completed item。
- Opportunity ID 回写。
- read-back mismatch 不能标 completed。

### 14.4 Route tests

- 必须登录。
- 非 UUID 拒绝。
- 未完成 OCR 不能 Approve。
- Approve 创建 snapshot + pending tracking。
- retry 权限。
- status response 不泄露敏感字段。

### 14.5 测试账号 Integration tests

默认跳过，只有显式设置环境变量才运行：

```bash
RUN_MERCURY_INTEGRATION_TESTS=1 python -m pytest -q tests/integration/test_mercury_test_account.py
```

执行顺序：

1. GET/search 验证 credentials。
2. POST 创建 `SMARTFINN-TEST-{timestamp}` Contact。
3. GET 验证姓名。
4. PUT 修改一个安全字段。
5. GET 验证部分更新。
6. POST 创建最小 Opportunity。
7. 保存 uniqueId。
8. 创建 Primary related party。
9. 创建一个测试 Asset/Liability。
10. 测试 Living Expense GET-merge-PUT。
11. 最后软删除本次测试创建的资源（客户允许时）。

测试失败时保留 ID 到受限测试输出，便于人工清理。

### 14.6 回归命令

```bash
cd backend
python -m compileall .
python -m pytest -q

cd ../frontend
npm run lint
npm test
npm run build
```

---

## 15. 分阶段开发计划

每个阶段都应独立可测试，不要一次提交全部功能。

### Phase 1：规范与安全底座

交付：

- 保存客户确认使用的 Swagger 到受控 docs/vendor 路径（不含密钥）。
- 配置环境变量。
- MercuryError。
- MercuryClient GET 和 dry-run。
- secret redaction tests。

验收：GET 测试账号成功；写开关默认关闭。

### Phase 2：Payload builders

交付：

- approved snapshot schema。
- normalizers。
- Contact、Opportunity、Related Party builders。
- Address、Employment、Income、Asset、Liability builders。
- extension merge。

验收：纯单元测试通过；不访问网络。

### Phase 3：数据库与 approval

交付：

- 新 migration。
- approval validation。
- snapshot builder。
- atomic RPC。
- pending tracking。

验收：Approve 后数据库产生 approved snapshot 和 pending job，但 dry-run 下不写 Mercury。

### Phase 4：Sync service 与 worker

交付：

- sync plan。
- 新建/更新顺序。
- item tracking。
- retry/idempotency。
- worker。

验收：fake client E2E 完整通过。

### Phase 5：前端状态

交付：

- confirmation。
- status badge。
- polling。
- retry UI。
- readable errors。

验收：mock pending→completed/failed 状态正确。

### Phase 6：测试账号真实验证

交付：

- Contact POST/GET/PUT/GET。
- Opportunity POST/GET/PUT/GET。
- related party 和子对象。
- extension merge。
- 截图/响应脱敏证据。

验收：Mercury UI 与 GET response 都确认数据正确。

### Phase 7：Approve 自动回传验收

交付：

- 一份完整测试 Fact Find。
- 人工纠正字段。
- Approve。
- 自动 CRM sync。
- 状态 completed。
- read-back 一致。

---

## 16. 推荐的第一批 Commit/PR

### PR 1：Mercury client foundation

```text
feat(crm): add guarded Mercury API client and configuration
```

只做 config/client/errors/tests，不接 Approve。

### PR 2：Approved snapshot and payload mapping

```text
feat(crm): build approved Fact Find snapshot and Mercury payloads
```

只做纯数据转换和单测。

### PR 3：CRM sync persistence and worker

```text
feat(crm): queue and execute durable Mercury sync jobs
```

包含 migration、tracking、worker、fake-client E2E。

### PR 4：Approval and frontend integration

```text
feat(crm): trigger Mercury sync after approval and show status
```

最后才把 Approve 接上写回。

这样出问题时容易回滚，也方便多人 review。

---

## 17. 常见错误与禁止事项

### 禁止事项

- 不要把 API Key/Token 写进代码、测试 fixture、截图或文档。
- 不要用浏览器直接调用 Mercury API。
- 不要从前端读取 Mercury secret。
- 不要把 OCR raw value 直接回传。
- 不要默认支持文件覆盖 Fact Find。
- 不要把审批和 CRM 成功视为同一个状态。
- 不要在 timeout 后盲目重复 POST。
- 不要对非测试前缀 Opportunity 执行写操作。
- 不要对 livingExpense/otherIncome 只 PUT 新行。
- 不要修改已执行 migration；必须新增 migration。
- 不要把整个 Mercury 实现塞在一个 service 文件。

### 常见误区

**误区：Swagger model 没 required，所以所有字段都可空。**  
错误。只能说明 Swagger 未完整声明 required；以官方最小示例和测试账号为准。

**误区：PUT 一定是完整替换。**  
Opportunity 官方文档明确允许部分更新；extension 则明确整组替换。必须按实体处理。

**误区：有 CRM 登录账号就能调用 API。**  
还需要 API Token、API Key 和写权限。

**误区：Approve 成功就表示 CRM 成功。**  
Approve 只负责本地批准并排队；CRM 有独立状态。

---

## 18. 开发接手执行清单

接手人员开始工作时按以下顺序：

1. 运行 `git status --short --branch`，保留所有用户未提交文件。
2. 确认当前 branch 与 `origin/main` 差异，不擅自 reset/checkout。
3. 阅读本文件第 0、1、2、3、15 节。
4. 阅读当前代码和测试，不根据文档猜函数签名。
5. 检查最新 migration 是否已经包含本文件建议的字段。
6. 先实现 Phase 1，不直接修改 Approve。
7. 所有网络写入默认 dry-run。
8. 没有环境变量时，单元测试必须仍可运行。
9. 测试账号写入前打印脱敏 preview，确认测试前缀。
10. 每完成一个 phase，更新本文件“实施状态”。

### 实施状态（后续维护人员更新）

| Phase | 状态 | PR/Commit | 验证 |
| --- | --- | --- | --- |
| 1. Client foundation | Not started |  |  |
| 2. Payload builders | Not started |  |  |
| 3. Approval persistence | Not started |  |  |
| 4. Worker/sync service | Not started |  |  |
| 5. Frontend status | Not started |  |  |
| 6. Test-account validation | Not started |  |  |
| 7. End-to-end approval | Not started |  |  |

---

## 19. 最终交接结论

现在已经具备开始开发的条件：客户确认 Swagger 版本可用、CRM 是测试账号，官方 Wiki 也提供了 Opportunity/Person payload、部分 PUT、嵌套 upsert 和 financial extension 的完整行为说明。

实现时最重要的原则是：

```text
先冻结人工批准的数据
→ 再生成版本化 Mercury payload
→ 用持久化后台任务同步
→ 保存所有 uniqueId
→ 写后回读验证
```

不要从“Approve 按钮里直接发几个 requests”开始。先完成 client、payload builder、数据库 job 和测试，再接入 Approve，才能避免重复数据、部分写入和不可恢复的 CRM 状态。
