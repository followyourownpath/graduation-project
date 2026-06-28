-- SmartFINN MVP — Initial Database Migration
-- Workstream 3: Data Modelling and Database Design
-- Author: Yang Shu (Solution Architect)
-- Database: PostgreSQL (Self-hosted Supabase)
-- Migration: 001_initial_schema.sql

-- ============================================================
-- EXTENSIONS
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- ENUMS
-- ============================================================
CREATE TYPE loan_type AS ENUM (
  'home_loan',
  'investment_loan',
  'personal_loan',
  'commercial_loan',
  'refinance'
);

CREATE TYPE application_status AS ENUM (
  'draft',
  'processing',
  'pending_review',
  'approved',
  'rejected',
  'escalated'
);

CREATE TYPE risk_level AS ENUM ('low', 'medium', 'high');

CREATE TYPE file_type AS ENUM ('pdf', 'jpeg', 'png', 'docx');

CREATE TYPE document_category AS ENUM (
  'payslip',
  'bank_statement',
  'id_document',
  'tax_return',
  'liability_statement',
  'rental_statement',
  'employment_contract',
  'purchase_contract',
  'other'
);

CREATE TYPE ocr_status AS ENUM ('pending', 'processing', 'completed', 'failed');

CREATE TYPE extraction_status AS ENUM ('pending', 'completed', 'partial', 'failed');

CREATE TYPE field_source AS ENUM ('ocr', 'openai', 'manual');

CREATE TYPE fraud_status AS ENUM ('clean', 'suspicious', 'confirmed_fraud', 'inconclusive');

CREATE TYPE severity_level AS ENUM ('low', 'moderate', 'critical');

CREATE TYPE check_type AS ENUM ('tool_api', 'abr', 'cross_document', 'mock');

CREATE TYPE alert_type AS ENUM (
  'name_mismatch',
  'income_mismatch',
  'missing_document',
  'fraud_detected',
  'low_confidence',
  'expired_id',
  'employer_mismatch',
  'other'
);

CREATE TYPE alert_status AS ENUM ('open', 'in_review', 'resolved', 'escalated');

