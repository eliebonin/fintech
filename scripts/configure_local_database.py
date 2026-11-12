"""Prepare/activate local database least privilege without replacing its volume.

First run --prepare, then `docker compose up -d`, migrate, and --apply.
On an existing volume supply its current maintenance connection through
MIGRATION_DATABASE_URL; --apply rotates that login explicitly. No secrets printed.
"""
import argparse
import os
from pathlib import Path
from secrets import token_urlsafe
import sys
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL,make_url
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.local_database_config import private_settings,private_write,migration_url
from security_master_schema.database_security import grant_runtime_access,assert_runtime_role

RUNTIME='platform_runtime'


def prepare(root=ROOT):
    secrets=Path(root)/'.local-secrets'
    for name in ['postgres-admin-password','postgres-runtime-password']:
        path=secrets/name
        if path.is_symlink() or not path.resolve().is_relative_to(Path(root).resolve()):
            raise ValueError('Private secrets must remain inside the selected project')
        if not path.exists():private_write(path,token_urlsafe(48)+'\n')
        value=path.read_text().strip()
        if len(value)<48 or any(c.isspace() for c in value):raise ValueError('Private database passwords must be random values of at least 48 characters')
    values=dotenv_values(Path(root)/'.env')
    # Keep names selected by the existing installation; never choose a new volume.
    user=values.get('POSTGRES_USER') or os.environ.get('POSTGRES_USER','platform')
    database=values.get('POSTGRES_DB') or os.environ.get('POSTGRES_DB','platform_secm')
    admin_path=Path(root)/'.env.migrations'
    if not admin_path.exists():
        password=(secrets/'postgres-admin-password').read_text().strip()
        admin=URL.create('postgresql+psycopg',username=user,password=password,host='127.0.0.1',port=15432,database=database)
        private_settings({'MIGRATION_DATABASE_URL':admin.render_as_string(hide_password=False)},admin_path)
    return user,database


def apply(root=ROOT):
    user,database=prepare(root)
    previous=make_url(migration_url(root))
    if previous.host not in {'localhost','127.0.0.1','::1'} or previous.port!=15432 or previous.database!=database or previous.username!=user:
        raise ValueError('Only the explicitly configured local maintenance login/database on port 15432 may be provisioned')
    admin_password=(Path(root)/'.local-secrets/postgres-admin-password').read_text().strip()
    runtime_password=(Path(root)/'.local-secrets/postgres-runtime-password').read_text().strip()
    engine=create_engine(previous,hide_parameters=True)
    try:
        with engine.begin() as c:
            # Catalogues must not contain executable privileged helpers available
            # to arbitrary callers; none are expected in this application.
            if c.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE p.prosecdef AND n.nspname NOT LIKE 'pg_%' AND n.nspname <> 'information_schema')")):
                raise RuntimeError('Review SECURITY DEFINER functions before granting runtime access')
            quote=c.dialect.identifier_preparer.quote
            if not c.scalar(text('SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=:role)'),{'role':RUNTIME}):
                c.exec_driver_sql(f'CREATE ROLE {quote(RUNTIME)} LOGIN')
            if c.scalar(text('SELECT EXISTS(SELECT 1 FROM pg_auth_members a JOIN pg_roles r ON r.oid=a.member WHERE r.rolname=:role)'),{'role':RUNTIME}):
                raise RuntimeError('Runtime login must have no inherited role memberships')
            pg=c.connection.driver_connection.pgconn
            verifier=pg.encrypt_password(runtime_password.encode(),RUNTIME.encode(),b'scram-sha-256').decode('ascii')
            # Only generated SCRAM verifiers enter DDL, never clear-text passwords.
            c.exec_driver_sql(f"ALTER ROLE {quote(RUNTIME)} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '{verifier}'")
            grant_runtime_access(c,RUNTIME)
            c.exec_driver_sql(f'GRANT CONNECT ON DATABASE {quote(database)} TO {quote(RUNTIME)}')
            admin_verifier=pg.encrypt_password(admin_password.encode(),user.encode(),b'scram-sha-256').decode('ascii')
            c.exec_driver_sql(f"ALTER ROLE {quote(user)} PASSWORD '{admin_verifier}'")
    finally:engine.dispose()
    # Match Compose's IPv4 loopback binding directly; avoid OS IPv6 retries.
    admin=previous.set(password=admin_password,host='127.0.0.1')
    runtime=previous.set(username=RUNTIME,password=runtime_password,host='127.0.0.1')
    private_settings({'MIGRATION_DATABASE_URL':admin.render_as_string(hide_password=False)},Path(root)/'.env.migrations')
    private_settings({'DATABASE_URL':runtime.render_as_string(hide_password=False)},Path(root)/'.env.local-access')
    # Connection verifies both the generated credential and the effective role.
    check=create_engine(runtime,hide_parameters=True)
    try:
        with check.connect() as c:assert_runtime_role(c)
    finally:check.dispose()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    try:
        if args.apply:apply()
        elif args.prepare:prepare()
        else:parser.error('Choose --prepare or --apply')
    except Exception as exc:
        print(f'Local database setup failed ({type(exc).__name__}); check local connectivity and private maintenance settings.',file=sys.stderr)
        raise SystemExit(1)
    print('Local database configuration completed; credentials were not printed.')
