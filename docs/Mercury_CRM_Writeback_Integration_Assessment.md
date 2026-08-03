# Mercury CRM 回传集成调研与实施差距分析

> 项目：SmartFINN AI Mortgage Application Automation  
> 调研日期：2026-08-02  
> 目标：工作人员批准（Approve）申请后，将 OCR 提取并经人工审核的数据通过 Connective Mercury Nexus API 写入 Mercury CRM，减少人工录入。

## 1. 结论摘要

项目目录中已经存在 Mercury CRM 的接口概览、字段映射、数据模型和会议需求，但当前资料与代码尚不足以可靠完成生产级 CRM 回传。

核心结论如下：

1. 项目使用的是 **Connective Mercury Nexus CRM**，不是 `docs.mercury.com` 所描述的美国银行 Mercury API。
2. `UNSW/new/mercury-factfind-field-mapping.html` 是目前最完整的 Mercury 资料，包含 API 基础信息、约 85 个 Fact Find 逻辑字段、Mercury 对象和字段映射、转换建议及已知 API 缺口。
3. 现有字段表主要描述 **Mercury → SmartFINN** 的 GET 读取和比对流程，不是完整的 **SmartFINN → Mercury** POST/PUT 回写契约。
4. OCR 原始 JSON 不应直接发送给 Mercury。数据必须先经过规范化、人工审核、批准快照和出站字段映射，再按 Mercury 的不同业务对象生成多个请求。
5. 当前 Approve 功能只更新本地 submission 状态，没有生成 approved data，也没有调用 Mercury API。
6. 开发 CRM connector 前，仍需客户或 AIMESHLABS 提供官方 Swagger/OpenAPI、出站 payload 规范、可安全写入的测试环境以及黄金测试案例。

## 2. 调研范围与资料来源

### 2.1 Mercury 与客户蓝图资料

- `/Users/liujiaqi/Documents/2026T2/COMP9900/UNSW/new/mercury-factfind-field-mapping.html`
- `/Users/liujiaqi/Documents/2026T2/COMP9900/UNSW/Mapping/new/mercury-factfind-field-mapping.html`
- `/Users/liujiaqi/Documents/2026T2/COMP9900/UNSW/2. Data Modeling/Smartfinn Fact Find Field Mapping Matrix.docx`
- `/Users/liujiaqi/Documents/2026T2/COMP9900/UNSW/2. Data Modeling/Data Model Specification.docx`
- `/Users/liujiaqi/Documents/2026T2/COMP9900/UNSW/2. Data Modeling/Tables.docx`
- `/Users/liujiaqi/Documents/2026T2/COMP9900/UNSW/2. Data Modeling/ER Diagram code.docx`
- `/Users/liujiaqi/Documents/2026T2/COMP9900/UNSW/new/imgs/` 下的 Mercury CRM 页面截图

两份 `mercury-factfind-field-mapping.html` 的 SHA-1 相同，是内容一致的副本。

### 2.2 会议记录

- `/Users/liujiaqi/Documents/2026T2/COMP9900/project  requirement/0727SmartFINN 项目会议纪要.docx`
- `/Users/liujiaqi/Documents/2026T2/COMP9900/project  requirement/20260715 SmartFINN 项目会议纪要.docx`
- `/Users/liujiaqi/Documents/2026T2/COMP9900/project  requirement/20260713会议纪要_Mortgage_AI_Verification_Project.docx`

其中 2026-07-27 是当前目录中最新的会议记录，也是本次 CRM 回传目标最直接的需求依据。

### 2.3 当前代码与仓库文档

- `backend/app/services/review.py`
- `backend/app/routes/review.py`
- `backend/app/services/ocr_pipeline.py`
- `backend/app/normalization/fact_find.py`
- `backend/app/normalization/fact_find_mapping.json`
- `backend/app/config.py`
- `frontend/src/app/(dashboard)/application/[id]/page.js`
- `frontend/src/lib/api.js`
- `supabase/migrations/create_smartfinn_schema.sql`
- `docs/API_CONTRACT.md`
- `docs/backend-handoff.md`
- `docs/FactFind_Frontend_Handoff.md`

