"""Database capability boundaries; application users are never schema owners."""
from sqlalchemy import text


def assert_runtime_role(c):
    unsafe=c.scalar(text("""
      SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls
      OR EXISTS(SELECT 1 FROM pg_database d WHERE d.datname=current_database()
                AND pg_has_role(current_user,d.datdba,'MEMBER'))
      OR EXISTS(SELECT 1 FROM pg_namespace n WHERE n.nspname NOT LIKE 'pg_%'
                AND n.nspname <> 'information_schema'
                AND (pg_has_role(current_user,n.nspowner,'MEMBER')
                     OR has_schema_privilege(current_user,n.oid,'CREATE')))
      OR EXISTS(SELECT 1 FROM pg_class t JOIN pg_namespace n ON n.oid=t.relnamespace
                WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname <> 'information_schema'
                AND pg_has_role(current_user,t.relowner,'MEMBER'))
      FROM pg_roles WHERE rolname=current_user
    """))
    if unsafe is not False:
        raise RuntimeError('The API requires a non-owner runtime database login without administrative or schema-creation privileges')


def grant_runtime_access(c, role):
    """Run as maintenance owner after migrations. No owner role membership."""
    quote=c.dialect.identifier_preparer.quote
    target=quote(role)
    owner=quote(c.scalar(text('SELECT current_user')))
    schemas=c.scalars(text("SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname <> 'information_schema' ORDER BY nspname")).all()
    for schema in schemas:
        name=quote(schema)
        c.exec_driver_sql(f'REVOKE CREATE ON SCHEMA {name} FROM PUBLIC')
        c.exec_driver_sql(f'GRANT USAGE ON SCHEMA {name} TO {target}')
        c.exec_driver_sql(f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {name} TO {target}')
        c.exec_driver_sql(f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {name} TO {target}')
        c.exec_driver_sql(f'ALTER DEFAULT PRIVILEGES FOR ROLE {owner} IN SCHEMA {name} GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {target}')
        c.exec_driver_sql(f'ALTER DEFAULT PRIVILEGES FOR ROLE {owner} IN SCHEMA {name} GRANT USAGE, SELECT ON SEQUENCES TO {target}')
    # Runtime audit access is append/read only, even before trigger enforcement.
    c.exec_driver_sql(f'REVOKE UPDATE, DELETE, TRUNCATE ON ten.access_audit_event FROM {target}')
    c.exec_driver_sql(f'REVOKE ALL ON public.alembic_version FROM {target}')
