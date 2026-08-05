# Rules Engine Phase 1 前端开发交接

> 负责人：前端开发者  
> 开始前必读：`RULES_ENGINE_PHASE1_MASTER_PLAN.md` 和其中冻结的 API JSON  
> 目标：完成 approved application 列表、开始/重新评分和可刷新的风险报告页，并将现有 Dashboard/Applications 接入真实分数。

## 1. 前端实施要求

1. 完整阅读总体计划，特别是第 3、4、5、8 节。
2. 阅读现有：
   - `frontend/src/components/dashboard-shell.jsx`
   - `frontend/src/lib/api.js`
   - `frontend/src/app/(dashboard)/applications/page.js`
   - `frontend/src/app/(dashboard)/dashboard/page.js`
   - `frontend/src/app/(dashboard)/application/[id]/page.js`
   - `frontend/src/app/(dashboard)/applications/new/page.js`
   - `frontend/src/components/ui/*`
   - `frontend/src/app/globals.css`
3. 尽量复用现有 shadcn/ui 和 Lucide icons，不在 Phase 1 引入新 UI framework、chart library 或状态管理库。
4. 前端不得计算规则、相似度、文件分数或总分。所有风险结果只信任后端 response。
5. 不直接使用 Supabase client 查评分表；一律通过 `api.js` 调 Flask API。
6. 不将 `frontend/src/lib/mock-data.js` 的假风险分接入 production 路径。

## 2. 交付文件

建议新增：

```text
frontend/src/app/(dashboard)/rules-engine/page.js
frontend/src/app/(dashboard)/rules-engine/[submissionId]/page.js
frontend/src/components/rules-engine/risk-score-card.jsx
frontend/src/components/rules-engine/risk-scale.jsx
frontend/src/components/rules-engine/document-result-row.jsx
frontend/src/components/rules-engine/rule-result-table.jsx
frontend/src/lib/risk-display.js
frontend/tests/risk-display.test.mjs
```

必须更新：

```text
frontend/src/components/dashboard-shell.jsx
frontend/src/lib/api.js
frontend/src/app/(dashboard)/applications/page.js
frontend/src/app/(dashboard)/dashboard/page.js
frontend/src/app/(dashboard)/applications/new/page.js
```

如需更新页面标题，可改 `DashboardShell` 的标题映射，不要继续使用简单 `pathname.includes("application")` 推断 Rules Engine 标题。

## 3. 路由和导航

### 3.1 新路由

```text
/rules-engine
/rules-engine/[submissionId]
```

列表页和报告页都放在现有 `(dashboard)` route group，自动复用 authenticated dashboard layout。

### 3.2 侧边栏

在 `navItems` 中增加：

```javascript
{ name: "Rules Engine", href: "/rules-engine", icon: ShieldAlert }
```

建议顺序：

```text
Dashboard
Applications
Rules Engine
Settings
```

活动状态不能只用 `pathname === item.href`；报告路由 `/rules-engine/<id>` 也必须高亮 Rules Engine。建议：

```javascript
const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
```

## 4. API client

在 `frontend/src/lib/api.js` 增加：

```javascript
getApprovedSubmissions() {
  return apiFetch("/submissions?status=approved");
},

startRiskAssessment(submissionId) {
  return apiFetch(`/submissions/${encodeURIComponent(submissionId)}/risk-assessment`, {
    method: "POST",
  });
},

getRiskAssessment(submissionId) {
  return apiFetch(`/submissions/${encodeURIComponent(submissionId)}/risk-assessment`);
},
```

必须复用现有 `apiFetch`，以便统一处理 Supabase session、401 退出和 API error code。

POST 不发 request body。不要在前端传送总分、规则选择或阈值。

## 5. Rules Engine 列表页

### 5.1 数据源

```http
GET /api/v1/submissions?status=approved
```

页面只使用后端已过滤的 approved data；前端可再作防御性 filter，但不能依赖客户端 filter 代替后端过滤。

### 5.2 列表列

| 列 | 数据 |
|---|---|
| Application | `local_application_id` 和可选 `crm_application_id` |
| Applicant | `customer_name` |
| Loan Type | 复用现有文案映射 |
| Approved/Created Date | Phase 1 API 如无 approved_at，使用 `created_at` 并标注 Application Date |
| Assessment Status | `assessment_status` |
| Risk Score | `overall_risk_score` + `risk_level` |
| Action | Start / Recalculate / View Report |

### 5.3 操作状态