## 3. 已确认的业务目标

### 3.1 客户需求

2026-07-27 会议明确要求：

- 在 VPS 部署完成后，尝试将已提取的 Fact Find 数据写入 Mercury CRM。
- 客户提供 Mercury API Key 和 CRM 访问权限。
- 优先实现已提取字段向 CRM 写入。
- Mercury CRM 集成是项目的重要价值提升功能。
- 目标流程应包含 OCR 提取、人工审核和 CRM 上传测试。

2026-07-15 会议进一步明确手工渠道的标识流程：

1. SmartFINN 先创建 Local Application ID。
2. 上传文件并进行 OCR、提取、审核。
3. 将 Application 发送给 Mercury CRM。
4. Mercury 创建 CRM Application ID。
5. 将 CRM Application ID 回写到 SmartFINN，并与 Local Application ID 同时保留。

### 3.2 目标业务流程

```text
文件上传
  → OCR / AcroForm 提取
  → 字段标准化
  → 人工审核与纠正
  → Approve application
  → 冻结 approved data snapshot
  → 生成 Mercury 同步计划与 payload
  → 调用 Mercury POST/PUT API
  → 保存 Mercury external IDs
  → GET 回读核对
  → 更新 CRM sync status 与审计日志
```

## 4. 项目中已有的 Mercury API 信息

### 4.1 API 基础信息

现有 Mercury HTML 文档记录了以下信息：

| 项目 | 当前资料中的定义 |
| --- | --- |
| 产品 | Connective Mercury Nexus CRM |
| API | Connective Public API v1 |
| Production base URL | `https://apis.connective.com.au/mercury/v1/{token}` |
| API Token | URL path segment |
| API Key | 请求头 `x-api-key: {apiKey}` |
| Content-Type | POST/PUT 使用 `application/json` |
| HTTP verbs | GET、POST、PUT |
| 删除 | 文档描述为 PUT `isDeleted: true` 的软删除 |
| 日期 | 很多响应使用 Unix timestamp milliseconds |
| 限流 | 60 requests/second、40,000 requests/day |

API Key 和 Token 必须仅保存在后端 Secret/环境变量中，不能提交到 Git、返回给浏览器或写入日志。

### 4.2 已记录的对象和读取 endpoint

| Mercury 对象 | 当前文档中的 endpoint |
| --- | --- |
| Opportunity | `GET /opportunities/{id}` |
| Related parties | `GET /opportunities/{id}/relatedParties` |
| Contact | `GET /contacts/{personId}` |
| Addresses | `GET /contacts/{personId}/addresses` |
| Employments | `GET /contacts/{personId}/employments` |
| Incomes | `GET /contacts/{personId}/incomes` |
| Assets | `GET /opportunities/{id}/assets` |
| Liabilities | `GET /opportunities/{id}/liabilities` |
| Living expenses | `GET /opportunities/{id}/extension/livingExpense` |
| Other income | `GET /opportunities/{id}/extension/otherIncome` |

现有推荐 GET 顺序是先获取 Opportunity 和 Related Parties，解析 Applicant 1/2 的 `personID`，再分别读取 Contact、Address、Employment 和 Income，最后读取 Opportunity 级别的资产、负债和支出数据。

### 4.3 字段映射覆盖情况

Mercury HTML 中记录了约 85 个逻辑字段：

| 状态 | 数量 | 含义 |
| --- | ---: | --- |
| Confirmed | 64 | 文档中有 API 路径，可用于同步/比较基础 |
| Verify in Swagger | 6 | 必须由官方 Swagger 或真实 API 响应确认 |
| Inferred | 6 | 逻辑映射存在，但需要更完整测试案例 |
| API gap | 4 | 不能通过当前 Mercury API 自动处理 |

文档给出的汇总是：Confirmed 约 75%，Swagger 验证后约 82%，所有映射尝试约 95%。这些百分比衡量的是 **Mercury 结构化数据读取覆盖率**，不能直接等同于出站写入覆盖率。

