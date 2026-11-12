from scripts.configure_local_database import prepare
from scripts.local_database_config import private_settings,migration_url
from dotenv import dotenv_values


def test_preparation_is_private_idempotent_and_preserves_installation_names(tmp_path):
    private_settings({'POSTGRES_USER':'custom_owner','POSTGRES_DB':'custom_db','POSTGRES_VOLUME_NAME':'existing_volume'},tmp_path/'.env')
    assert prepare(tmp_path)==('custom_owner','custom_db')
    secret=(tmp_path/'.local-secrets/postgres-admin-password').read_text()
    assert len(secret.strip())>=48
    prepare(tmp_path)
    assert secret==(tmp_path/'.local-secrets/postgres-admin-password').read_text()
    assert dotenv_values(tmp_path/'.env')['POSTGRES_VOLUME_NAME']=='existing_volume'
    assert 'custom_owner' in dotenv_values(tmp_path/'.env.migrations')['MIGRATION_DATABASE_URL']


def test_migrations_cannot_accidentally_select_the_test_administration_database(tmp_path,monkeypatch):
    monkeypatch.delenv('MIGRATION_DATABASE_URL',raising=False)
    private_settings({'MIGRATION_DATABASE_URL':'postgresql+psycopg://owner@localhost/app'},tmp_path/'.env.migrations')
    monkeypatch.setenv('TEST_DATABASE_ADMIN_URL','postgresql+psycopg://test@localhost/postgres')
    assert migration_url(tmp_path).endswith('/app')
    assert migration_url(tmp_path,test_admin=True).endswith('/postgres')


def test_preparation_uses_unreserved_loopback_port_without_changing_existing_identity(tmp_path):
    from sqlalchemy.engine import make_url
    private_settings({'POSTGRES_USER':'existing_owner','POSTGRES_DB':'existing_db','POSTGRES_VOLUME_NAME':'existing_volume'},tmp_path/'.env')
    prepare(tmp_path)
    url=make_url(dotenv_values(tmp_path/'.env.migrations')['MIGRATION_DATABASE_URL'])
    assert (url.host,url.port,url.database,url.username)==('127.0.0.1',15432,'existing_db','existing_owner')
    assert dotenv_values(tmp_path/'.env')['POSTGRES_VOLUME_NAME']=='existing_volume'
