# Workstream 3：数据建模与数据库设计

> **负责人：** Yang Shu（Shuyang）— Solution Architect  
> **依据：** 指导文件 §8、客户 scope Task i/ii、SmartFINN 技术栈（Self-hosted Supabase / PostgreSQL）  
> **状态：** MVP 初稿，待 Alan（字段定义）、Haomiao（OCR 映射）、Jiawen（验证规则）评审

---

## 1. 目标（Objective）

在后端实施开始之前完成数据库结构设计，确保：

- Task i（数据捕获）有表可写
- Task ii（验证与检查）有结果可存、差异可 flag
- Task iii（Dashboard）可按 `overall_confidence_pct` 排名

---

## 2. 交付物清单

| 交付物 | 文件位置 |
|--------|----------|
| 实体关系图（ERD） | `ERD.drawio` → 导出 `ERD.png` |
| 数据库模式文档 | 本文档 §4–§6 |
| 表关系说明 | 本文档 §3 |
| 每张表字段列表 | 本文档 §5 |
| 提取数据 JSON 样例 | `samples/sample-extracted-data-payslip.json` |
| 迁移计划 | 本文档 §7 + `migrations/001_initial_schema.sql` |
| 命名规范 | 本文档 §8 |

---

## 3. 表关系说明（Table Relationship Explanation）

### 3.1 指导文件要求的关系

| 关系 | 基数 | 实现方式 |
|------|------|----------|
| 一个客户 → 多个申请 | 1 : N | `applications.client_id` → `clients.id` |
| 一个申请 → 多个文档 | 1 : N | `documents.application_id` → `applications.id` |
| 一个文档 → 一条提取数据 | 1 : 1 | `extracted_data.document_id` UNIQUE |
| 一个文档 → 一条欺诈结果 | 1 : 1 | `fraud_results.document_id` UNIQUE |
| 一个申请 → 多条告警 | 1 : N | `alerts.application_id` → `applications.id` |
| 一条告警 → 多条状态历史 | 1 : N | `alert_status_history.alert_id` → `alerts.id` |

### 3.2 扩展关系（支撑 MVP 实现）

| 关系 | 说明 |
|------|------|
| `extracted_data` → `extracted_field_values` (1:N) | 指导文件要求「可搜索字段用列、灵活 OCR 用 JSON」；主记录 1:1 存 JSON，子表存可索引字段 |
| `validation_rules` → `verification_results` (1:N) | 规则执行后写入验证结果（Task ii） |
| `validation_rules` → `alerts` (1:N) | 验证失败可生成告警 |
| `documents` → `alerts` (1:N, optional) | 告警可关联到具体文档 |

### 3.3 范围外实体（OOS — 本迁移不建表）

| 实体 | 原因 |
|------|------|
| `users` | RBAC 不在 MVP（scope Task iv） |
| `roles` | 同上 |
| `reports` | 指导文件标 OOS |
| `audit_logs` | 指导文件标 OOS；后续 Phase 可加 append-only 表 |
| `notifications` | 指导文件标 OOS |

---

## 4. 实体总览与 Scope 映射

```
clients
  └── applications (loan_type, confidence, risk_score)
        ├── documents (pdf/jpeg/png/docx)
        │     ├── extracted_data (JSONB + 1:1)
        │     │     └── extracted_field_values (可搜索列)
        │     └── fraud_results (1:1)
        ├── verification_results (Task ii)
        └── alerts
              └── alert_status_history

validation_rules (规则配置，种子数据)
```

| 实体 | Task i | Task ii | Task iii |
|------|--------|---------|----------|
| clients | ✅ | | |
| applications | ✅ | ✅ | ✅ 排名 |
| documents | ✅ | | |
| extracted_data | ✅ | | |
| extracted_field_values | ✅ | ✅ 比对源 | |
| fraud_results | | ✅ | |
| validation_rules | | ✅ | |
| verification_results | | ✅ | |
| alerts | | ✅ | ✅ 展示 |
| alert_status_history | | ✅ | |