### 4.4 已知限制

- Mercury public API 当前没有已记录的附件列表/下载 endpoint。
- SmartFINN 应直接接收用户上传的 PDF/图片并运行 OCR，不能依赖 Mercury 文件存储。
- Dependants count 可从 Contact 获取，但 dependant name/age 没有对应 API。
- Consent、声明、签名等内容不能从 Mercury API 自动获得，应保留在 SmartFINN/DigiSign 流程。
- 重复资产、负债和 employment 不能按 Fact Find PDF 固定行号处理，应按 Mercury 数组和 `uniqueId` 管理。
- 不是所有 Mercury UI 字段都有 public API endpoint。

## 5. 是否需要在回传前处理数据

答案是 **必须处理**。

### 5.1 文档要求的数据层次

Data Model Specification 规定四层数据：

1. Source layer：CRM 原始数据、上传文件、原始元数据。
2. Extraction layer：OCR 原始输出、字段、表格、置信度和位置。
3. Normalisation layer：申请人、地址、工作、资产、负债和支出等结构化业务数据。
4. Review/Approval layer：人工审核后、可用于 CRM 更新的数据。

OCR extracted data 不等于 approved data。只有人工审核后的结果才能进入 `approved_fact_find_data` 并用于 CRM 更新。

### 5.2 数据来源优先级

现有 Field Mapping Matrix 建议下游使用以下优先级：

1. Analyst-approved value
2. CRM value
3. OCR-extracted normalised value
4. Raw OCR value

当 CRM 和 OCR 值冲突时，应保留双方值并触发 discrepancy review，不应自动覆盖 CRM。

### 5.3 必需的标准化处理

2026-07-15 会议明确将 Data Cleaning 和 Data Standardisation 纳入范围，包括：

- 姓名和公司名称标准化。
- 地址清洗和分段。
- 澳洲电话号码标准化。
- 日期格式统一。
- 金额、货币和小数处理。
- Email 格式校验。
- 特殊字符、连字符和多余空格处理。
- 空值、未知值和字段缺失处理。
- 重复记录处理。
- CRM enum 映射。

### 5.4 Mercury payload 转换示例

| SmartFINN 数据 | Mercury 回传前处理 |
| --- | --- |
| `full_name` | 根据已审核姓名拆分为 `firstName`、`middleName`、`lastName`；拆分规则需要客户确认 |
| `0412 345 678` | 规范化后再按 Mercury 接受格式发送 |
| `$12,500.00` | 转为 JSON number `12500.00` |
| `"true"` | 转为 JSON boolean `true` |
| 澳洲日期文本 | 按 Swagger 要求转为 Unix ms 或指定 date format |
| `full_time` | 映射成 Mercury 的正式 employment enum |
| Applicant 1/2 | 关联 Primary/Secondary `personId` |
| PDF 固定资产行 | 转成 Mercury asset 数组；更新时按 `uniqueId` upsert |
| 空 OCR 值 | 默认 omit，不能无意覆盖 CRM 已有值；具体规则需契约确认 |

不能把 GET response 字段简单反向作为 PUT payload。GET 字段可能是只读字段、计算字段，或只允许在 create 时写入。

## 6. 当前代码实现情况

### 6.1 已实现

- 上传 Fact Find、Payslip、Bank Statement、ID 和 ATO Notice 等文件。
- 运行 AcroForm direct-read 或 Azure Document Intelligence。
- 将 OCR 结果保存到 `extracted_field`。
- 保存 `raw_value`、`normalised_value`、`confidence`、`mapped_table` 和 `mapped_column`。
- 前端展示 OCR 字段并允许手工纠正。
- `field_review` 记录字段审核历史。
- 前端具有 Approve/Reject 按钮。
- 数据库已经预留 `approved_fact_find_data`、`crm_field_mapping` 和 `crm_update_tracking` 表。

### 6.2 Approve 当前真实行为

前端点击 Approve 后调用：

