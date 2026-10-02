from uuid import uuid4
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql
from security_master_schema import models as m
from tests.test_swap_creation_rules import terms

def test_definition_is_unique_and_has_version_fk():
    table=m.metadata.tables['secm.swap_definition_version']
    assert list(table.primary_key.columns.keys())==['instrument_definition_version_id']
    assert {fk.target_fullname for fk in table.foreign_keys}=={'secm.instrument_definition_version.instrument_definition_version_id'}
    ddl=str(CreateTable(table).compile(dialect=postgresql.dialect()))
    assert 'JSONB NOT NULL' in ddl

def test_migration_storage_round_trip():
    # An isolated PostgreSQL database, never the operating database.
    from tests.test_migrations import _recreate_test_database, _run_alembic, TEST_DATABASE_URL
    _recreate_test_database()
    result=_run_alembic('upgrade','head')
    assert result.returncode==0,result.stderr
    engine=create_engine(TEST_DATABASE_URL)
    from security_master_schema.demo_data import load_demo_data
    load_demo_data(engine)
    with engine.begin() as c:
        assert c.scalar(text('SELECT count(*) FROM secm.swap_definition_version'))==0
        # Use a real parent definition written by the demo seed migration.
        parent=c.scalar(text('SELECT instrument_definition_version_id FROM secm.instrument_definition_version LIMIT 1'))
        assert parent is not None
        value=terms()
        c.execute(m.swap_definition_version.insert().values(instrument_definition_version_id=parent,
            schema_version=1,economics_payload=value.model_dump(mode='json',by_alias=True)))
        stored=c.execute(m.swap_definition_version.select()).mappings().one()
        from apps.reference_api.swap_creation_contracts import GenericSwapTerms
        assert GenericSwapTerms.model_validate(stored['economics_payload']).contractual_notional==1000000
        for values in [dict(instrument_definition_version_id=parent,schema_version=1),
            dict(instrument_definition_version_id=uuid4(),schema_version=1)]:
            with pytest.raises(IntegrityError):
                with c.begin_nested():
                    c.execute(m.swap_definition_version.insert().values(**values,economics_payload=stored['economics_payload']))
