begin;

create extension if not exists pgcrypto with schema extensions;

create table public.crm_application (
  id uuid primary key default gen_random_uuid(),
  crm_application_id text,
  crm_client_id text,
  broker_branch_id text,
  broker_user_id text,
  loan_type text,
  application_status text,
  crm_created_at timestamptz,
  crm_updated_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table public.fact_find_submission (
  id uuid primary key default gen_random_uuid(),
  crm_application_id uuid references public.crm_application(id) on delete restrict,
  intake_source text,
  source_channel text,
  customer_name text,
  form_date date,
  crm_data_available boolean,
  submission_status text,
  extraction_status text,
  review_status text,
  crm_sync_status text,
  analyst_uploaded_by text,
  analyst_uploaded_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table public.crm_application_snapshot (
  id uuid primary key default gen_random_uuid(),
  fact_find_submission_id uuid not null references public.fact_find_submission(id) on delete cascade,
  crm_application_external_id text,
  snapshot_json jsonb,
  snapshot_taken_at timestamptz,
  source_system text
);

create table public.source_document (
  id uuid primary key default gen_random_uuid(),
  fact_find_submission_id uuid not null references public.fact_find_submission(id) on delete cascade,
  original_file_name text,
  file_type text,
  mime_type text,
  file_size_bytes bigint,
  file_hash_sha256 text,
  storage_uri text,
  document_type text,
  upload_source text,
  page_count integer,
  processing_status text,
  received_at timestamptz,
  created_at timestamptz default now()
);

create table public.document_page (
  id uuid primary key default gen_random_uuid(),
  source_document_id uuid not null references public.source_document(id) on delete cascade,
  page_number integer,
  page_label text,
  width numeric,
  height numeric,
  rendered_image_uri text,
  raw_text text,
  created_at timestamptz default now()
);

create table public.ocr_extraction_job (
  id uuid primary key default gen_random_uuid(),
  source_document_id uuid not null references public.source_document(id) on delete cascade,
  provider text,
  model_name text,
  job_status text,
  started_at timestamptz,
  completed_at timestamptz,
  error_message text,
  raw_response_uri text,
  created_at timestamptz default now()
);

create table public.extracted_field (
  id uuid primary key default gen_random_uuid(),
  ocr_extraction_job_id uuid not null references public.ocr_extraction_job(id) on delete cascade,
  source_document_id uuid not null references public.source_document(id) on delete cascade,
  document_page_id uuid references public.document_page(id) on delete set null,
  section_name text,
  applicant_number integer,
  field_key text,
  field_label text,
  raw_value text,
  normalised_value text,
  data_type text,
  confidence numeric,
  bounding_box jsonb,
  mapped_table text,
  mapped_column text,
  review_status text,
  created_at timestamptz default now()
);

create table public.extracted_table (
  id uuid primary key default gen_random_uuid(),
  ocr_extraction_job_id uuid not null references public.ocr_extraction_job(id) on delete cascade,
  source_document_id uuid not null references public.source_document(id) on delete cascade,
  document_page_id uuid references public.document_page(id) on delete set null,
  table_name text,
  section_name text,
  row_count integer,
  column_count integer,
  confidence numeric,
  bounding_box jsonb,
  created_at timestamptz default now()
);

create table public.extracted_table_cell (
  id uuid primary key default gen_random_uuid(),
  extracted_table_id uuid not null references public.extracted_table(id) on delete cascade,
  row_index integer,
  column_index integer,
  column_name text,
  raw_value text,
  normalised_value text,
  data_type text,
  confidence numeric,
  bounding_box jsonb,
  created_at timestamptz default now()
);

create table public.applicant (
  id uuid primary key default gen_random_uuid(),
  fact_find_submission_id uuid not null references public.fact_find_submission(id) on delete cascade,
  applicant_number integer,
  title text,
  full_name text,
  mobile text,
  email text,
  marital_status text,
  source_type text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table public.applicant_dependant (
  id uuid primary key default gen_random_uuid(),
  applicant_id uuid not null references public.applicant(id) on delete cascade,
  dependant_name text,
  dependant_age integer,
  created_at timestamptz default now()
);

create table public.applicant_address (
  id uuid primary key default gen_random_uuid(),
  applicant_id uuid not null references public.applicant(id) on delete cascade,
  address_type text,
  sequence_number integer,
  street text,
  suburb text,
  state text,
  postcode text,
  ownership_status text,
  from_date date,
  to_date date,
  same_as_applicant_1 boolean,
  created_at timestamptz default now()
);

create table public.applicant_employment (
  id uuid primary key default gen_random_uuid(),
  applicant_id uuid not null references public.applicant(id) on delete cascade,
  employment_type text,
  sequence_number integer,
  employer_name text,
  employment_basis text,
  position_title text,
  start_date date,
  end_date date,
  employer_address text,
  employer_phone text,
  created_at timestamptz default now()
);

create table public.loan_requirements (
  id uuid primary key default gen_random_uuid(),
  fact_find_submission_id uuid not null unique references public.fact_find_submission(id) on delete cascade,
  specific_goals_or_objectives text,
  preferred_repayment_frequency text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table public.repayment_account (
  id uuid primary key default gen_random_uuid(),
  fact_find_submission_id uuid not null unique references public.fact_find_submission(id) on delete cascade,
  account_name text,
  bsb text,
  account_number text,
  created_at timestamptz default now()
);

create table public.property_asset (
  id uuid primary key default gen_random_uuid(),
  fact_find_submission_id uuid not null references public.fact_find_submission(id) on delete cascade,
  sequence_number integer,
  property_address text,
  estimated_value numeric,
  loan_balance numeric,
  lender text,
  property_type text,
  ownership text,
  created_at timestamptz default now()
);

create table public.financial_asset (
  id uuid primary key default gen_random_uuid(),
  fact_find_submission_id uuid not null references public.fact_find_submission(id) on delete cascade,
  asset_category text,
  account_label text,
  asset_type text,
  provider text,
  value numeric,
  ownership text,
  created_at timestamptz default now()
);

create table public.vehicle_asset (
  id uuid primary key default gen_random_uuid(),
  fact_find_submission_id uuid not null references public.fact_find_submission(id) on delete cascade,
  vehicle_number integer,
  make_model text,
  value numeric,
  vehicle_year integer,
  ownership text,
  created_at timestamptz default now()
);

create table public.other_asset (
  id uuid primary key default gen_random_uuid(),
  fact_find_submission_id uuid not null references public.fact_find_submission(id) on delete cascade,
  applicant_number integer,
  asset_type text,
  value numeric,
  created_at timestamptz default now()
);

create table public.liability (
  id uuid primary key default gen_random_uuid(),
  fact_find_submission_id uuid not null references public.fact_find_submission(id) on delete cascade,
  liability_type text,
  sequence_number integer,
  balance numeric,
  credit_limit numeric,
  creditor text,
  repayment_amount numeric,
  ownership text,
  paying_out boolean,
  created_at timestamptz default now()
);

create table public.monthly_expense (
  id uuid primary key default gen_random_uuid(),
  fact_find_submission_id uuid not null references public.fact_find_submission(id) on delete cascade,
  expense_category text,
  expense_description text,
  monthly_amount numeric,
  created_at timestamptz default now()
);

create table public.customer_consent (
  id uuid primary key default gen_random_uuid(),
  fact_find_submission_id uuid not null unique references public.fact_find_submission(id) on delete cascade,
  consent_to_collect_use_disclose boolean,
  consent_to_credit_report_access boolean,
  declaration_completed boolean,
  declaration_timestamp timestamptz,
  applicant_1_signed boolean,
  applicant_2_signed boolean,
  signature_method text,
  created_at timestamptz default now()
);

create table public.field_review (
  id uuid primary key default gen_random_uuid(),
  extracted_field_id uuid not null references public.extracted_field(id) on delete cascade,
  reviewed_by text,
  review_status text,
  original_value text,
  corrected_value text,
  review_notes text,
  reviewed_at timestamptz
);

create table public.approved_fact_find_data (
  id uuid primary key default gen_random_uuid(),
  fact_find_submission_id uuid not null references public.fact_find_submission(id) on delete cascade,
  approved_data_json jsonb,
  approval_status text,
  approved_by text,
  approved_at timestamptz,
  notes text,
  created_at timestamptz default now()
);

create table public.crm_update_tracking (
  id uuid primary key default gen_random_uuid(),
  fact_find_submission_id uuid not null references public.fact_find_submission(id) on delete cascade,
  crm_application_id uuid not null references public.crm_application(id) on delete restrict,
  update_mode text,
  update_status text,
  updated_by text,
  updated_at timestamptz,
  update_notes text,
  created_at timestamptz default now()
);

create table public.audit_event (
  id uuid primary key default gen_random_uuid(),
  fact_find_submission_id uuid references public.fact_find_submission(id) on delete set null,
  crm_application_id uuid references public.crm_application(id) on delete set null,
  source_document_id uuid references public.source_document(id) on delete set null,
  event_type text,
  actor_type text,
  actor_id text,
  event_timestamp timestamptz,
  event_details jsonb,
  created_at timestamptz default now()
);

create table public.crm_field_mapping (
  id uuid primary key default gen_random_uuid(),
  internal_table text,
  internal_column text,
  crm_object text,
  crm_field_name text,
  data_type text,
  direction text,
  is_active boolean,
  created_at timestamptz default now()
);

create index fact_find_submission_crm_application_idx on public.fact_find_submission(crm_application_id);
create index crm_application_snapshot_submission_idx on public.crm_application_snapshot(fact_find_submission_id);
create index source_document_submission_idx on public.source_document(fact_find_submission_id);
create index document_page_document_idx on public.document_page(source_document_id);
create index ocr_extraction_job_document_idx on public.ocr_extraction_job(source_document_id);
create index extracted_field_job_idx on public.extracted_field(ocr_extraction_job_id);
create index extracted_field_document_idx on public.extracted_field(source_document_id);
create index extracted_field_page_idx on public.extracted_field(document_page_id);
create index extracted_table_job_idx on public.extracted_table(ocr_extraction_job_id);
create index extracted_table_document_idx on public.extracted_table(source_document_id);
create index extracted_table_page_idx on public.extracted_table(document_page_id);
create index extracted_table_cell_table_idx on public.extracted_table_cell(extracted_table_id);
create index applicant_submission_idx on public.applicant(fact_find_submission_id);
create index applicant_dependant_applicant_idx on public.applicant_dependant(applicant_id);
create index applicant_address_applicant_idx on public.applicant_address(applicant_id);
create index applicant_employment_applicant_idx on public.applicant_employment(applicant_id);
create index property_asset_submission_idx on public.property_asset(fact_find_submission_id);
create index financial_asset_submission_idx on public.financial_asset(fact_find_submission_id);
create index vehicle_asset_submission_idx on public.vehicle_asset(fact_find_submission_id);
create index other_asset_submission_idx on public.other_asset(fact_find_submission_id);
create index liability_submission_idx on public.liability(fact_find_submission_id);
create index monthly_expense_submission_idx on public.monthly_expense(fact_find_submission_id);
create index field_review_field_idx on public.field_review(extracted_field_id);
create index approved_fact_find_data_submission_idx on public.approved_fact_find_data(fact_find_submission_id);
create index crm_update_tracking_submission_idx on public.crm_update_tracking(fact_find_submission_id);
create index crm_update_tracking_application_idx on public.crm_update_tracking(crm_application_id);
create index audit_event_submission_idx on public.audit_event(fact_find_submission_id);
create index audit_event_application_idx on public.audit_event(crm_application_id);
create index audit_event_document_idx on public.audit_event(source_document_id);

alter table public.crm_application enable row level security;
alter table public.fact_find_submission enable row level security;
alter table public.crm_application_snapshot enable row level security;
alter table public.source_document enable row level security;
alter table public.document_page enable row level security;
alter table public.ocr_extraction_job enable row level security;
alter table public.extracted_field enable row level security;
alter table public.extracted_table enable row level security;
alter table public.extracted_table_cell enable row level security;
alter table public.applicant enable row level security;
alter table public.applicant_dependant enable row level security;
alter table public.applicant_address enable row level security;
alter table public.applicant_employment enable row level security;
alter table public.loan_requirements enable row level security;
alter table public.repayment_account enable row level security;
alter table public.property_asset enable row level security;
alter table public.financial_asset enable row level security;
alter table public.vehicle_asset enable row level security;
alter table public.other_asset enable row level security;
alter table public.liability enable row level security;
alter table public.monthly_expense enable row level security;
alter table public.customer_consent enable row level security;
alter table public.field_review enable row level security;
alter table public.approved_fact_find_data enable row level security;
alter table public.crm_update_tracking enable row level security;
alter table public.audit_event enable row level security;
alter table public.crm_field_mapping enable row level security;

commit;