```http
PUT /api/v1/submissions/{submission_id}/status
Content-Type: application/json

{
  "status": "approved"
}
```

后端当前仅执行：

```text
PATCH fact_find_submission
SET submission_status = approved
```

然后返回 `Status updated successfully`。

### 6.3 尚未实现

- Approve 前置校验，例如 OCR 是否完成、必填字段是否确认、冲突是否解决。
- 将所有文档的审核字段聚合为一份 canonical Fact Find 数据。
- 写入不可变的 `approved_fact_find_data` 版本。
- 将 OCR 结果完整落入 applicant、employment、asset、liability 等 normalised business tables。
- `crm_field_mapping` seed data。
- Mercury backend client 和 credentials configuration。
- Mercury request payload builder。
- Opportunity/Contact/Related Party 等对象的 POST/PUT 调用。
- Mercury external ID 保存与 Local Application ID 关联。
- `crm_update_tracking` 的实际创建和状态更新。
- 后台同步任务、重试、幂等和限流处理。
- 写入后的 GET 回读验证。
- Mercury request/response 审计和脱敏日志。
- Mercury unit、contract、integration 和 end-to-end tests。

因此，当前系统中的 “Approved” 只表示本地状态发生变化，不表示 CRM 已同步。

## 7. 推荐的 Mercury 出站数据模型

批准后的 canonical snapshot 不应直接等于某个 Mercury request。应先生成同步计划，再拆分成对象请求。

```text
Applicant 1
  ├─ Contact
  ├─ Addresses[]
  ├─ Employments[]
  └─ Incomes[]

Applicant 2（如果存在）
  ├─ Contact
  ├─ Addresses[]
  ├─ Employments[]
  └─ Incomes[]

Application / Opportunity
  ├─ Opportunity
  ├─ Related Parties[]
  ├─ Assets[]
  ├─ Liabilities[]
  ├─ Living Expense extension
  └─ Other Income extension
```

建议区分两种同步模式：

### 7.1 新建模式

适用于 manual/email intake，没有 Mercury external ID。

初步顺序需要客户和 Swagger 最终确认：

1. 创建 Applicant Contact(s)。
2. 创建 Opportunity。
3. 创建 Primary/Secondary Related Parties。
4. 创建 Address、Employment 和 Income。
5. 创建 Assets、Liabilities、Living Expenses 和 Other Income。
6. 保存所有 Mercury 返回的 external IDs。

### 7.2 更新模式

适用于已有 Mercury Opportunity/Person ID 的申请。

1. GET 当前 Mercury snapshot。
2. 对比 approved snapshot 与当前 Mercury 值。
3. 只生成允许更新且真正发生变化的字段/对象。
4. 按 Mercury `uniqueId` upsert 重复记录。
5. PUT 后 GET 回读并验证。

## 8. 推荐的 Approve 与异步同步流程

Mercury 调用不应直接阻塞前端 Approve HTTP 请求。推荐采用审批事务 + 后台同步任务。

### 8.1 Approval transaction

Approve 时在一个本地事务中：

1. 确认所有必要 OCR jobs 已完成。
2. 确认必填字段已 reviewed/corrected/confirmed。
3. 确认没有未解决的 source conflict。
4. 聚合 final approved values。
5. 创建不可变的 `approved_fact_find_data` 版本。
6. 更新 `submission_status=approved`。
7. 创建 `crm_update_tracking(update_status=pending)`。
8. 创建 `audit_event(event_type=crm_update_required)`。

### 8.2 Background CRM sync

后台 worker：

1. 获取 approved snapshot 和对应 mapping version。
2. 验证 Mercury credentials/configuration。
3. 构建同步计划和 payload。
4. 执行 POST/PUT。
5. 记录每个 Mercury 对象的请求结果和 external ID。
6. GET 回读关键对象并核对。
7. 成功则标记 `completed`，失败则标记 `failed` 并保存可重试错误。

### 8.3 状态分离

审批状态和 CRM 同步状态必须分开：

