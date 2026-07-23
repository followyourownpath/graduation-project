# Fact Find 后端 ↔ 前端交接说明

> 更新日期：2026-07-23  
> 后端负责人：Jiawen（Gavin085）  
> 分支 / PR：`feature/fact-find-extraction` · [#13](https://github.com/unsw-cse-comp99-3900/capstone-project-26t2-9900-w19b-bread/pull/13)  
> 状态：**可以开始前后端联调**；PR 暂未合入 `main`（等 review）。CI 已全绿。

---

## 1. 一句话结论

**可以交付给前端联调。**  
后端已支持 `document_type=fact_find` 的上传 → 提取 → 落库；你们在 `main`/本分支上的新建申请页已有 Fact Find 上传入口（`document_types` 用 `fact_find`）。  

请 **checkout 本功能分支起后端**（或等 #13 merge 进 main），不要只用旧的不含 Fact Find 提取逻辑的 backend。

---

## 2. 你们需要拉什么代码

```bash
git fetch origin
git checkout feature/fact-find-extraction
# 或：git pull origin feature/fact-find-extraction
```

- 前端：本分支已 merge 过最新 `main`（含 Fact Find UI + Toast，PR #12）。  
- 后端：本分支含 AcroForm 直读 + Azure OCR 分页解析。  
- **本地 `.env` 不要提交**；向 Jiawen / Huaiyu 要 Supabase +（扫描件测试才需要）Azure 配置。

### 起后端

```bash
cd backend
# 确认 .venv 与 .env 已配置
.venv/bin/python wsgi.py
# http://localhost:5000
curl http://localhost:5000/api/v1/health
```

期望 `integrations_configured.supabase` / `azure_document_intelligence` 按你本地配置显示。

### 起前端（照旧）

```bash
cd frontend
npm install   # 本分支可能有 sonner 等新依赖
npm run dev   # 默认 localhost:3000，api.js 指向 localhost:5000
```

`frontend/src/lib/api.js`：`USE_REAL_API = true`，`BASE_URL = http://localhost:5000/api/v1`。

---

## 3. 我们完成了什么（后端）

### 3.1 能力清单

| 能力 | 说明 |
|------|------|
| 文档类型 | Intake 白名单已加 **`fact_find`** |
| 路径 A：AcroForm 直读 | 电子填写、仍带表单控件的 PDF → PyMuPDF 读控件，**不调 Azure** |
| 路径 B：Azure OCR | 扫描件 / 压平件（无控件）→ 按 F0 限制 **每请求最多 2 页** 切分、分析、合并 → 再解析成业务字段 |
| 空白可填表 | 有控件但全空 → HTTP **422**，`error.code = fact_find_blank_form` |
| 字段落库 | 与 payslip 同构，写入 Supabase **`extracted_field`** |
| 原始备份 | Storage bucket **`ocr-responses/{document_id}/{job_id}.json`** |
| 单测 | `tests/test_fact_find.py`、`tests/test_fact_find_ocr.py` |
| Smoke | `tools/smoke_test_fact_find.py`（本地已跑通满表 7 页 / **264** 字段） |

### 3.2 关键代码位置

| 文件 | 作用 |
|------|------|
| `backend/app/normalization/fact_find.py` | AcroForm 直读 |
| `backend/app/normalization/fact_find_mapping.json` | 控件名 → field_key（Mapping Matrix v1） |
| `backend/app/normalization/fact_find_ocr.py` | Azure layout JSON → 字段 |
| `backend/app/services/azure_paging.py` | PDF 分页切块 + 结果合并 |
| `backend/app/services/ocr_pipeline.py` | 管线分流与落库 |
| `backend/app/routes/intake.py` | `DOCUMENT_TYPES` 含 `fact_find` |
| `backend/tests/fixtures/fact_find_filled.pdf` | 满表测试 PDF |

### 3.3 已验证的端到端（后端 API）

- 满表 fixture：`pages=7`，`fields=264`，`ocr_extraction_job.provider=acroform_direct_read`，`model_name=pymupdf`  
- 示例 job（历史 smoke）：`9a1f35be-dcc4-446d-b7a5-eeecb9671182`（库里应有 264 条 `extracted_field`）

---

## 4. 端到端流程（前后端一起怎么走）

```
[前端] 新建申请
  → POST /api/v1/applications          { customer_name, loan_type, ... }
  → 得到 submission_id

[前端] 对每个文件（含 Fact Find PDF）
  → POST /api/v1/submissions/{submission_id}/documents
       multipart: file + document_type
       Fact Find 时 document_type 必须是字面量：fact_find

  → 得到 document.id

[前端]（你们 api.js 已做）POST /api/v1/documents/{document_id}/ocr
  → 后端同步处理（可能较久：直读很快；OCR 分页可能数分钟）

[后端管线自动分流]
  fact_find + PDF + 有控件且有值  → AcroForm → extracted_field
  fact_find + PDF + 有控件但全空  → 422 fact_find_blank_form
  fact_find + PDF + 无控件        → Azure 分页 OCR → fact_find_ocr → extracted_field
  其它类型（如 payslip）          → 原有逻辑

[前端] 审核 / 详情页
  → GET /api/v1/documents/{document_id}/extracted-data
  → 展示 fields 列表（与 payslip 相同结构，字段数量会多很多）
```

### 4.1 前端已有的对接点（请确认）

`applications/new/page.js`：

- Fact Find 上传使用 **`categoryId = 'fact_find'`**  
- `handleSubmit` 里：`formData.append('document_types', categoryId)`  
→ 会正确传到后端的 `document_type=fact_find`。  

**注意：**

- 「Email sync」目前是 **UI stub**，不会真上传附件；联调请用 **Upload Fact Find PDF**。  
- `factFindImported`（模拟导入）若未附带真实文件，**不会**产生后端 document；提交时请保证 `categoryFiles['fact_find']` 里有真实 PDF。

### 4.2 OCR 触发时机

`api.createSubmission` 在上传成功后会 **异步逐个** `POST .../ocr`（避免 429/打满线程）。  
详情页若打开过早，可能仍是 `processing` / 字段为空——需要 **轮询或刷新**（你们 application 页若已有 re-fetch，保持即可）。

---

## 5. API 契约（联调用）

Base：`http://localhost:5000/api/v1`  
鉴权：请求头 `Authorization: Bearer <token>`（见第 7 节 Demo 旁路说明）。

### 5.1 创建申请

`POST /applications`  
JSON 示例：

```json
{
  "customer_name": "John & Mary Citizen",
  "loan_type": "purchase",
  "source_channel": "frontend"
}
```

响应含：`application_id`、`submission_id`。

### 5.2 上传文档

`POST /submissions/{submission_id}/documents`  
`multipart/form-data`：

- `file`：PDF  
- `document_type`：`fact_find`

成功约 201，body 含 document `id`、`processing_status`（初始多为 `uploaded`）等。

### 5.3 触发提取

`POST /documents/{document_id}/ocr`  

成功 200 示例：

```json
{
  "job_id": "...",
  "document_id": "...",
  "status": "completed",
  "pages": 7,
  "fields": 264,
  "tables": 0,
  "cells": 0
}
```

失败示例（空白可填表）：

```json
{
  "error": {
    "code": "fact_find_blank_form",
    "message": "The fact find form contains no filled-in values. Please upload a completed copy."
  }
}
```

其它可能：`azure_rate_limited`、`azure_*`、`document_not_found` 等。

### 5.4 拉取已提取字段

`GET /documents/{document_id}/extracted-data`  

字段元素形状（与 payslip / DB `extracted_field` 对齐），核心列：

| 字段 | 含义 |
|------|------|
| `id` | extracted_field UUID（审核写回用） |
| `field_key` | 稳定键，如 `applicant_1_mobile` |
| `field_label` | 展示名 |
| `raw_value` | 原始 |
| `normalised_value` | 归一化后 |
| `data_type` | text / money / date / phone / email / enum / boolean / integer… |
| `section_name` | 如 `personal_details`、`employment`、`monthly_expenses` |
| `applicant_number` | 1 或 2（部分全局字段为 1） |
| `mapped_table` / `mapped_column` | 映射到业务表列（可选展示） |
| `review_status` | 初始 `pending` |
| `confidence` | 直读多为 `1.0`；OCR 可能为空 |
| `bounding_box` | 可选，8 个数的多边形 |

满表大约 **264** 条；部分填写的 sample 会更少。  
UI 建议按 `section_name` + `applicant_number` 分组，不要按 payslip 那种「十来个字段」硬编码。

---

## 6. 业务约定（审核 / 展示务必知道）

### 6.1「Same as applicant 1」

若勾选 Same as applicant 1，提取结果 **只存旗标**，例如：

- `applicant_2_current_address_same_as_applicant_1` → normalised `true`

**不会**把申请人 1 的地址复制到申请人 2 字段。  
展示时：见旗标为 true → 显示申请人 1 的（可能已人工改正的）地址。与客户 Mapping Matrix §6.1 一致。

### 6.2 归一化示例

- 日期：优先澳式，输出 ISO `YYYY-MM-DD`（如 `15/03/2020` → `2020-03-15`）  
- 手机：E.164，如 `0412 345 678` → `+61412345678`  
- 金额：字符串小数，如 `2500.00`  
- 枚举：如 marital `single`，ownership `applicant_1` / `both`  

### 6.3 如何区分直读 vs OCR（调试用）

查 Supabase `ocr_extraction_job`：

| provider | model_name | 含义 |
|----------|------------|------|
| `acroform_direct_read` | `pymupdf` | 电子表直读 |
| `azure_document_intelligence` | `prebuilt-layout`（或配置值） | OCR |

`raw_response_uri` 指向 Storage 里的原始 JSON。

---

## 7. 鉴权（重要）

当前仓库里的 `backend/app/auth.py` → `require_staff` 仍是 **Demo B 旁路**：

- **不校验**真实用户 JWT  
- 注入 `demo_user` / `demo_profile`  
- 用 `SUPABASE_SECRET_KEY`（若有）访问 DB（绕过 RLS）  

因此：

- 前端即使暂时不带登录 token，本地联调也可能「能通」（取决于你们 fetch 是否仍带 Header）。  
- `/api/v1/auth/me` 可能返回 `demo@smartfinn.com`，**不能**用来验证真实 staff。  
- **合 main / 上正式环境前**必须与 Jerry 对齐，恢复真实 JWT + `staff_profile` 校验。

真实 staff（已建）：邮箱 `z5560574@ad.unsw.edu.au`（密码问 Jiawen）——恢复真鉴权后用。

---

## 8. 测试用 PDF

| 文件 | 用途 |
|------|------|
| `backend/tests/fixtures/fact_find_filled.pdf` | 满表直读，期望 ~264 字段 |
| 仓库外 / 团队盘：`Client_form_2024_FILLED.pdf`、`Client_form 2024_sample_1.pdf` | 同左；sample_1 字段更少 |
| 压平/扫描版（无 AcroForm 控件） | 测 OCR 路径；会耗 Azure F0 配额，较慢 |

空白模板（有控件未填）→ 应看到 422，不要当成功用例。

---

## 9. 前端建议自测清单

1. Checkout `feature/fact-find-extraction`，前后端都起来。  
2. 新建申请 → Fact Find 区上传 **满表 PDF** → 再传至少一份其它材料（若校验要求）→ 提交。  
3. 打开申请详情，等 OCR 完成后刷新，确认 Fact Find 文档下字段数量很多（满表约 264）。  
4. 抽查：`cover_customer_name`、`applicant_1_mobile`、`expense_groceries_monthly_amount` 等。  
5. （可选）上传空白可填表 → 应失败并有明确错误提示（若前端有展示 `error.message`）。  
6. （可选）字段按 `section_name` 折叠展示，避免一页刷 264 行无结构。

---

## 10. 尚未完成 / 已知限制（交接边界）

| 项 | 状态 | 谁跟 |
|----|------|------|
| PR #13 merge 进 `main` | 未合，等 review | 全组 |
| 恢复真实 `require_staff` | Demo 旁路仍在 | 后端 + Jerry |
| 前端按 section 优化 Fact Find 审核 UI | 可选增强 | 前端 |
| 扫描件 Azure 真机联调 | 后端单测有；完整 UI 联调可选 | 后端协助 |
| Email 同步 Fact Find | 前端 stub | 前端 / 后置 |
| 把 `extracted_field` 展开写入 `applicant` 等业务表 | **不在本 PR**；当前停在 extracted_field + 审核 | 后置 |

---

## 11. 出问题怎么查

1. `curl localhost:5000/api/v1/health`  
2. 浏览器 Network：documents 上传的 `document_type` 是否为 **`fact_find`**（不要写成 `Fact Find` / `ffs`）。  
3. `POST .../ocr` 的 HTTP 状态与 JSON `error.code`。  
4. Supabase（需 Dashboard 权限，找 Huaiyu）：  
   - `ocr_extraction_job`（provider / status）  
   - `extracted_field`（按 `source_document_id` 或 `ocr_extraction_job_id` count）  
5. 后端终端日志。  
6. 联系 Jiawen；PR 评论也可以。

---

## 12. 联系与链接

- PR：https://github.com/unsw-cse-comp99-3900/capstone-project-26t2-9900-w19b-bread/pull/13  
- 分支：`feature/fact-find-extraction`  
- 进度备忘（Jiawen 本地）：`9900/FactFind_进度_待办.md`（未进 git）  
- Supabase 项目 ref：`eebqyropaqcdvepcjqxo`（Dashboard 账号找 Huaiyu）

---

## 13. 给前端的最短「怎么开始」

1. `git checkout feature/fact-find-extraction && git pull`  
2. 配好 `backend/.env`，起 `wsgi.py` + `npm run dev`  
3. 新建申请 → 上传 `fact_find_filled.pdf`（或团队满表 PDF）到 Fact Find 区 → 提交  
4. 详情页刷新看提取字段  
5. 有问题把 `document_id` / Network 报错发 Jiawen  

**可以开始联调；先不 merge #13 也可以，用功能分支即可。**
