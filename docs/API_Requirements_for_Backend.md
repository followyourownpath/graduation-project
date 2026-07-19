# [DEPRECATED] 前端到后端 API 需求接口文档 (API Requirements for Backend)

> [!CAUTION]
> **This document is deprecated.** It is based on an outdated database design.
> **Please refer to the new API contract: [API_Contract_v2_Demo_B.md](./API_Contract_v2_Demo_B.md)**
> Which aligns with the current Supabase schema and frontend implementation.

本文档根据当前已实现的前端页面逻辑，梳理了前端所需的各个接口以及涉及的请求 (Request) 与响应 (Response) 字段，供后端开发作为接口设计的参考。

---

## 1. 认证模块 (Authentication)

### 1.1. 用户登录 (`POST /api/auth/login`)
- **场景**: 对应前端 `/login` 页面提交表单。
- **Request (前端传给后端)**:
  - `email` (string): 邮箱或用户名
  - `password` (string): 密码
- **Response (后端返回给前端)**:
  - `token` (string): JWT 凭证
  - `user` (object):
    - `id` (string): 用户ID
    - `name` (string): 用户姓名 (用于 Dashboard 顶部展示)
    - `role` (string): 角色 (如 `Compliance Officer`, `Admin`)

---

## 2. 概览与列表模块 (Dashboard & Applications)

### 2.1. 获取大盘指标 (`GET /api/dashboard/metrics`)
- **场景**: 对应前端 `/dashboard` 顶部的四个统计卡片。
- **Request**: 无 (Header中带 JWT Token)
- **Response**:
  - `total_applications` (number): 总申请量
  - `pending_review` (number): 待处理数量
  - `high_risk_alerts` (number): 高危预警数量
  - `approved_today` (number): 今日已批准数量

### 2.2. 获取申请列表 (`GET /api/applications`)
- **场景**: 对应 `/dashboard` 的简易表格 和 `/applications` 的完整管理表格。
- **Request (Query Parameters)**:
  - `page` (number): 页码 (默认 1)
  - `limit` (number): 每页条数
  - `search` (string): 模糊搜索关键词 (按姓名或 ID)
  - `status` (string): 状态过滤 (如 `Pending`, `Approved`, `Rejected`)
  - `risk_level` (string): 风险级别过滤
- **Response**:
  - `total_count` (number): 满足条件的总条数
  - `data` (array of objects):
    - `id` (string): 案卷号 (如 `APP-2026-001`)
    - `applicant_name` (string): 申请人姓名
    - `loan_type` (string): 贷款类型 (如 `Purchase`, `Refinance`)
    - `date_submitted` (string): 提交日期 (YYYY-MM-DD)
    - `status` (string): 当前状态
    - `risk_score` (number): AI 风险评分 (0-100)
    - `risk_level` (string): 风险级别 (`High`, `Medium`, `Low`)

---

## 3. 文件上传模块 (Application Creation)

### 3.1. 创建新申请并上传文件 (`POST /api/applications`)
- **场景**: 对应前端 `/applications/new` 页面，一次性提交表单和多个文件。
- **Request (Multipart/form-data)**:
  - `applicant_name` (string): 申请人姓名
  - `loan_type` (string): 贷款类型
  - `files` (Array of Files): 业务员拖拽的多个文件实体 (PDF, JPG, PNG)
- **Response**:
  - `application_id` (string): 新生成的案卷号
  - `message` (string): "Upload successful, OCR processing started"

*(备注：由于 OCR 解析需要时间，后端此时应异步处理文件，前端只需拿到成功的返回即可跳转回列表。)*

---

## 4. 审查与详情模块 (Review & Action)

### 4.1. 获取单条申请详情与文件组 (`GET /api/applications/:id`)
- **场景**: 对应前端 `/application/[id]` 页面，获取该案卷的全局信息以及包含的子文件。
- **Response**:
  - `id` (string): 案卷号
  - `applicant_name` (string): 申请人
  - `status` (string): 整体状态
  - `overall_risk_score` (number): 综合评分
  - `documents` (array): 左侧 Tabs 需要的文件列表
    - `doc_id` (string): 文件 ID
    - `doc_type` (string): 文件分类 (如 `Payslip`, `Passport`)
    - `file_url` (string): 供前端 PDF 渲染器拉取的临时 URL

### 4.2. 获取单一文件的 OCR 提取数据 (`GET /api/documents/:doc_id/extracted-data`)
- **场景**: 前端在左侧点击不同文件 Tab 时，右侧表单需展示对应的提取数据。
- **Response**:
  - `data_fields` (array of objects):
    - `key` (string): 字段标识 (如 `net_pay`)
    - `label` (string): 前端展示用的字段名 (如 `Net Pay`)
    - `value` (string): OCR 识别出来的值
    - `confidence` (number): 置信度 (较低时前端可标红)

### 4.3. 获取该案卷的合规预警 (`GET /api/applications/:id/alerts`)
- **场景**: 对应前端右侧的 Compliance Alerts 红色/黄色面板。
- **Response**:
  - `alerts` (array of objects):
    - `alert_id` (string)
    - `severity` (string): 严重程度 (`High`, `Medium`)
    - `title` (string): 预警短标题 (如 `Income Discrepancy`)
    - `description` (string): 详细描述
    - `status` (string): 状态 (`Open`, `Resolved`)

### 4.4. 保存审查员对 OCR 数据的修改 (`PUT /api/documents/:doc_id/extracted-data`)
- **场景**: 审查员发现 OCR 提取有误，在输入框手动修改后点击 `Save Corrections`。
- **Request (JSON)**:
  - `corrected_fields`: 键值对对象 (如 `{ net_pay: "$7,200.00" }`)
- **Response**:
  - `message` (string): "Updated successfully"

### 4.5. 最终审批决断 (`POST /api/applications/:id/decision`)
- **场景**: 审查员点击右下角的 Approve 或 Reject 并确认。
- **Request (JSON)**:
  - `decision` (string): `Approve` 或 `Reject`
  - `reason` (string): 审查员填写的决断理由/备注
- **Response**:
  - `message` (string): "Decision recorded successfully"