| `assessment_status` | 主操作 | 辅助操作 |
|---|---|---|
| `not_started` | Start Assessment | 无 |
| `processing` | 禁用的 Assessing… | 无 |
| `completed` | View Report | Recalculate |
| `failed` | Retry Assessment | 可显示错误提示 |

POST 是同步的，但点击后仍要立即将该行本地状态设为 processing，防止双击。

成功：

```javascript
const report = await api.startRiskAssessment(id);
router.push(`/rules-engine/${id}`);
```

409 readiness error：

- 保留在列表页。
- 用 toast 显示 `error.message`。
- 如 `error.details` 有缺少文件/字段，在可扫读对话框或行下详情中列出，不要只 `console.error`。

### 5.4 筛选

Phase 1 至少实现：

- 按 applicant/Application ID 搜索。
- 按 assessment status 筛选。
- 按 risk level 筛选。

页面数据量在演示中较小，可在客户端筛选；不需新增后端筛选 API。

## 6. 风险报告页

### 6.1 加载

`submissionId` 来自 route param。页面 mount 后调：

```javascript
api.getRiskAssessment(submissionId)
```

不依赖从列表页 navigation state 传入报告，确保页面刷新和直接访问 URL 可用。

404 `risk_assessment_not_found`：显示空状态和 Start Assessment 按钮，不要显示通用“Submission not found”。

### 6.2 页面区块

按设计稿实现四个主区块：

1. 页头：风险评估报告、Application Reference、Report Date。
2. 总览卡：圆环分数、`failed_document_count / 4`、每失败文件 +25、五档风险标尺。
3. 文件结果：Fact Find 基准行 + ID/Payslip/Bank/NOA 四行，显示 pass/fail 和匹配 applicant。
4. 不一致字段明细：仅默认列出 `status=fail`，可展开查看所有 pass/N/A 规则。

### 6.3 圆环

不引入 chart library。使用 CSS `conic-gradient` 或 SVG circle：

```javascript
const degrees = report.overall_risk_score * 3.6;
```

这只是视觉比例，不是业务计分。分数文本必须直接显示 API 值。

### 6.4 五档标尺

固定节点：

```text
0 Low
25 Lower
50 Medium
75 Higher
100 High
```

根据 API score 高亮恰好一个节点。因为后端保证只有五个可能分数，不得在前端做就近取整。

### 6.5 文件结果

Fact Find 行是“Comparison baseline”，不在 `document_results` 中，前端使用固定基准行。

四个文件行必须展示：

- display name。
- original file name。
- `matched_applicant_numbers`：例如 `Matched to Applicant 2`。
- status badge。
- 0 或 +25。
- 展开/收起 rules。

行顺序固定：ID、Payslip、Bank Statement、NOA，不依赖 API 数组偶然顺序。

### 6.6 不一致明细表

列：

| UI 列 | API |
|---|---|
| Document | parent `display_name` |
| Rule | `rule_id` + `label` |
| Compared Field | `document_field_keys.join(', ')` |
| Fact Find Baseline | `fact_find_value` |
| Extracted Document Value | `document_value` |
| Result | `status` |

可在展开详情显示 normalised values、similarity/difference 和 threshold。

账号、BSB 只在前端显示脱敏值：

- Account number：仅显示尾 4 位，如 `•••• 1234`。
- BSB：可显示，但不在 console/log 里输出整份 report。
- TFN 不属于 13 条规则，绝不得出现在 report UI。

## 7. 风险颜色和显示 helper

在 `frontend/src/lib/risk-display.js` 建立唯一映射，避免三个页面各自写一套：

```javascript
export const RISK_DISPLAY = {
  low:    { label: "Low Risk",    score: 0,   className: "...green..." },
  lower:  { label: "Lower Risk",  score: 25,  className: "...slate/blue..." },
  medium: { label: "Medium Risk", score: 50,  className: "...blue/amber..." },
  higher: { label: "Higher Risk", score: 75,  className: "...orange..." },
  high:   { label: "High Risk",   score: 100, className: "...red..." },
};
```

同时提供：

```javascript
riskDisplay(level)
assessmentStatusDisplay(status)
documentStatusDisplay(status)
maskAccountNumber(value)
```

未评分不得默认绿色。必须显示 `Not assessed`。

## 8. 修正现有 Risk Score UI

### 8.1 Applications page

当前页面在 risk level 为 null 时会落入绿色分支。必须改为：

- `assessment_status !== completed`：中性 `Not assessed` / `Assessment failed`。
- completed：使用 `risk-display.js`。
- 分数 0 是有效数值，使用 `??`，禁止 `score || 'N/A'`。

