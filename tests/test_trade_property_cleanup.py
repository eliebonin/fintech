"""Retire embedded choices without erasing historical trade evidence."""
from unittest.mock import MagicMock
import pytest
from apps.reference_api import trade_properties
from scripts.provision_trade_properties import provision_config

def test_provisioning_cannot_create_new_embedded_choices(monkeypatch):
    monkeypatch.setattr(trade_properties,"assert_trade_configurator",lambda *args:None)
    monkeypatch.setattr(trade_properties,"lock_trade_catalogue",lambda *args:None)
    connection=MagicMock()
    connection.scalar.return_value=0
    connection.execute.return_value.mappings.return_value.first.return_value=None
    with pytest.raises(ValueError,match="governed catalogue"):
        trade_properties.provision_trade_catalogue(connection,"tenant","actor",[dict(code="BUCKET",label="Bucket",valueType="CHOICE",choices=["CORE"])],[])


def test_demo_config_uses_a_governed_catalogue():
    import json
    from pathlib import Path
    config = json.loads((Path(__file__).resolve().parents[1]/"docs/examples/trade-properties-demo.json").read_text())
    field = next(p for p in config["properties"] if p["code"] == "BOOKING_BUCKET")
    assert field["valueType"] == "REFERENCE"
    source = next(c for c in config["catalogues"] if c["code"] == field["catalogueCode"])
    assert [r["label"] for r in source["records"]] == ["CORE", "TACTICAL", "HEDGE"]


def test_config_rejects_embedded_choices_before_any_writes():
    connection = MagicMock()
    with pytest.raises(ValueError, match="governed catalogue"):
        provision_config(connection, "tenant", "actor", {"properties": [{"valueType":"CHOICE"}]})
    connection.begin_nested.assert_not_called()


