# Rules Engine Phase 1 总体实施与交接计划

> 状态：待开发  
> 范围：仅实现 13 条 Fact Find ↔ ID / Payslip / Bank Statement / NOA 必要规则  
> 参与者：数据库开发者、后端开发者、前端开发者  
> 本文档是三端共同契约；任何人或 AI agent 开始工作前必须先完整阅读。

## 1. Phase 1 交付目标

建立一个可完整演示的风险评分闭环：

```text
Application 完成 OCR 和人工审核
  -> submission_status = approved
  -> Rules Engine 列表只显示 approved applications
  -> 用户点击 Start Assessment / Recalculate
  -> 后端执行 13 条规则
  -> 每类文件有任意一条 FAIL 则贡献 25 分
  -> 数据库 upsert 并覆盖该 submission 的旧评分
  -> 前端展示 0/25/50/75/100 和字段不一致明细
```

本阶段不保留历史评分。每个 `fact_find_submission` 在数据库中最多只有一条 `risk_assessment`。

## 2. 不在 Phase 1 范围内

- 其余 39 条规则。
- Payslip ↔ NOA、Payslip ↔ Bank Statement、ID ↔ NOA 等非 Fact Find 比对。
- 银行交易分类、周期性支出识别、未申报负债检测。
- 文件篡改取证、图像指纹、跨 Application 重复证件。
- 多份同类文件选择和历史版本。
- 每个 Applicant 独立的 0-100 总分。
- 规则可视化编辑器、按 lender 配置阈值。
- 修改 Fact Find 表单或新增收入字段。

## 3. 分数和状态契约

### 3.1 四个评分桶

| 文件 | 上传 `document_type` | 分数 |
|---|---|---:|
| ID | `id_100` | 0 或 25 |
| Payslip | `payslip` | 0 或 25 |
| Bank Statement | `bank_statement_3m` | 0 或 25 |
| NOA | `ato_notice` | 0 或 25 |

Fact Find 的 `document_type` 是 `fact_find`，仅作为基准，不产生第五个 25 分。

### 3.2 规则状态

| 状态 | 含义 | 是否导致文件 +25 |
|---|---|---:|
| `pass` | 实际执行且一致 | 否 |
| `fail` | 实际执行且明确不一致 | 是 |
| `not_applicable` | 条件不适用，如没有申报储蓄资产 | 否 |
| `incomplete` | 必需输入缺失；理论上应被 Approval gate 阻止 | 否 |
| `error` | 规则执行异常 | 否，整次评分应失败 |

文件分数计算：

```text
document_score = 25 if any(rule.status == "fail") else 0
overall_risk_score = id_score + payslip_score + bank_statement_score + noa_score
```

同一文件失败 1 条或 5 条规则都只加 25 分。

### 3.3 五档风险等级

| 分数 | 数据库 `risk_level` | API/UI 文案 |
|---:|---|---|
| 0 | `low` | Low Risk |
| 25 | `lower` | Lower Risk |
| 50 | `medium` | Medium Risk |
| 75 | `higher` | Higher Risk |
| 100 | `high` | High Risk |

## 4. 冻结的 13 条规则

### 4.1 ID（3 条）

| 规则 ID | Fact Find 输入 | ID 输入 | 通过条件 |
|---|---|---|---|
| `FF-ID-001` | `applicant_{n}_full_name` | `full_legal_name` | 姓名标准化后精确一致或相似度 >= 0.95 |
| `FF-ID-002` | 当前/历史地址组件 | `residential_address` | 街道号、邮编精确一致，整体相似度 >= 0.90 |
| `FF-ID-003` | `cover_form_date` | `expiry_date` | `expiry_date >= cover_form_date` |

### 4.2 Payslip（3 条）

