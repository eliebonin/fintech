"""Tenant custom-field management, with rollback-backed lifecycle checks."""
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS, load_demo_data
from security_master_schema.tenant_workspace import TenantActionForbidden
from apps.reference_api.trade_configuration import create_property, retire_property, replace_property, list_properties

@pytest.fixture(scope="module")
def engine():
    engine=create_engine("postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm")
    load_demo_data(engine)
    yield engine
    engine.dispose()

@pytest.fixture
def connection(engine):
    with engine.connect() as connection:
        transaction=connection.begin()
        try: yield connection
        finally: transaction.rollback()

def values(**extra):
    return dict(code=f"TEST_{uuid4().hex}",label="Desk classification",valueType="TEXT",required=False,choices=[],description="Trade context",**extra)

def test_create_replay_and_audited_retirement(connection):
    tenant,actor=DEMO_IDS["tenant"],DEMO_IDS["demo_user_account"]
    payload=values()
    first=create_property(connection,tenant,actor,payload)
    assert create_property(connection,tenant,actor,payload)["definitionId"]==first["definitionId"]
    retired=retire_property(connection,tenant,actor,first["definitionId"])
    assert retired["status"]=="RETIRED"
    assert retired["retiredByUserAccountId"]==actor
    assert retired["retiredAtUtc"] is not None
    assert retire_property(connection,tenant,actor,first["definitionId"])==retired
    assert first["definitionId"] in {p["definitionId"] for p in list_properties(connection,tenant,actor)}

def test_replace_preserves_old_meaning_and_replays(connection):
    tenant,actor=DEMO_IDS["tenant"],DEMO_IDS["demo_user_account"]
    first=create_property(connection,tenant,actor,values())
    payload=dict(code=first["code"],label="New label",valueType="BOOLEAN",required=False,choices=[],description=None)
    replacement=replace_property(connection,tenant,actor,first["definitionId"],payload)
    assert replacement["versionNo"]==2
    assert replacement["definitionId"]!=first["definitionId"]
    assert replace_property(connection,tenant,actor,first["definitionId"],payload)==replacement
    old=connection.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.definition_id==first["definitionId"])).mappings().one()
    assert old["label"]=="Desk classification" and old["value_type"]=="TEXT" and old["status"]=="RETIRED"

def test_invalid_replacement_does_not_retire_old(connection):
    tenant,actor=DEMO_IDS["tenant"],DEMO_IDS["demo_user_account"]
    first=create_property(connection,tenant,actor,values())
    with pytest.raises(ValueError), connection.begin_nested():
        replace_property(connection,tenant,actor,first["definitionId"],dict(code=first["code"],label="Bad",valueType="CHOICE",choices=[]))
    assert connection.scalar(select(m.trade_property_definition.c.status).where(m.trade_property_definition.c.definition_id==first["definitionId"]))=="ACTIVE"

def test_required_field_needs_explicit_impact_acknowledgement(connection):
    payload=values();payload["required"]=True
    with pytest.raises(ValueError,match="acknowledge"):
        create_property(connection,DEMO_IDS["tenant"],DEMO_IDS["demo_user_account"],payload)
    payload["acknowledgeRequiredImpact"]=True
    assert create_property(connection,DEMO_IDS["tenant"],DEMO_IDS["demo_user_account"],payload)["required"]

def test_nonadmin_and_cross_tenant_definition_denied(connection):
    actor=DEMO_IDS["demo_user_account"]
    first=create_property(connection,DEMO_IDS["tenant"],actor,values())
    with pytest.raises(TenantActionForbidden): list_properties(connection,DEMO_IDS["second_tenant"],actor)
    # Tenant checking precedes definition lookup; no private definition leaks.
    with pytest.raises(TenantActionForbidden): retire_property(connection,DEMO_IDS["second_tenant"],actor,first["definitionId"])
