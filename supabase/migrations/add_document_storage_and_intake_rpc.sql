begin;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'source-documents',
  'source-documents',
  false,
  20971520,
  array['application/pdf', 'image/jpeg', 'image/png', 'image/tiff']
)
on conflict (id) do update
set public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

create policy source_documents_active_staff_insert
on storage.objects
for insert
to authenticated
with check (
  bucket_id = 'source-documents'
  and public.is_active_staff()
);

create policy source_documents_active_staff_select
on storage.objects
for select
to authenticated
using (
  bucket_id = 'source-documents'
  and public.is_active_staff()
);

create policy source_documents_owner_or_admin_delete
on storage.objects
for delete
to authenticated
using (
  bucket_id = 'source-documents'
  and public.is_active_staff()
  and (
    owner_id = (select auth.uid())::text
    or public.is_staff_admin()
  )
);

create or replace function public.create_application_intake(
  p_customer_name text,
  p_loan_type text,
  p_source_channel text default 'web',
  p_external_application_id text default null
)
returns table(application_id uuid, submission_id uuid)
language plpgsql
security invoker
set search_path = ''
as $$
declare
  new_application_id uuid;
  new_submission_id uuid;
begin
  if nullif(btrim(p_customer_name), '') is null then
    raise exception 'customer name is required' using errcode = '22023';
  end if;

  if nullif(btrim(p_loan_type), '') is null then
    raise exception 'loan type is required' using errcode = '22023';
  end if;

  insert into public.crm_application (
    crm_application_id,
    loan_type,
    application_status
  )
  values (
    nullif(btrim(p_external_application_id), ''),
    btrim(p_loan_type),
    'draft'
  )
  returning id into new_application_id;

  insert into public.fact_find_submission (
    crm_application_id,
    intake_source,
    source_channel,
    customer_name,
    crm_data_available,
    submission_status,
    extraction_status,
    review_status,
    crm_sync_status,
    analyst_uploaded_by,
    analyst_uploaded_at
  )
  values (
    new_application_id,
    'document_upload',
    coalesce(nullif(btrim(p_source_channel), ''), 'web'),
    btrim(p_customer_name),
    false,
    'draft',
    'pending',
    'pending',
    'not_started',
    (select auth.uid())::text,
    now()
  )
  returning id into new_submission_id;

  return query select new_application_id, new_submission_id;
end;
$$;

revoke all on function public.create_application_intake(text, text, text, text) from public;
grant execute on function public.create_application_intake(text, text, text, text) to authenticated;

commit;