def test_migration_preserves_old_values_and_replay_and_blocks_new_choices():
    """Exercise populated upgrade in an isolated disposable database, not the app."""
    import os
    import subprocess
    import sys
    from pathlib import Path
    from uuid import uuid4
    from sqlalchemy import create_engine, insert, select, text
    from sqlalchemy.exc import IntegrityError
    from security_master_schema import models as m
    from security_master_schema.demo_data import DEMO_IDS, load_demo_data
    from apps.reference_api.contracts import TradeBookingRequest
    from apps.reference_api.repository import _trade_booking_fingerprint, _TRADE_BOOKING_ENDPOINT, book_listed_cash_trade

    base = os.environ.get("DATABASE_URL", os.environ["DATABASE_URL"]).rsplit("/",1)[0]
    name = "fortem_choice_cleanup_test_" + uuid4().hex
    admin = create_engine(base + "/postgres", isolation_level="AUTOCOMMIT")
    engine = create_engine(base + "/" + name)
    root = Path(__file__).resolve().parents[1]
    def migrate(*args):
        return subprocess.run([sys.executable,"-m","alembic",*args],cwd=root,env=os.environ|{"DATABASE_URL":base+"/"+name},capture_output=True,text=True)
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        result = migrate("upgrade", "20261001_52")
        assert result.returncode == 0, result.stderr
        load_demo_data(engine)
        tenant, actor = DEMO_IDS["tenant"], DEMO_IDS["demo_user_account"]
        identifier = uuid4()
        malformed = uuid4()
        payload = TradeBookingRequest(listingId=DEMO_IDS["hsbc_xlon_listing_node"],strategyId=DEMO_IDS["strategy"],side="BUY",quantity="10",executionPrice="12.5",tradeDatetime="2026-09-30T10:00:00Z",settlementDate="2026-10-02",properties=[{"definitionId":identifier,"value":"CORE"}])
        with engine.begin() as connection:
            connection.execute(insert(m.trade_property_definition).values(definition_id=identifier,tenant_id=tenant,code="BOOKING_BUCKET",label="Booking bucket",value_type="CHOICE",choices=["CORE","lower case","VALUE_002"],created_by_user_account_id=actor))
            # Simulate an already booked pre-migration execution and its durable key.
            # Construct the historical row using the pre-upgrade schema. The
            # current application read model legitimately requires later
            # columns (e.g. position_effect), so do not run it on revision 52.
            trade = uuid4()
            connection.execute(insert(m.trade).values(trade_id=trade,trade_subject_reference_node_id=payload.listing_id,reference_instrument_node_id=DEMO_IDS['hsbc_instrument_node'],strategy_id=payload.strategy_id,trade_type='INVESTMENT',quantity=payload.quantity,quantity_unit='SHARES',execution_price=payload.execution_price,price_basis='UNIT_PRICE',price_currency_id=DEMO_IDS['gbp_currency'],trade_datetime_utc=payload.trade_datetime,settlement_date=payload.settlement_date,booked_by_user_account_id=actor,created_by_user_account_id=actor,execution_channel='MANUAL_UI',lifecycle_status='BOOKED'))
            connection.execute(insert(m.trade_property_value).values(trade_id=trade,definition_id=identifier,tenant_id=tenant,value="CORE"))
            fingerprint = _trade_booking_fingerprint(payload,connection,tenant)
            connection.execute(insert(m.trade_booking_idempotency).values(tenant_id=tenant,endpoint=_TRADE_BOOKING_ENDPOINT,idempotency_key="legacy-key",request_fingerprint=fingerprint,trade_id=trade))
            # Deliberate name collision: migration must not adopt unrelated data.
            connection.execute(insert(m.reference_catalogue).values(tenant_id=tenant,code="BOOKING_BUCKET",label="Unrelated list",created_by_user_account_id=actor))
            connection.execute(insert(m.trade_property_definition).values(definition_id=malformed,tenant_id=DEMO_IDS["second_tenant"],code="MALFORMED",label="Bad legacy list",value_type="CHOICE",choices=[" bad "],created_by_user_account_id=actor))
        result = migrate("upgrade", "head")
        assert result.returncode != 0 and "distinct nonblank strings" in result.stderr
        with engine.begin() as connection:
            assert connection.scalar(select(m.trade_property_definition.c.status).where(m.trade_property_definition.c.definition_id==identifier)) == "ACTIVE"
            assert connection.scalar(text("SELECT count(*) FROM trd.trade_configuration_event WHERE action='LEGACY_CHOICES_MIGRATED'")) == 0
            connection.execute(text("UPDATE trd.trade_property_definition SET status='RETIRED',retired_by_user_account_id=:actor,retired_at_utc=CURRENT_TIMESTAMP WHERE definition_id=:identifier"),{"actor":actor,"identifier":malformed})
        result = migrate("upgrade", "head")
        assert result.returncode == 0, result.stderr
        with engine.begin() as connection:
            old = connection.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.definition_id==identifier)).mappings().one()
            assert old["status"] == "RETIRED" and old["value_type"] == "CHOICE"
            current = connection.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.code=="BOOKING_BUCKET",m.trade_property_definition.c.status=="ACTIVE")).mappings().one()
            assert current["version_no"] == 2 and current["value_type"] == "REFERENCE"
            records = connection.execute(select(m.reference_catalogue_record).where(m.reference_catalogue_record.c.catalogue_id==current["catalogue_id"])).mappings().all()
            assert {r["label"] for r in records} == {"CORE","lower case","VALUE_002"}
            assert len({r["code"] for r in records}) == 3
            assert connection.scalar(select(m.trade_property_value.c.value).where(m.trade_property_value.c.definition_id==identifier)) == "CORE"
            replay = book_listed_cash_trade(connection,tenant,actor,payload,"legacy-key","cleanup-test")
            assert replay.data.trade.trade_id == trade
            assert next(p.value for p in replay.data.properties if p.definition_id==identifier) == "CORE"
            event = connection.execute(select(m.trade_configuration_event).where(m.trade_configuration_event.c.action=="LEGACY_CHOICES_MIGRATED")).mappings().one()
            assert event["payload"]["oldDefinitionId"] == str(identifier)
            assert len(event["payload"]["mapping"]) == 3
            with pytest.raises(IntegrityError,match="governed catalogue"), connection.begin_nested():
                connection.execute(insert(m.trade_property_definition).values(tenant_id=tenant,code="FORBIDDEN",label="Forbidden",value_type="CHOICE",choices=["A"],created_by_user_account_id=actor))
        result = migrate("downgrade", "20261001_52")
        # A newer forward-only guard can stop the downgrade before the older
        # choice archival guard. Either must preserve all upgraded evidence.
        assert result.returncode != 0 and ("archival" in result.stderr or "Forward-only" in result.stderr)
        with engine.connect() as connection:
            assert connection.scalar(select(m.trade_property_value.c.value).where(m.trade_property_value.c.definition_id==identifier)) == 'CORE'
    finally:
        engine.dispose()
        # Exact generated test name; never target the application database.
        assert name.startswith("fortem_choice_cleanup_test_") and len(name.rsplit("_",1)[1]) == 32
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()
