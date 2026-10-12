"""Trade catalogue validation and database invariants."""
from uuid import uuid4
import pytest
import os
from sqlalchemy import create_engine, insert, select, update
from sqlalchemy.exc import IntegrityError, DBAPIError
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS, load_demo_data

DATABASE_URL = os.environ["DATABASE_URL"]

def test_trade_registry_has_unique_assignment_and_tenant_keys():
    assert "trd.trade_property_definition" in m.metadata.tables
    assert "trd.trade_property_value" in m.metadata.tables
    assert "trd.trade_tag_assignment" in m.metadata.tables
    assert any(set(c.columns.keys()) == {"trade_id", "definition_id"} for c in m.trade_property_value.constraints if hasattr(c, "columns"))

@pytest.mark.parametrize("value,kind,choices,expected", [
    (False, "BOOLEAN", [], False), ("0", "DECIMAL", [], "0"),
    ("1.2300", "DECIMAL", [], "1.23"), ("2028-02-29", "DATE", [], "2028-02-29"),
    ("core", "CHOICE", ["core"], "core"), (" thesis ", "TEXT", [], "thesis"),
])
def test_typed_values_preserve_meaning(value, kind, choices, expected):
    from apps.reference_api.trade_properties import normalize_property_value
    assert normalize_property_value(value, kind, choices) == expected

@pytest.mark.parametrize("value,kind,choices", [("false", "BOOLEAN", []), (True, "DECIMAL", []), ("NaN", "DECIMAL", []), ("2026-02-30", "DATE", []), ("unknown", "CHOICE", ["core"]), ({}, "TEXT", [])])
def test_invalid_typed_values_are_rejected(value, kind, choices):
    from apps.reference_api.trade_properties import normalize_property_value
    with pytest.raises(ValueError): normalize_property_value(value, kind, choices)

@pytest.fixture(scope="module")
def engine():
    result = create_engine(DATABASE_URL)
    load_demo_data(result)
    yield result
    result.dispose()

def test_trade_property_assignments_are_unique_and_tenant_consistent(engine):
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            from apps.reference_api.contracts import TradeBookingRequest
            from apps.reference_api.repository import book_listed_cash_trade
            payload = TradeBookingRequest(listingId=DEMO_IDS["hsbc_xlon_listing_node"],strategyId=DEMO_IDS["strategy"],side="BUY",quantity="10",executionPrice="12.5",tradeDatetime="2026-09-30T10:00:00Z",settlementDate="2026-10-02")
            trade_id = book_listed_cash_trade(connection,DEMO_IDS["tenant"],DEMO_IDS["demo_user_account"],payload,str(uuid4()),"property-invariants").data.trade.trade_id
            definition_id = uuid4()
            connection.execute(insert(m.trade_property_definition).values(definition_id=definition_id, tenant_id=DEMO_IDS["tenant"], code=f"TEST_{uuid4().hex}", label="Test", value_type="BOOLEAN", created_by_user_account_id=DEMO_IDS["demo_user_account"]))
            values = dict(trade_id=trade_id, definition_id=definition_id, tenant_id=DEMO_IDS["tenant"], value=False)
            connection.execute(insert(m.trade_property_value).values(**values))
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(insert(m.trade_property_value).values(**values))
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(update(m.trade_property_value).where(m.trade_property_value.c.definition_id == definition_id).values(value=True))
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(insert(m.trade_tag_assignment).values(trade_id=trade_id, tag_id=uuid4(), tenant_id=uuid4()))
        finally: transaction.rollback()

def test_property_meaning_cannot_be_rewritten(engine):
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            definition_id = uuid4()
            connection.execute(insert(m.trade_property_definition).values(definition_id=definition_id, tenant_id=DEMO_IDS["tenant"], code=f"TEST_{uuid4().hex}", label="Test", value_type="BOOLEAN", created_by_user_account_id=DEMO_IDS["demo_user_account"]))
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(update(m.trade_property_definition).where(m.trade_property_definition.c.definition_id == definition_id).values(value_type="TEXT"))
            connection.execute(update(m.trade_property_definition).where(m.trade_property_definition.c.definition_id == definition_id).values(status="RETIRED", retired_by_user_account_id=DEMO_IDS["demo_user_account"], retired_at_utc=__import__("datetime").datetime.now(__import__("datetime").timezone.utc)))
        finally: transaction.rollback()

def test_provisioning_rejects_unauthorised_actor_and_overwrite(engine):
    from apps.reference_api.trade_properties import provision_trade_catalogue
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with pytest.raises((PermissionError, ValueError)):
                provision_trade_catalogue(connection, DEMO_IDS["tenant"], uuid4(), [], [])
            code = f"TEST_{uuid4().hex}"
            definition = dict(code=code, label="Test", valueType="BOOLEAN")
            provision_trade_catalogue(connection, DEMO_IDS["tenant"], DEMO_IDS["demo_user_account"], [definition], [])
            with pytest.raises(ValueError, match="overwritten"):
                provision_trade_catalogue(connection, DEMO_IDS["tenant"], DEMO_IDS["demo_user_account"], [{**definition, "valueType":"TEXT"}], [])
        finally: transaction.rollback()

def test_provisioning_rejects_unbookable_whitespace_choices(engine):
    from apps.reference_api.trade_properties import provision_trade_catalogue
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with pytest.raises(ValueError, match="choices"):
                provision_trade_catalogue(connection, DEMO_IDS["tenant"], DEMO_IDS["demo_user_account"], [dict(code=f"TEST_{uuid4().hex}",label="Choice",valueType="CHOICE",choices=[" core "])], [])
        finally: transaction.rollback()
