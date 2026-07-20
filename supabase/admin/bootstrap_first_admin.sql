-- ADMIN-ONLY ONE-TIME OPERATIONAL SCRIPT.
-- Run this once in the Supabase SQL Editor after creating the first Auth user.
-- Enter the email once in admin_email before running.

do $$
declare
  admin_email constant text := '';
  admin_user_id uuid;
begin
  if nullif(trim(admin_email), '') is null or position('@' in admin_email) = 0 then
    raise exception 'Enter the Auth user email in admin_email before running this script';
  end if;

  select id
  into admin_user_id
  from auth.users
  where lower(email) = lower(admin_email);

  if admin_user_id is null then
    raise exception 'No Supabase Auth user found for email %', admin_email;
  end if;

  insert into public.staff_profile (user_id, full_name, role, is_active)
  select
    id,
    coalesce(raw_user_meta_data ->> 'full_name', email),
    'admin'::public.staff_role,
    true
  from auth.users
  where id = admin_user_id
  on conflict (user_id) do update
  set role = 'admin'::public.staff_role,
      is_active = true,
      updated_at = now();
end;
$$;

select user_id, full_name, role, is_active, created_at
from public.staff_profile
where role = 'admin'::public.staff_role
order by created_at;