| 规则 ID | Fact Find 输入 | Payslip 输入 | 通过条件 |
|---|---|---|---|
| `FF-PS-001` | `applicant_{n}_full_name` | `employee_name` | 姓名标准化后精确一致或相似度 >= 0.95 |
| `FF-PS-002` | 对应 applicant 的 current/secondary employer name | `employer_name` | 机构名标准化后相似度 >= 0.90 |
| `FF-PS-003` | 已匹配 employer 的 `start_date` | `pay_period_end` | `pay_period_end >= start_date` |

### 4.3 Bank Statement（5 条）

| 规则 ID | Fact Find 输入 | Bank 输入 | 通过条件 |
|---|---|---|---|
| `FF-BS-001` | `applicant_{n}_full_name` | `account_holder_name` | 持有人名称包含任一 Fact Find applicant |
| `FF-BS-002` | `repayment_account_name` | `account_holder_name` | 姓名/账户名标准化后相似度 >= 0.95 |
| `FF-BS-003` | `repayment_account_bsb` | `bsb` | 去除非数字后均为 6 位并精确一致 |
| `FF-BS-004` | `repayment_account_number` | `account_number` | 保留前导零后精确一致；遮盖账号见下文 |
| `FF-BS-006` | savings/term deposit 的申报 `value` | `closing_balance` | savings 差异 <= 10%；term deposit 绝对差 <= 1 AUD |

`FF-BS-004` 遮盖账号仅在以下条件同时成立时允许比较尾 4 位：

- Bank account number 明确带遮盖符，或只剩 4 位。
- `FF-BS-002` 已 `pass`。
- `FF-BS-003` 已 `pass`。
- Fact Find 账号尾 4 位与 Bank 一致。

`FF-BS-006` 没有申报 savings/term deposit 时返回 `not_applicable`，不得失败。Phase 1 演示数据应保证最多只有一个需匹配的储蓄/定期存款记录；多记录时取差异最小的一条，并在结果中记录选中的 Fact Find field key。

### 4.4 NOA（2 条）

| 规则 ID | Fact Find 输入 | NOA 输入 | 通过条件 |
|---|---|---|---|
| `FF-NOA-001` | `applicant_{n}_full_name` | `taxpayer_name` | 姓名标准化后精确一致或相似度 >= 0.95 |
| `FF-NOA-002` | 当前/历史地址组件 | `taxpayer_address` | 街道号、邮编精确一致，整体相似度 >= 0.90 |

NOA 没有 `taxpayer_address` 时，`FF-NOA-002` 返回 `not_applicable`。

## 5. 申请人绑定契约

Phase 1 不新增文件与 applicant 的关联表。后端必须在每次评分时基于主体姓名对整份文件做一次绑定：

| 文件 | 主体字段 |
|---|---|
| ID | `full_legal_name` |
| Payslip | `employee_name` |
| Bank Statement | `account_holder_name` |
| NOA | `taxpayer_name` |

算法：

1. 从 Fact Find 读取 Applicant 1 和 Applicant 2 的姓名（空姓名忽略）。
2. 将文件主体姓名与每个 applicant 比较。
3. 唯一匹配时，记录 `matched_applicant_number=1|2`。
4. 无匹配时，姓名规则 `fail`，不执行该文件依赖 applicant 的其余规则；这些规则标记 `incomplete`。
5. 同一份文件的其他 applicant-level 字段必须只与已绑定的同一 applicant 比较，禁止逐字段分别选择不同 applicant。
6. Bank Statement 同时包含两个 applicant 姓名时允许 `matched_applicant_numbers=[1,2]`；账户规则仍使用 submission-level repayment account。

Phase 1 的总分是 application-level 四桶总分，不对 Applicant 1/2 分别计算 0-100。

## 6. 字段取值和标准化契约

### 6.1 取值优先级

```text
comparison_value = normalised_value if normalised_value is not null else raw_value
```

人工修正已经由现有 Review API 写回 `normalised_value`，因此 Rules Engine 不得只使用 `raw_value`。

### 6.2 姓名标准化

- Unicode NFKC。
- 转大写。
- 删除 `MR`, `MRS`, `MS`, `MISS`, `DR` 称谓。
- 标点、连字符视为空格。
- 合并连续空格。
- 保留姓名词元，禁止静默删除不同的姓。
- 首先精确比较；不精确时使用确定性字符串相似度，阈值 0.95。

