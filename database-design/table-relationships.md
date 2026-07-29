# Table Relationships — Primary and Foreign Key Reference

> **Owner:** Yang Shu
> **Full specification:** `database-schema.md` sections 3 and 5 · **Diagram:** `ERD.drawio`
> **Migration:** `migrations/001_initial_schema.sql`

---

## Structure at a Glance

```
clients ──→ applications ──→ documents ──→ extracted_data ──→ extracted_field_values
                              │                └── fraud_results
                              ├── verification_results ← validation_rules
                              └── alerts ──→ alert_status_history
```

All primary keys are UUIDs named **`id`**. Foreign keys follow the
**`{singular_parent_table}_id`** convention.

---

## Relationships

| Child table | Foreign key | → | Parent table | Primary key | Cardinality |
|-------------|-------------|---|--------------|-------------|-------------|
| `applications` | `client_id` | → | `clients` | `id` | Many applications to one client |
| `documents` | `application_id` | → | `applications` | `id` | Many documents to one application |
| `extracted_data` | `document_id` | → | `documents` | `id` | **One-to-one** (`UNIQUE`) |
| `extracted_field_values` | `extracted_data_id` | → | `extracted_data` | `id` | Many fields to one extraction record |
| `fraud_results` | `document_id` | → | `documents` | `id` | **One-to-one** (`UNIQUE`) |
| `verification_results` | `application_id` | → | `applications` | `id` | Many-to-one |
| `verification_results` | `validation_rule_id` | → | `validation_rules` | `id` | Many-to-one, nullable |
| `alerts` | `application_id` | → | `applications` | `id` | Many-to-one |
| `alerts` | `document_id` | → | `documents` | `id` | Many-to-one, nullable |
| `alerts` | `validation_rule_id` | → | `validation_rules` | `id` | Many-to-one, nullable |
| `alert_status_history` | `alert_id` | → | `alerts` | `id` | Many-to-one |

---

## Business Flow (SF-01 to SF-08)

### Create an Application (SF-01 / SF-02)

1. **INSERT** a row into `clients` and obtain `clients.id`.
2. **INSERT** a row into `applications`, set `client_id = clients.id`, and record the loan type in `loan_type`.

### Upload Documents (SF-04 to SF-06)

3. **INSERT** each file into `documents`, set `application_id = applications.id`, and point `storage_path` to the stored file.

### Persist OCR Results (SF-07 / SF-08)

4. **INSERT** into `extracted_data` with `document_id = documents.id` (at most one row per document).
5. **INSERT** into `extracted_field_values` with `extracted_data_id = extracted_data.id` (one row per field).
6. **UPDATE** `applications.overall_confidence_pct` with the aggregate confidence used for dashboard ranking.

---

## Common Query Paths

| Query | Join or filter |
|-------|----------------|
| All documents for an application | `documents` WHERE `application_id = ?` |
| OCR result for a document | `extracted_data` WHERE `document_id = ?` |
| Extracted fields and confidence for a document | `extracted_field_values` JOIN `extracted_data` ON `extracted_data_id` |
| All applications for a client | `applications` WHERE `client_id = ?` |
| Application with client details | `applications` JOIN `clients` ON `client_id` |
| All alerts for an application | `alerts` WHERE `application_id = ?` |
| Alert status history | `alert_status_history` WHERE `alert_id = ?` |

---

## Standalone Configuration Table

| Table | Description |
|-------|-------------|
| `validation_rules` | Validation-rule templates seeded by migration 001 and referenced by `verification_results` and `alerts` |

---

## Tables Outside the MVP

`users` · `roles` · `reports` · `audit_logs` · `notifications` have no foreign-key relationships because migration 001 does not create them.

---

## Related Files

| File | Contents |
|------|----------|
| **This document:** `table-relationships.md` | Concise primary/foreign-key reference |
| `database-schema.md` section 3 | Formal table-relationship specification |
| `database-schema.md` section 5 | Complete field list for every table |
| `ERD.drawio` | Draw.io relationship diagram; export it as PNG for the proposal |
| `migrations/001_initial_schema.sql` | Authoritative `CREATE TABLE` statements and foreign-key constraints |
