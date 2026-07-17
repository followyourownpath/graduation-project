-- Read-only verification for the internal staff access model.

select
  (
    select count(*)
    from pg_tables
    where schemaname = 'public'
  ) as public_tables,
  (
    select count(*)
    from pg_policies
    where schemaname = 'public'
  ) as policy_count,
  (
    select count(*)
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
      and c.relkind = 'r'
      and c.relrowsecurity
  ) as rls_enabled,
  (
    select count(*)
    from information_schema.table_privileges
    where grantee = 'anon'
      and table_schema = 'public'
  ) as anon_table_privileges,
  (
    select count(*)
    from public.staff_profile
    where role = 'admin'::public.staff_role
      and is_active
  ) as active_admins;