### 8.2 Dashboard

- High-risk count 使用 `risk_level === 'high'`，不再使用旧 mock 的 `'High'`。
- 表格对未评分记录显示中性状态。
- 不得将 0 分显示成 N/A。

### 8.3 Application Review

将页头的 Risk badge 改为同一 helper。该页不需展示完整规则报告，可添加 `View Risk Report` 链接（仅 completed 时）。

## 9. 一类一文件限制

`applications/new/page.js` 中 Phase 1 五种文件每种最多一份：

```text
fact_find
id_100
payslip
bank_statement_3m
ato_notice
```

实现要求：

- 一个 category 已有文件时，再选择应替换前一份或弹出“Remove existing file first”；两种 UX 选一并保持一致。
- 禁止在 `FormData` 中对同一 category append 多次。
- 提交前再做一次客户端唯一性校验。
- 后端仍会二次校验，前端限制不是安全边界。

## 10. Loading、错误和可访问性

### 10.1 Loading

- 列表首次加载：居中 spinner/skeleton。
- 行评分：只禁用当前行，不锁死整页。
- 报告加载：总体 skeleton，避免先显示 0 分再跳变。

### 10.2 Error

- 所有 API error 必须有用户可见的 toast/页面错误，不得只 `console.error`。
- 401 由 `apiFetch` 处理退出。
- 404 report not found 显示可开始评分的空状态。
- 409 显示具体 readiness 问题。
- 500/502 显示重试按钮，不显示内部错误堆栈。

### 10.3 Accessibility

- 分数和状态不能只靠颜色，必须有文字。
- 可展开行使用 button/accordion，支持键盘和 `aria-expanded`。
- spinner 区域使用 `aria-live` 或可读 loading text。
- 表格小屏可横向滚动，不裁剪不一致值。

## 11. 前端测试计划

现有项目使用 Node built-in test runner，新纯 helper 必须可直接在 `.mjs` test 中导入。至少测试：

### 11.1 `risk-display.test.mjs`

- 五个 risk level 都返回正确 label/score。
- null/unknown 返回 Not assessed 中性显示。
- score 0 不被当作空值。
- account masking 只保留尾 4 位。
- document status pass/fail/N/A/incomplete 文案正确。

### 11.2 页面手工/自动验收

- 列表只有 approved applications。
- not_started 可开始；completed 可查看和重算。
- 快速双击不会发送两个并发 POST。
- 0/25/50/75/100 在圆环和标尺正确高亮。
- 同一文件多条 fail 仍显示 +25。
- 失败明细显示基准值和文件值。
- 报告直接 URL 访问和刷新正常。
- Applicant 2 匹配文案正确。
- Recalculate 后页面显示新 report，不残留旧明细。
- 409 缺文件错误可见。
- 每个 Phase 1 category 最多一份上传文件。

## 12. 命令级验证

在 `frontend` 下执行：

```bash
npm test
npm run lint
npm run build
```

三个命令必须全部通过。不得为了合并而关闭 ESLint rule 或删除现有测试。

## 13. 与后端的联调清单

联调前要求后端提供总体计划中约定的测试 submission。逐项验证：

- [ ] `GET /submissions?status=approved` 包含 assessment 四字段。
- [ ] POST 首次评分返回 201 或 200，JSON 可直接渲染。
- [ ] GET 返回与 POST 相同报告。
- [ ] 重新 POST 后 GET 只看到新结果。
- [ ] 404 和 409 的 `ApiError.code` 可正确区分。
- [ ] risk level 是 lowercase `low/lower/medium/higher/high`。
- [ ] `document_results` 恰好四类，规则合计恰好 13。

## 14. 前端 Definition of Done

- [ ] 侧边栏新增 Rules Engine，列表和报告路由都正确高亮。
- [ ] Rules Engine 列表仅显示 approved applications。
- [ ] Start、processing、View、Recalculate、Retry 状态完整。
- [ ] 报告页严格消费后端 JSON，不在客户端评分。
- [ ] 总分、五档标尺、四文件、失败明细符合设计稿。
- [ ] 页面刷新可从 GET API 恢复报告。
- [ ] 0 分正确显示，未评分不假装成绿色低风险。
- [ ] Applications、Dashboard、Application Review 共用一套 risk display helper。
- [ ] 每种 Phase 1 document type 最多一份。
- [ ] 账号脱敏，TFN 不出现在报告或日志。
- [ ] loading/error/empty/accessibility 状态完整。
- [ ] `npm test`、`npm run lint`、`npm run build` 全部通过。