### 6.3 机构名标准化

- Unicode NFKC、大写、去标点、合并空格。
- `&` 统一为 `AND`。
- 比较副本可去除 `PTY`, `LTD`, `LIMITED`, `PTY LTD`等后缀，报告仍保留原值。
- 阈值 0.90。

### 6.4 地址标准化

- Unicode NFKC、大写、去标点、合并空格。
- 统一 `ST/STREET`, `RD/ROAD`, `AVE/AVENUE`, `DR/DRIVE`, `CRES/CRESCENT`, `HWY/HIGHWAY`。
- 提取街道号和 4 位邮编；两者存在时必须精确一致。
- 对当前和历史地址逐一计算，使用最高相似度，阈值 0.90。

### 6.5 标识符和金额

- BSB/账号：仅删除显示用空格和连字符，必须保留前导零，禁止模糊匹配。
- 金额：使用 `Decimal`，禁止 float；报告中保留两位小数。
- 比例差异：`abs(document - fact_find) / abs(fact_find)`；Fact Find 为 0 时仅当 document 也为 0 才通过。

## 7. 审批前置条件

Rules Engine 只允许评分 `submission_status=approved` 的 submission。后端在执行评分时仍必须二次校验，不得只依赖前端。

必须满足：

- 每种 `fact_find`, `id_100`, `payslip`, `bank_statement_3m`, `ato_notice` 恰好一份。
- 五份文件都有最新 `job_status=completed` 的 OCR job。
- Fact Find 至少有 Applicant 1 姓名和 `cover_form_date`。
- ID 有 `full_legal_name`, `residential_address`, `expiry_date`。
- Payslip 有 `employee_name`, `employer_name`, `pay_period_end`。
- Bank Statement 有 `account_holder_name`, `bsb`, `account_number`, `closing_balance`。
- NOA 有 `taxpayer_name`。`taxpayer_address` 是可选字段。

不满足时 `POST risk-assessment` 返回 409，不得产生一个误导性的 0 分报告。

## 8. 共享 API 契约

### 8.1 Approved applications 列表

复用：

```http
GET /api/v1/submissions?status=approved
```

每行在现有字段上增加：

```json
{
  "assessment_status": "not_started",
  "overall_risk_score": null,
  "risk_level": null,
  "assessed_at": null
}
```

`assessment_status` API 可选值：`not_started`, `processing`, `completed`, `failed`。`not_started` 是后端对无数据库记录的派生值，不写入数据库。

### 8.2 开始/重新评分

```http
POST /api/v1/submissions/{submission_id}/risk-assessment
Authorization: Bearer <token>
```

- 新建或覆盖同一 submission 的结果。
- 13 条规则是本地确定性计算，Phase 1 采用同步 API。
- 首次成功可返回 201，覆盖可返回 200；前端必须同时接受。
- 响应体是完整报告，与 GET 一致。

### 8.3 取得已保存报告

```http
GET /api/v1/submissions/{submission_id}/risk-assessment
```

- 有报告：200 + 完整报告。
- 未评分：404，`error.code=risk_assessment_not_found`。

### 8.4 完整报告 JSON

```json
{
  "assessment_id": "uuid",
  "submission_id": "uuid",
  "application_reference": "external CRM id or local application uuid",
  "customer_name": "Alice Smith",
  "assessment_status": "completed",
  "ruleset_version": "phase1-v1",
  "overall_risk_score": 25,
  "risk_level": "lower",
  "failed_document_count": 1,
  "total_scored_documents": 4,
  "assessed_at": "2026-08-02T10:30:00Z",
  "document_results": [
    {
      "document_type": "id_100",
      "display_name": "ID",
      "source_document_id": "uuid",
      "original_file_name": "licence.jpg",
      "matched_applicant_numbers": [1],
      "status": "fail",
      "score": 25,
      "rules": [
        {
          "rule_id": "FF-ID-001",
          "label": "Applicant name matches ID",
          "status": "fail",
          "fact_find_field_keys": ["applicant_1_full_name"],
          "document_field_keys": ["full_legal_name"],
          "fact_find_value": "ALICE SMITH",
          "document_value": "ALICIA SMITH",
          "normalised_fact_find_value": "ALICE SMITH",
          "normalised_document_value": "ALICIA SMITH",
          "comparison": {
            "operator": "name_similarity",
            "similarity": 0.88,
            "threshold": 0.95
          },
          "message": "Applicant name does not match ID."
        }
      ]
    }
  ]
}
```