---

## 5. 字段列表（Field List per Table）

### 5.1 `clients` — 客户

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| full_name | VARCHAR(200) | NOT NULL | 全名 |
| date_of_birth | DATE | | 出生日期 |
| email_masked | VARCHAR(100) | | 脱敏邮箱 |
| phone_masked | VARCHAR(30) | | 脱敏电话 |
| address_line | VARCHAR(300) | | 地址 |
| state | VARCHAR(50) | | 州 |
| postcode | VARCHAR(10) | | 邮编 |
| created_at | TIMESTAMPTZ | NOT NULL | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL | 更新时间 |

### 5.2 `applications` — 贷款申请

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| client_id | UUID | FK → clients | 客户 |
| loan_type | loan_type ENUM | NOT NULL | 贷款类型 |
| loan_amount | NUMERIC(14,2) | | 贷款金额 |
| declared_annual_income | NUMERIC(14,2) | | 申报年收入 |
| property_address | VARCHAR(500) | | 房产地址 |
| status | application_status ENUM | NOT NULL | 申请状态 |
| overall_confidence_pct | NUMERIC(5,2) | 0–100 | **Task iii 排名字段** |
| risk_score | NUMERIC(5,2) | 0–100 | 风险分（Jiawen 规则计算） |
| risk_level | risk_level ENUM | | low / medium / high |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**loan_type 枚举值：** `home_loan` | `investment_loan` | `personal_loan` | `commercial_loan` | `refinance`

### 5.3 `documents` — 上传文档

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| application_id | UUID | FK → applications | |
| file_name | VARCHAR(255) | NOT NULL | 原始文件名 |
| file_type | file_type ENUM | NOT NULL | pdf / jpeg / png / docx |
| document_category | document_category ENUM | NOT NULL | payslip / bank_statement / id_document 等 |
| storage_path | VARCHAR(500) | NOT NULL | Supabase Storage 路径 |
| file_size_bytes | BIGINT | | 文件大小 |
| ocr_status | ocr_status ENUM | NOT NULL | pending → processing → completed / failed |
| is_mandatory | BOOLEAN | NOT NULL | 是否必填（Workstream 2 矩阵决定） |
| uploaded_at | TIMESTAMPTZ | NOT NULL | |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL | |

### 5.4 `extracted_data` — OCR 提取主记录（1:1 文档）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| document_id | UUID | FK UNIQUE → documents | 一对一 |
| raw_ocr_json | JSONB | | Azure OCR 原始响应 |
| normalized_fields | JSONB | | OpenAI 归一化后的结构化 JSON |
| avg_confidence_pct | NUMERIC(5,2) | 0–100 | 该文档平均置信度 |
| extraction_status | extraction_status ENUM | NOT NULL | pending / completed / partial / failed |
| extracted_at | TIMESTAMPTZ | | 提取完成时间 |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL | |

### 5.5 `extracted_field_values` — 可搜索字段行

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| extracted_data_id | UUID | FK → extracted_data | |
| field_name | VARCHAR(100) | NOT NULL | 归一化字段名，如 `employer_name` |
| field_value | TEXT | | 字段值 |
| confidence_pct | NUMERIC(5,2) | 0–100 | 单字段置信度 |
| source | field_source ENUM | NOT NULL | ocr / openai / manual |
| created_at | TIMESTAMPTZ | NOT NULL | |

### 5.6 `fraud_results` — 欺诈检测结果（1:1 文档）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| document_id | UUID | FK UNIQUE → documents | |
| fraud_status | fraud_status ENUM | NOT NULL | clean / suspicious / confirmed_fraud / inconclusive |
| severity | severity_level ENUM | NOT NULL | low / moderate / critical |
| reason | TEXT | | 原因说明 |
| confidence_pct | NUMERIC(5,2) | | 欺诈检测置信度 |
| recommendation | TEXT | | 如 "Manual review required" |
| raw_response | JSONB | | Fortiro / Mock API 原始响应 |
| checked_at | TIMESTAMPTZ | | |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL | |

