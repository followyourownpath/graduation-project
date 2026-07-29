# Database Design — Workstream 3

> **Owner:** Yang Shu (Solution Architect)

## Files

| File | Description |
|------|-------------|
| `database-schema.md` | Full schema document |
| `table-relationships.md` | Concise PK/FK reference |
| `ERD.drawio` | Entity Relationship Diagram — open in draw.io, export PNG |
| `migrations/001_initial_schema.sql` | Initial PostgreSQL migration |
| `samples/sample-extracted-data-payslip.json` | Sample OCR output for payslip |

## Quick Start

1. Review `database-schema.md` with the team
2. Open `ERD.drawio` in https://app.diagrams.net → export `ERD.png`
3. Run migration against self-hosted Supabase PostgreSQL when backend is ready

## MVP Tables (10)

`clients` · `applications` · `documents` · `extracted_data` · `extracted_field_values` · `fraud_results` · `validation_rules` · `verification_results` · `alerts` · `alert_status_history`

## OOS (not in migration 001)

`users` · `roles` · `reports` · `audit_logs` · `notifications`