```text
Approved / CRM Sync Pending
Approved / CRM Sync In Progress
Approved / CRM Sync Completed
Approved / CRM Sync Failed
```

CRM 暂时失败不应撤销人工审批；应保留 approved snapshot 并允许安全重试。

## 9. 仍需客户或 AIMESHLABS 提供的文档

### 9.1 官方 Swagger/OpenAPI

必须获得实际使用版本的 Swagger 2.0/OpenAPI，至少覆盖：

- Contacts
- Addresses
- Employments
- Incomes
- Opportunities
- Related Parties
- Assets
- Liabilities
- Living Expenses
- Other Income

需要确认每个 endpoint 的 method、path、request schema、response schema、必填字段、read-only 字段、enum、nullable、长度限制和错误响应。

### 9.2 Outbound Mapping Matrix

现有字段表需要增加真正的出站信息：

| 必需列 | 用途 |
| --- | --- |
| Approved data JSON path | 明确最终数据来源 |
| Mercury object | Contact、Opportunity、Asset 等 |
| Mercury field | 精确属性名和大小写 |
| Operation | POST create / PUT update |
| Endpoint | 精确请求 path |
| Data type | string、number、boolean、enum、array |
| Required on create | 新建时是否必填 |
| Updateable | 是否允许更新 |
| Null/omit rule | null、omit、empty 的行为 |
| Transform rule | 日期、电话、金额、enum 等转换 |
| Repeating record key | `uniqueId` 或其他匹配键 |
| Ownership rule | Applicant 1/2/both |
| Verification status | Confirmed/Swagger verified/API gap |
| Read-back endpoint | 写入后如何验证 |

### 9.3 Create/update 生命周期

需要客户确认：

- Contact 和 Opportunity 谁先创建。
- 如何创建 Primary/Secondary applicant 关联。
- 新建成功后各 external ID 位于哪个 response field。
- 更新 existing opportunity 时所需 ID。
- PUT 是局部更新还是完整对象替换。
- 是否支持并发控制、版本号或 modified timestamp。
- 部分子对象失败时的处理规则。

### 9.4 测试环境规范

资料中存在需要澄清的矛盾：

- 2026-07-13 会议称客户提供了 Mercury CRM Sandbox。
- Mercury mapping HTML 称 API 没有 UAT/sandbox。

需要确认所谓 Sandbox 是：

- 独立 API host；或
- 生产 API host 下的测试 branch/account；或
- 只有 CRM UI 的测试账号。

同时需要确认哪些测试 records 允许执行 POST/PUT，以及如何清理测试数据。

### 9.5 错误、限流和幂等规范

至少需要：

- 400、401、403、404、409、429、500 等真实响应样例。
- 429 是否返回 `Retry-After`。
- API timeout 建议。
- 可重试与不可重试错误分类。
- 重复 POST 的防重方式。
- 是否支持 idempotency key/correlation ID。
- 每个对象的数组上限、字段长度和请求大小限制。

### 9.6 黄金测试案例

至少提供以下去敏案例：

1. 单申请人新建 Opportunity。
2. 双申请人新建 Opportunity。
3. 更新已有 Opportunity。
4. 包含多项 employment、asset、liability 和 living expense。
5. 输入 Fact Find/OCR approved snapshot。
6. 期望 POST/PUT payload。
7. 写入后的 Mercury UI 截图或 GET response。

## 10. 建议补充的项目规范

### 10.1 Mercury Connector Contract

建议新增 `docs/MERCURY_API_CONTRACT.md`，记录：

- API version 和环境。
- 认证与 secret 管理。
- endpoint catalogue。
- request/response schemas。
- 错误模型。
- timeout/retry/rate-limit。
- idempotency。
- 日志脱敏要求。
- test fixtures 和 acceptance criteria。

### 10.2 Mapping Configuration

建议将出站 mapping 版本化，例如：

```text
backend/app/integrations/mercury/mappings/v1.json
```

不要把 85 个字段映射硬编码在 service 函数中。mapping 应包含 direction、transform、required、nullable、operation 和 verification status，并保存 mapping version 到 approved/sync records，保证审计可重现。