### 5.7 `validation_rules` — 验证规则配置

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| rule_code | VARCHAR(50) | UNIQUE NOT NULL | 如 `NAME_MATCH` |
| rule_name | VARCHAR(200) | NOT NULL | |
| description | TEXT | | |
| severity | severity_level ENUM | NOT NULL | |
| loan_types | loan_type[] | | 适用贷款类型，NULL = 全部 |
| is_active | BOOLEAN | NOT NULL | |
| rule_config | JSONB | | 规则参数（阈值等） |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL | |

### 5.8 `verification_results` — 验证执行结果（Task ii）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| application_id | UUID | FK → applications | |
| validation_rule_id | UUID | FK → validation_rules | 可空 |
| check_type | check_type ENUM | NOT NULL | tool_api / abr / cross_document / mock |
| field_name | VARCHAR(100) | | 被验证字段 |
| expected_value | TEXT | | 期望值 |
| actual_value | TEXT | | 实际值 |
| passed | BOOLEAN | NOT NULL | 是否通过 |
| verified_at | TIMESTAMPTZ | NOT NULL | |
| created_at | TIMESTAMPTZ | NOT NULL | |

### 5.9 `alerts` — 告警

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| application_id | UUID | FK → applications | |
| document_id | UUID | FK → documents | 可空 |
| validation_rule_id | UUID | FK → validation_rules | 可空 |
| alert_type | alert_type ENUM | NOT NULL | name_mismatch / income_mismatch 等 |
| severity | severity_level ENUM | NOT NULL | |
| title | VARCHAR(200) | NOT NULL | |
| description | TEXT | | |
| field_name | VARCHAR(100) | | |
| status | alert_status ENUM | NOT NULL | open / in_review / resolved / escalated |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL | |

### 5.10 `alert_status_history` — 告警状态历史

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| alert_id | UUID | FK → alerts | |
| from_status | alert_status | | 变更前状态 |
| to_status | alert_status | NOT NULL | 变更后状态 |
| changed_by | VARCHAR(100) | NOT NULL | MVP 无 users 表，存操作者标识 |
| notes | TEXT | | 审查备注 |
| changed_at | TIMESTAMPTZ | NOT NULL | append-only，不更新 |

---

## 6. 数据库设计标准（落实指导文件 §8）

| 标准 | 实现 |
|------|------|
| 清晰表名 | 全小写、复数、下划线：`loan_applications` → 简化为 `applications` |
| 主键 / 外键 | 全部 UUID + 显式 FK 约束 |
| 时间戳 | 所有主表含 `created_at`、`updated_at` |
| 枚举状态 | PostgreSQL ENUM 类型 |
| 灵活 OCR 结果 | `extracted_data.raw_ocr_json`、`normalized_fields` JSONB |
| 可搜索字段 | `extracted_field_values` 独立列 + 索引 |
| 审计日志 append-only | `alert_status_history` 仅 INSERT；`audit_logs` 留 Phase 2 |
| 避免多余敏感数据 | `email_masked`、`phone_masked`；不存完整账号 |

### JSON 列 vs 普通列 — 决策

| 数据 | 存储方式 | 原因 |
|------|----------|------|
| Azure OCR 原始响应 | `raw_ocr_json` JSONB | 结构随模型变化，不需查询 |
| OpenAI 归一化输出 | `normalized_fields` JSONB | 灵活扩展字段 |
| 用于比对/搜索的字段 | `extracted_field_values` 列 | 支持索引、JOIN、Dashboard 聚合 |
| 欺诈 API 原始响应 | `fraud_results.raw_response` JSONB | 调试用 |
| 规则参数 | `validation_rules.rule_config` JSONB | 未来可配置化 |

---

## 7. 迁移计划（Migration Plan）