字段名必须按该契约保持不变。前端不得自行重算分数、相似度或文件状态。

## 9. 三人工作量分配

| 责任人 | 必须交付 | 不得承担/修改 |
|---|---|---|
| 数据库开发者 | `risk_assessment` migration、索引、RLS、schema verification、rollback 说明 | 规则计算、Flask API、React UI |
| 后端开发者 | 13 规则、标准化、applicant 绑定、Supabase repository、3 个 API、现有 submission API 风险字段、测试、API 文档 | 数据库 migration 结构擅自改名、前端视觉实现 |
| 前端开发者 | Rules Engine 导航、approved 列表、评分操作、报告页、API client、五档样式、一类一文件限制、测试 | 前端计算风险分、直接读 Supabase、改规则阈值 |

详细实施分别见：

- `RULES_ENGINE_PHASE1_DATABASE_HANDOFF.md`
- `RULES_ENGINE_PHASE1_BACKEND_HANDOFF.md`
- `RULES_ENGINE_PHASE1_FRONTEND_HANDOFF.md`

## 10. 开发和合并顺序

### 10.1 分支建议

```text
feature/rules-engine-phase1-db
feature/rules-engine-phase1-backend
feature/rules-engine-phase1-frontend
```

### 10.2 并行工作

- 数据库开发者先提交 migration 和验证 SQL。
- 后端可用 fake repository 并行完成规则纯函数和 route tests。
- 前端可根据本文第 8 节的冻结 JSON fixture 并行开发页面。

### 10.3 合并顺序

1. Database PR 合并并在共享 Supabase 应用 migration。
2. Backend PR 合并，后端集成测试通过。
3. Frontend PR 合并，完成真实 API E2E。

不允许前端 PR 为等待后端而将 mock 分数保留到 production path。

## 11. 全局 Definition of Done

- [ ] 数据库 migration 可在空环境一次成功执行，RLS 通过验证。
- [ ] `GET /submissions?status=approved` 返回真实评分字段，不再硬编码 `null`。
- [ ] 未 approved、文件不全、OCR 未完成的 submission 不能评分。
- [ ] 13 条规则都有 pass/fail 单元测试。
- [ ] 0/25/50/75/100 和四文件分数聚合有测试。
- [ ] Applicant 2 文件可正确绑定，不依赖 mapper 中写死的 `applicant_number=1`。
- [ ] 重新评分覆盖旧结果，数据库仍只有一条记录。
- [ ] Rules Engine 页只列 approved applications。
- [ ] 报告页刷新后仍能从数据库恢复。
- [ ] 报告显示每条失败规则的 Fact Find 字段、基准值、文件字段、提取值和结果。
- [ ] Applications 和 Dashboard 显示数据库真实分数。
- [ ] 每种 Phase 1 文件的上传数量被限制为 1。
- [ ] Backend pytest、frontend lint/test/build 全部通过。

## 12. 实施中的变更控制

如发现字段不存在或契约无法实现，AI agent 必须：

1. 先用代码和实际 migration 证明问题。
2. 停止对该契约的猜测实现。
3. 在 PR/交接中记录阻塞、影响规则 ID 和建议变更。
4. 由三端共同确认后同步更新本文和 API contract。

禁止任何一端单方改名 JSON 字段、规则 ID、risk level 枚举或评分公式。