### 10.3 Sync Item Tracking

当前 `crm_update_tracking` 只表示整次同步，粒度不足。建议增加 `crm_update_item`，或在 audit event 中保存每个对象的执行结果：

- entity type
- local record ID
- Mercury external ID
- operation
- request hash
- attempt count
- response status
- error code/message
- started/completed timestamps

敏感值和 API Key 不得写入日志。

## 11. 实施阶段建议

### Phase 0：客户资料补齐

- 获取 Swagger/OpenAPI。
- 获取 outbound mapping 和 payload 样例。
- 明确 API 测试环境。
- 获取黄金测试案例。

### Phase 1：Approved data pipeline

- 实现 approval validation。
- 聚合 reviewed/corrected 字段。
- 生成 immutable approved snapshot。
- 写入 approval 和 audit 记录。

### Phase 2：Mercury mapping 与 client

- 创建 Mercury config 和 secret loading。
- 实现 mapping registry、normalisers 和 validators。
- 实现 request/response client、timeout、retry 和 rate limit。
- 使用 mock server 完成 contract tests。

### Phase 3：新建/更新同步

- 先实现一个最小 vertical slice，例如单 Applicant Contact + Opportunity。
- 保存 external IDs。
- 增加 Applicant 2、related parties 和重复对象。
- 增加资产、负债、收入和支出。

### Phase 4：真实环境验证

- 在客户批准的测试 record 上执行写入。
- GET 回读并与 approved snapshot 对比。
- 验证 UI、状态、错误恢复和重试。
- 完成客户验收和部署 runbook。

## 12. 建议验收标准

一个申请只有满足以下条件，才能称为“成功回传 CRM”：

- [ ] Approve 前所有必要字段均已审核或明确豁免。
- [ ] `approved_fact_find_data` 保存完整、不可变的数据版本。
- [ ] 本次同步使用的 mapping/API version 可追踪。
- [ ] Mercury 所需字段通过 schema 和 enum 校验。
- [ ] Applicant、Opportunity 和重复子对象按正确顺序创建/更新。
- [ ] 所有 Mercury external IDs 已保存。
- [ ] 重复执行不会创建重复记录。
- [ ] 部分失败可追踪、可重试且不会破坏已成功对象。
- [ ] GET 回读的关键字段与 approved snapshot 一致。
- [ ] `crm_update_tracking` 显示 completed。
- [ ] audit event 记录审批者、时间、操作和结果。
- [ ] 日志、数据库和前端均未暴露 API Key/Token。
- [ ] 客户在 Mercury UI 中确认数据进入正确对象和字段。

## 13. 当前阻塞项

| 阻塞项 | 影响 | 所需负责人 |
| --- | --- | --- |
| 本地没有官方 Swagger/OpenAPI | 无法确认 POST/PUT schema | 客户 / AIMESHLABS |
| 缺少 outbound payload 示例 | 无法安全实现 payload builder | 客户 / AIMESHLABS |
| Sandbox/API 环境定义矛盾 | 无法安全执行写测试 | 客户 |
| `crm_field_mapping` 未 seed | 代码无法配置化映射 | Backend / Integration |
| Approve 仅更新 status | 没有 approved snapshot 和同步任务 | Backend |
| OCR 结果未完整聚合到业务模型 | 无稳定 canonical outbound source | Backend / OCR |
| 无 Mercury client 和集成测试 | 无法执行或验证回传 | Integration |

## 14. 最终判断

项目已有足够资料证明 CRM 自动回传是客户确认的核心目标，也有不错的数据模型基础；但现有 Mercury 文档主要适合读取、比对和字段分析，尚不能独立支撑生产写入。

下一步不应直接把 OCR JSON 接到 Mercury API。正确顺序是先取得官方写接口契约和测试权限，实现 approved canonical data，再开发配置化的 Mercury connector。完成 Swagger、outbound mapping、测试环境和黄金案例四项资料补齐后，项目才具备开始真实 CRM write-back 集成的条件。
