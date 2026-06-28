# 表关系速查 — 主键 / 外键怎么连

> **Owner:** Yang Shu  
> **完整版:** `database-schema-cn.md` §3、§5 · 可视化: `ERD.drawio`  
> **建表脚本:** `migrations/001_initial_schema.sql`

---

## 一句话结构

```
clients ──→ applications ──→ documents ──→ extracted_data ──→ extracted_field_values
                              │                └── fraud_results
                              ├── verification_results ← validation_rules
                              └── alerts ──→ alert_status_history
```

所有主键统一叫 **`id`**（UUID）。外键命名 **`{父表单数}_id`**。

---

## 逐条连线（谁连谁）

| 从表（子） | 外键列 | → | 主表（父） | 主键 | 关系 |
|-----------|--------|---|-----------|------|------|
| `applications` | `client_id` | → | `clients` | `id` | 多对一：一个客户多个申请 |
| `documents` | `application_id` | → | `applications` | `id` | 多对一：一个申请多个文档 |
| `extracted_data` | `document_id` | → | `documents` | `id` | **一对一**（UNIQUE） |
| `extracted_field_values` | `extracted_data_id` | → | `extracted_data` | `id` | 多对一：一条提取记录多个字段 |
| `fraud_results` | `document_id` | → | `documents` | `id` | **一对一**（UNIQUE） |
| `verification_results` | `application_id` | → | `applications` | `id` | 多对一 |
| `verification_results` | `validation_rule_id` | → | `validation_rules` | `id` | 多对一（可空） |
| `alerts` | `application_id` | → | `applications` | `id` | 多对一 |
| `alerts` | `document_id` | → | `documents` | `id` | 多对一（可空） |
| `alerts` | `validation_rule_id` | → | `validation_rules` | `id` | 多对一（可空） |
| `alert_status_history` | `alert_id` | → | `alerts` | `id` | 多对一 |

---

## 按业务路径理解（SF-01 ~ SF-08）

### 创建申请（SF-01 / SF-02）

1. 先 **INSERT** `clients`，得到 `clients.id`
2. 再 **INSERT** `applications`，`client_id = clients.id`，`loan_type` 写入贷款类型

### 上传文档（SF-04 ~ SF-06）

3. **INSERT** `documents`，`application_id = applications.id`，`storage_path` 指向文件

### OCR 入库（SF-07 / SF-08）

4. **INSERT** `extracted_data`，`document_id = documents.id`（每个文档最多一条）
5. **INSERT** `extracted_field_values`，`extracted_data_id = extracted_data.id`（每个字段一行）
6. **UPDATE** `applications.overall_confidence_pct`（聚合后，供 Dashboard 排名）

---

## 常见查询路径

| 想查什么 | 怎么连 |
|----------|--------|
| 某申请下所有文档 | `documents` WHERE `application_id = ?` |
| 某文档的 OCR 结果 | `extracted_data` WHERE `document_id = ?` |
| 某文档每个字段及置信度 | `extracted_field_values` JOIN `extracted_data` ON `extracted_data_id` |
| 某客户全部申请 | `applications` WHERE `client_id = ?` |
| 申请 + 客户信息 | `applications` JOIN `clients` ON `client_id` |
| 某申请全部告警 | `alerts` WHERE `application_id = ?` |
| 告警变更历史 | `alert_status_history` WHERE `alert_id = ?` |

---

## 独立配置表（不挂申请树）

| 表 | 说明 |
|----|------|
| `validation_rules` | 验证规则模板（种子数据已写在 migration 001），被 `verification_results`、`alerts` 引用 |

---

## MVP 未建的表（OOS）

`users` · `roles` · `reports` · `audit_logs` · `notifications` — 无 FK 连线，迁移 001 不包含。

---

## 相关文件在哪

| 文件 | 内容 |
|------|------|
| **本文档** `table-relationships-cn.md` | 主外键速查（简短） |
| `database-schema-cn.md` §3 | 表关系说明（正式交付） |
| `database-schema-cn.md` §5 | 每张表全部字段 |
| `ERD.drawio` | Draw.io 关系图，导出 PNG 给 Proposal |
| `migrations/001_initial_schema.sql` | 实际 CREATE TABLE 与 FK 约束 |
