begin;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'ocr-responses',
  'ocr-responses',
  false,
  10485760,
  array['application/json']
)
on conflict (id) do update
set public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

create policy ocr_responses_active_staff_insert
on storage.objects for insert to authenticated
with check (bucket_id = 'ocr-responses' and public.is_active_staff());

create policy ocr_responses_active_staff_select
on storage.objects for select to authenticated
using (bucket_id = 'ocr-responses' and public.is_active_staff());

create policy ocr_responses_owner_or_admin_delete
on storage.objects for delete to authenticated
using (
  bucket_id = 'ocr-responses'
  and public.is_active_staff()
  and (owner_id = (select auth.uid())::text or public.is_staff_admin())
);

commit;
