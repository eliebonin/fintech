"""Neutral defaults do not override an installation's explicit connection."""
from apps.reference_api.config import Settings
from security_master_schema.demo_data import DEMO_IDS
from uuid import UUID


def test_default_deployment_uses_neutral_database_identity(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert Settings.from_environment().database_url == (
        "postgresql+psycopg://platform:platform_local_only@localhost:54329/platform_secm"
    )


def test_explicit_existing_installation_connection_is_preserved(monkeypatch):
    url = "postgresql+psycopg://operator:secret@localhost:54329/existing_workspace"
    monkeypatch.setenv("DATABASE_URL", url)
    assert Settings.from_environment().database_url == url


def test_demo_renaming_preserves_stable_organisation_identity():
    assert DEMO_IDS.get("platform_organisation") == UUID("00000000-0000-7000-8000-000000000002")
    assert DEMO_IDS.get("platform_entity") == UUID("00000000-0000-7000-8000-000000000001")


def test_operator_database_target_requires_its_own_explicit_setting(monkeypatch):
    from security_master_schema.database_config import local_workspace_database
    monkeypatch.delenv('LOCAL_WORKSPACE_DATABASE', raising=False)
    monkeypatch.setenv('DATABASE_URL', 'postgresql://operator:secret@localhost:54329/arbitrary_database')
    assert local_workspace_database() == 'platform_secm'
    monkeypatch.setenv('LOCAL_WORKSPACE_DATABASE', 'existing_workspace')
    assert local_workspace_database() == 'existing_workspace'
