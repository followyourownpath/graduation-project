-- Read-only, single-row verification for the SmartFinn schema.

with expected_tables(table_name) as (
  values
    ('crm_application'),
    ('fact_find_submission'),
    ('crm_application_snapshot'),
    ('source_document'),
    ('document_page'),
    ('ocr_extraction_job'),
    ('extracted_field'),
    ('extracted_table'),
    ('extracted_table_cell'),
    ('applicant'),
    ('applicant_dependant'),
    ('applicant_address'),
    ('applicant_employment'),
    ('loan_requirements'),
    ('repayment_account'),
    ('property_asset'),
    ('financial_asset'),
    ('vehicle_asset'),
    ('other_asset'),
    ('liability'),
    ('monthly_expense'),
    ('customer_consent'),
    ('field_review'),
    ('approved_fact_find_data'),
    ('crm_update_tracking'),
    ('audit_event'),
    ('crm_field_mapping')
),
table_status as (
  select
    count(*) filter (where t.table_name is not null) as tables_found,
    count(*) filter (where t.table_name is null) as tables_missing,
    coalesce(
      array_agg(e.table_name order by e.table_name)
        filter (where t.table_name is null),
      array[]::text[]
    ) as missing_table_names
  from expected_tables e
  left join information_schema.tables t
    on t.table_schema = 'public'
   and t.table_name = e.table_name
),
foreign_key_status as (
  select count(*) as foreign_key_count
  from information_schema.table_constraints tc
  join expected_tables e on e.table_name = tc.table_name
  where tc.constraint_schema = 'public'
    and tc.constraint_type = 'FOREIGN KEY'
),
rls_status as (
  select
    count(*) filter (where c.relrowsecurity) as rls_enabled,
    count(*) filter (where not c.relrowsecurity) as rls_disabled
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
  join expected_tables e on e.table_name = c.relname
  where n.nspname = 'public'
    and c.relkind = 'r'
)
select
  ts.tables_found,
  ts.tables_missing,
  fks.foreign_key_count,
  rs.rls_enabled,
  rs.rls_disabled,
  ts.missing_table_names
from table_status ts
cross join foreign_key_status fks
cross join rls_status rs;