### 7.1 迁移文件

| 顺序 | 文件 | 内容 |
|------|------|------|
| 001 | `migrations/001_initial_schema.sql` | 枚举、10 张 MVP 表、索引、触发器、默认验证规则种子 |
| 002 | （Sprint 2 计划）`002_add_audit_logs.sql` | 若客户要求最小审计 |
| 003 | （Sprint 3 计划）`003_dashboard_views.sql` | Dashboard 聚合视图 |

### 7.2 执行方式

```bash
# 在 Supabase PostgreSQL 容器中执行
psql -U postgres -d smartfinn -f migrations/001_initial_schema.sql
```

### 7.3 回滚策略

- 开发环境：`DROP SCHEMA public CASCADE; CREATE SCHEMA public;` 后重新执行 001
- 生产/演示：每次迁移配 `down` 脚本（002 起补充）

### 7.4 与 Supabase 集成

- 表由自托管 Supabase PostgreSQL 承载
- 文件存 Supabase Storage，`documents.storage_path` 存 bucket 路径
- Node.js DAL 通过 `@supabase/supabase-js` 访问

---

## 8. 命名规范（Database Naming Convention）

| 类别 | 规范 | 示例 |
|------|------|------|
| 表名 | 小写复数、下划线 | `clients`, `extracted_field_values` |
| 主键 | 统一 `id`，UUID | `id UUID PRIMARY KEY` |
| 外键列 | `{单数表名}_id` | `client_id`, `application_id` |
| 枚举类型 | `{含义}_type` 或 `{含义}_status` | `loan_type`, `ocr_status` |
| 时间戳 | `created_at`, `updated_at` | 所有主实体表 |
| 布尔 | `is_` 前缀 | `is_mandatory`, `is_active` |
| 索引 | `idx_{表名}_{列名}` | `idx_applications_confidence` |
| 触发器 | `trg_{表名}_{动作}` | `trg_applications_updated_at` |
| 规则代码 | 大写蛇形 | `NAME_MATCH`, `ABR_ENTITY` |
| 字段名（OCR） | 小写蛇形、归一化 | `employer_name`, `gross_income` |

---

## 9. 样例提取 JSON

见 `samples/sample-extracted-data-payslip.json`。

写入流程：

1. n8n WF1 完成 OCR → 插入 `extracted_data`（`raw_ocr_json` + `normalized_fields`）
2. 遍历 `normalized_fields` → 批量插入 `extracted_field_values`
3. 计算 `avg_confidence_pct` → 回写 `extracted_data`
4. 聚合所有文档置信度 → 更新 `applications.overall_confidence_pct`

---

## 10. 待团队确认项

| 问题 | 负责人 | 状态 |
|------|--------|------|
| 贷款类型 × 必填文档 → `documents.is_mandatory` 逻辑 | Alan + Jiawen | 待 Workstream 2 矩阵 |
| OCR 字段名最终清单 → `extracted_field_values.field_name` | Haomiao | 待 OCR 映射文档 |
| 风险评分公式 → `applications.risk_score` 计算时机 | Jiawen | 待匹配规则文档 |
| API 用 `/applications` 还是 `/cases` | Huaiyu + Shuyang | 建议统一 `/applications` |
| `audit_logs` MVP 是否做最小版 | Alan + 客户 | 当前 OOS |

---

## 11. 评审与下一步

- [ ] Alan 确认 `applications` 业务字段完整
- [ ] Haomiao 确认 OCR JSON 结构与 `normalized_fields` 格式
- [ ] Huaiyu 确认 DAL / Repository 与表映射
- [ ] Jiawen 确认 `validation_rules` 种子规则覆盖匹配规则草案
- [ ] Jerry 确认 Dashboard 查询字段（`overall_confidence_pct`, `risk_level`, alerts count）

**导出 ERD：** 用 Draw.io 打开 `ERD.drawio` → Export PNG → 嵌入 Proposal / TSD。
