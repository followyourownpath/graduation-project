-- ADMIN-ONLY OPERATIONAL SCRIPT.
-- Add or update one internal SmartFinn staff member.
-- Prerequisite: the user must already exist in Authentication -> Users.
-- Edit only staff_email, assigned_role, and optionally display_name.

do $$
declare
  staff_email constant text := '';
  assigned_role constant public.staff_role := 'analyst';
  display_name constant text := '';
  staff_user_id uuid;
begin
  if nullif(trim(staff_email), '') is null or position('@' in staff_email) = 0 then
    raise exception 'Enter the existing Auth user email in staff_email';
  end if;

  select id
  into staff_user_id
  from auth.users
  where lower(email) = lower(staff_email);

  if staff_user_id is null then
    raise exception 'No Supabase Auth user found for email %', staff_email;
  end if;

  insert into public.staff_profile (
    user_id,
    full_name,
    role,
    is_active
  )
  select
    id,
    coalesce(
      nullif(trim(display_name), ''),
      nullif(raw_user_meta_data ->> 'full_name', ''),
      email
    ),
    assigned_role,
    true
  from auth.users
  where id = staff_user_id
  on conflict (user_id) do update
  set full_name = excluded.full_name,
      role = excluded.role,
      is_active = true,
      updated_at = now();
end;
$$;

-- The result lists all staff so the newly added email and role can be confirmed.
select
  sp.user_id,
  au.email,
  sp.full_name,
  sp.role,
  sp.is_active,
  sp.updated_at
from public.staff_profile sp
join auth.users au on au.id = sp.user_id
order by sp.updated_at desc;