-- ============================================================
-- TABLE: clients
-- ============================================================
CREATE TABLE clients (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name     VARCHAR(200) NOT NULL,
  date_of_birth DATE,
  email_masked  VARCHAR(100),
  phone_masked  VARCHAR(30),
  address_line  VARCHAR(300),
  state         VARCHAR(50),
  postcode      VARCHAR(10),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_clients_full_name ON clients (full_name);

-- ============================================================
-- TABLE: applications
-- ============================================================
CREATE TABLE applications (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id               UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
  loan_type               loan_type NOT NULL,
  loan_amount             NUMERIC(14, 2),
  declared_annual_income  NUMERIC(14, 2),
  property_address        VARCHAR(500),
  status                  application_status NOT NULL DEFAULT 'draft',
  overall_confidence_pct  NUMERIC(5, 2) CHECK (overall_confidence_pct BETWEEN 0 AND 100),
  risk_score              NUMERIC(5, 2) CHECK (risk_score BETWEEN 0 AND 100),
  risk_level              risk_level,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_applications_client_id ON applications (client_id);
CREATE INDEX idx_applications_status ON applications (status);
CREATE INDEX idx_applications_confidence ON applications (overall_confidence_pct ASC NULLS LAST);

-- ============================================================
-- TABLE: documents
-- ============================================================
CREATE TABLE documents (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id     UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  file_name          VARCHAR(255) NOT NULL,
  file_type          file_type NOT NULL,
  document_category  document_category NOT NULL DEFAULT 'other',
  storage_path       VARCHAR(500) NOT NULL,
  file_size_bytes    BIGINT,
  ocr_status         ocr_status NOT NULL DEFAULT 'pending',
  is_mandatory       BOOLEAN NOT NULL DEFAULT FALSE,
  uploaded_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_application_id ON documents (application_id);
CREATE INDEX idx_documents_category ON documents (document_category);
CREATE INDEX idx_documents_ocr_status ON documents (ocr_status);

-- ============================================================
-- TABLE: extracted_data (1:1 with documents per Workstream 3)
-- ============================================================
CREATE TABLE extracted_data (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id         UUID NOT NULL UNIQUE REFERENCES documents(id) ON DELETE CASCADE,
  raw_ocr_json        JSONB,
  normalized_fields   JSONB,
  avg_confidence_pct  NUMERIC(5, 2) CHECK (avg_confidence_pct BETWEEN 0 AND 100),
  extraction_status   extraction_status NOT NULL DEFAULT 'pending',
  extracted_at        TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_extracted_data_document_id ON extracted_data (document_id);
CREATE INDEX idx_extracted_data_normalized_gin ON extracted_data USING GIN (normalized_fields);

-- ============================================================
-- TABLE: extracted_field_values (searchable normal columns)
-- ============================================================
CREATE TABLE extracted_field_values (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  extracted_data_id  UUID NOT NULL REFERENCES extracted_data(id) ON DELETE CASCADE,
  field_name         VARCHAR(100) NOT NULL,
  field_value        TEXT,
  confidence_pct     NUMERIC(5, 2) CHECK (confidence_pct BETWEEN 0 AND 100),
  source             field_source NOT NULL DEFAULT 'ocr',
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_efv_extracted_data_id ON extracted_field_values (extracted_data_id);
CREATE INDEX idx_efv_field_name ON extracted_field_values (field_name);
CREATE INDEX idx_efv_field_value ON extracted_field_values (field_value);

-- ============================================================
-- TABLE: fraud_results (1:1 with documents)
-- ============================================================
CREATE TABLE fraud_results (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id      UUID NOT NULL UNIQUE REFERENCES documents(id) ON DELETE CASCADE,
  fraud_status     fraud_status NOT NULL DEFAULT 'inconclusive',
  severity         severity_level NOT NULL DEFAULT 'low',
  reason           TEXT,
  confidence_pct   NUMERIC(5, 2) CHECK (confidence_pct BETWEEN 0 AND 100),
  recommendation   TEXT,
  raw_response     JSONB,
  checked_at       TIMESTAMPTZ,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fraud_results_document_id ON fraud_results (document_id);
CREATE INDEX idx_fraud_results_status ON fraud_results (fraud_status);

-- ============================================================
-- TABLE: validation_rules
-- ============================================================
CREATE TABLE validation_rules (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_code    VARCHAR(50) NOT NULL UNIQUE,
  rule_name    VARCHAR(200) NOT NULL,
  description  TEXT,
  severity     severity_level NOT NULL DEFAULT 'moderate',
  loan_types   loan_type[],
  is_active    BOOLEAN NOT NULL DEFAULT TRUE,
  rule_config  JSONB,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TABLE: verification_results (Task ii)
-- ============================================================
CREATE TABLE verification_results (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id      UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  validation_rule_id  UUID REFERENCES validation_rules(id) ON DELETE SET NULL,
  check_type          check_type NOT NULL,
  field_name          VARCHAR(100),
  expected_value      TEXT,
  actual_value        TEXT,
  passed              BOOLEAN NOT NULL,
  verified_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_verification_application_id ON verification_results (application_id);
CREATE INDEX idx_verification_passed ON verification_results (passed);

-- ============================================================
-- TABLE: alerts
-- ============================================================
CREATE TABLE alerts (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id      UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  document_id         UUID REFERENCES documents(id) ON DELETE SET NULL,
  validation_rule_id  UUID REFERENCES validation_rules(id) ON DELETE SET NULL,
  alert_type          alert_type NOT NULL,
  severity            severity_level NOT NULL,
  title               VARCHAR(200) NOT NULL,
  description         TEXT,
  field_name          VARCHAR(100),
  status              alert_status NOT NULL DEFAULT 'open',
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alerts_application_id ON alerts (application_id);
CREATE INDEX idx_alerts_status ON alerts (status);
CREATE INDEX idx_alerts_severity ON alerts (severity);

-- ============================================================
-- TABLE: alert_status_history
-- ============================================================
CREATE TABLE alert_status_history (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_id     UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
  from_status  alert_status,
  to_status    alert_status NOT NULL,
  changed_by   VARCHAR(100) NOT NULL DEFAULT 'reviewer',
  notes        TEXT,
  changed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alert_history_alert_id ON alert_status_history (alert_id);

-- ============================================================
-- TRIGGER: auto-update updated_at
-- ============================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_clients_updated_at
  BEFORE UPDATE ON clients FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_applications_updated_at
  BEFORE UPDATE ON applications FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_documents_updated_at
  BEFORE UPDATE ON documents FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_extracted_data_updated_at
  BEFORE UPDATE ON extracted_data FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_fraud_results_updated_at
  BEFORE UPDATE ON fraud_results FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_validation_rules_updated_at
  BEFORE UPDATE ON validation_rules FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_alerts_updated_at
  BEFORE UPDATE ON alerts FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- SEED: default validation rules (Sprint 1)
-- ============================================================
INSERT INTO validation_rules (rule_code, rule_name, description, severity, loan_types) VALUES
  ('NAME_MATCH', 'Applicant Name Consistency', 'Name must match across ID, payslip, and bank statement', 'critical', NULL),
  ('INCOME_MATCH', 'Income Consistency', 'Payslip income must match salary credits in bank statement', 'critical', NULL),
  ('ID_NOT_EXPIRED', 'ID Expiry Check', 'Identification document must not be expired', 'critical', NULL),
  ('MANDATORY_DOCS', 'Mandatory Documents Present', 'All mandatory documents for loan type must be uploaded', 'critical', NULL),
  ('EMPLOYER_MATCH', 'Employer Name Match', 'Employer on payslip should match bank transaction description', 'moderate', NULL),
  ('OCR_CONFIDENCE', 'OCR Confidence Threshold', 'Field confidence below 80% requires manual review', 'moderate', NULL),
  ('ABR_ENTITY', 'ABR Business Check', 'Employer ABN/entity status validation via ABR API', 'moderate', NULL);
