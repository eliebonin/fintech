"""Full enrichment round trips and replay compatibility, with rollback fixtures."""
from datetime import datetime, timezone
from uuid import uuid4
import hashlib, json
import pytest
from sqlalchemy import create_engine, insert, select, update, func
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS, load_demo_data
from apps.reference_api.contracts import TradeBookingRequest
from apps.reference_api.repository import book_listed_cash_trade, get_booked_trade_detail, IdempotencyKeyConflict

@pytest.fixture(scope="module")
def engine():
    engine = create_engine("postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm")
    load_demo_data(engine)
    yield engine
    engine.dispose()

@pytest.fixture
def connection(engine):
    with engine.connect() as connection:
        transaction = connection.begin()
        try: yield connection
        finally: transaction.rollback()

def request(**extra):
    return TradeBookingRequest(listingId=DEMO_IDS["hsbc_xlon_listing_node"], strategyId=DEMO_IDS["strategy"], side="BUY", quantity="10", executionPrice="12.5", tradeDatetime="2026-09-30T10:00:00Z", settlementDate="2026-10-02", **extra)

def definition(connection, kind="BOOLEAN", required=False, choices=None):
    identifier = uuid4()
    connection.execute(insert(m.trade_property_definition).values(definition_id=identifier, tenant_id=DEMO_IDS["tenant"], code=f"TEST_{identifier.hex}", label="Test property", value_type=kind, required=required, choices=choices or [], created_by_user_account_id=DEMO_IDS["demo_user_account"]))
    return identifier

def book(connection, payload, key=None):
    return book_listed_cash_trade(connection, DEMO_IDS["tenant"], DEMO_IDS["demo_user_account"], payload, key or str(uuid4()), "enrichment-test")

def test_enriched_trade_round_trips_roles_properties_tags_and_references(connection):
    prop = definition(connection)
    decimal = definition(connection, "DECIMAL")
    tag = uuid4()
    connection.execute(insert(m.trade_tag).values(tag_id=tag, tenant_id=DEMO_IDS["tenant"], code=f"TEST_{tag.hex}", label="Test tag", created_by_user_account_id=DEMO_IDS["demo_user_account"]))
    payload = request(counterpartyOrganisationId=DEMO_IDS["bank_a_organisation"], executingBrokerOrganisationId=DEMO_IDS["bank_a_organisation"], tradePurpose="HEDGING", marketActivity="SECONDARY", properties=[{"definitionId":prop,"value":False},{"definitionId":decimal,"value":"0"}], tagIds=[tag], externalReferences=[{"referenceType":"BROKER_REFERENCE","referenceValue":"B-123","sourceSystemId":"Broker"}])
    detail = book(connection, payload).data
    assert {p.role for p in detail.parties} == {"COUNTERPARTY", "EXECUTING_BROKER"}
    assert {p.definition_id:p.value for p in detail.properties} == {prop:False, decimal:"0"}
    assert detail.tags[0].tag_id == tag
    assert detail.trade.trade_purpose == "HEDGING"
    assert detail.trade.market_activity == "SECONDARY"
    assert detail.external_references[0].reference_value == "B-123"

def test_required_property_rejection_creates_no_trade(connection):
    definition(connection, required=True)
    before = connection.scalar(select(func.count()).select_from(m.trade))
    with pytest.raises(ValueError, match="required"):
        book(connection, request())
    assert connection.scalar(select(func.count()).select_from(m.trade)) == before

def test_legacy_minimal_fingerprint_replays_unchanged(connection):
    payload = request()
    old_fields = {k:v for k,v in payload.model_dump(mode="json", by_alias=True).items() if k in {"listingId","strategyId","side","quantity","executionPrice","tradeDatetime","settlementDate","counterpartyOrganisationId","externalReference","comment"}}
    old_hash = hashlib.sha256(json.dumps(old_fields, sort_keys=True,separators=(",",":")).encode()).hexdigest()
    key = str(uuid4())
    first = book(connection, payload, key)
    connection.execute(update(m.trade_booking_idempotency).where(m.trade_booking_idempotency.c.idempotency_key == key).values(request_fingerprint=old_hash))
    assert book(connection, payload, key).data.trade.trade_id == first.data.trade.trade_id

def test_property_order_replays_but_changed_value_conflicts(connection):
    first_id, second_id = definition(connection), definition(connection)
    first = request(properties=[{"definitionId":first_id,"value":False},{"definitionId":second_id,"value":True}])
    reversed_request = request(properties=[{"definitionId":second_id,"value":True},{"definitionId":first_id,"value":False}])
    key = str(uuid4())
    original = book(connection, first, key)
    assert book(connection, reversed_request, key).data.trade.trade_id == original.data.trade.trade_id
    with pytest.raises(IdempotencyKeyConflict): book(connection, request(properties=[{"definitionId":first_id,"value":True},{"definitionId":second_id,"value":True}]), key)

def test_decimal_property_replay_uses_canonical_value_after_retirement(connection):
    prop = definition(connection, "DECIMAL")
    key = str(uuid4())
    original = book(connection, request(properties=[{"definitionId":prop,"value":"1.2300"}]), key)
    connection.execute(update(m.trade_property_definition).where(m.trade_property_definition.c.definition_id == prop).values(status="RETIRED", retired_by_user_account_id=DEMO_IDS["demo_user_account"], retired_at_utc=datetime.now(timezone.utc)))
    replay = book(connection, request(properties=[{"definitionId":prop,"value":"1.23"}]), key)
    assert replay.data.trade.trade_id == original.data.trade.trade_id
    assert replay.data.properties[0].value == "1.23"
    assert connection.scalar(select(m.trade_property_definition.c.status).where(m.trade_property_definition.c.definition_id == prop)) == "RETIRED"

def test_duplicate_namespaced_reference_is_field_error_without_partial_trade(connection):
    from apps.reference_api.trade_properties import TradeFieldError
    value = str(uuid4())
    payload = request(externalReferences=[{"referenceType":"BROKER_REFERENCE","referenceValue":value,"sourceSystemId":"test-broker"}])
    book(connection, payload)
    before = connection.scalar(select(func.count()).select_from(m.trade))
    with pytest.raises(TradeFieldError, match="already recorded"), connection.begin_nested():
        book(connection, payload)
    assert connection.scalar(select(func.count()).select_from(m.trade)) == before

def test_real_other_tenant_annotations_are_rejected(connection):
    from apps.reference_api.trade_properties import TradeFieldError
    prop, tag = uuid4(), uuid4()
    connection.execute(insert(m.trade_property_definition).values(definition_id=prop,tenant_id=DEMO_IDS["second_tenant"],code=f"TEST_{prop.hex}",label="Private",value_type="TEXT",created_by_user_account_id=DEMO_IDS["demo_user_account"]))
    connection.execute(insert(m.trade_tag).values(tag_id=tag,tenant_id=DEMO_IDS["second_tenant"],code=f"TEST_{tag.hex}",label="Private",created_by_user_account_id=DEMO_IDS["demo_user_account"]))
    for payload in (request(properties=[{"definitionId":prop,"value":"secret"}]),request(tagIds=[tag])):
        with pytest.raises(TradeFieldError): book(connection,payload)

@pytest.mark.parametrize("kind,value,choices", [("TEXT","note",[]),("DATE","2026-09-30",[]),("INTEGER","42",[])])
def test_enriched_sell_round_trips_remaining_types(connection,kind,value,choices):
    prop=definition(connection,kind,choices=choices)
    payload=request(properties=[{"definitionId":prop,"value":value}]).model_copy(update={"side":"SELL"})
    detail=book(connection,payload).data
    assert float(detail.trade.quantity) < 0
    assert next(p.value for p in detail.properties if p.definition_id==prop) == value

def test_trader_is_named_separately_from_booker_and_revalidated(connection):
    from datetime import date
    from apps.reference_api.trade_properties import list_trade_traders, TradeFieldError
    person, account, membership = uuid4(),uuid4(),uuid4()
    connection.execute(insert(m.person).values(person_id=person,display_name="Test responsible trader",status="ACTIVE"))
    connection.execute(insert(m.user_account).values(user_account_id=account,person_id=person,account_type="HUMAN",status="ACTIVE"))
    connection.execute(insert(m.tenant_user_account).values(tenant_user_account_id=membership,tenant_id=DEMO_IDS["tenant"],user_account_id=account,membership_role="OPERATIONS",status="ACTIVE",valid_from=date(2026,1,1)))
    assert list_trade_traders(connection,DEMO_IDS["tenant"],"Test responsible") == [{"personId":person,"displayName":"Test responsible trader"}]
    assert list_trade_traders(connection,DEMO_IDS["second_tenant"],"Test responsible") == []
    detail=book(connection,request(traderPersonId=person)).data
    assert detail.trader_name == "Test responsible trader"
    assert detail.trade.trader_person_id == person
    assert detail.trade.booked_by_user_account_id == DEMO_IDS["demo_user_account"]
    connection.execute(update(m.tenant_user_account).where(m.tenant_user_account.c.tenant_user_account_id==membership).values(status="REVOKED"))
    assert list_trade_traders(connection,DEMO_IDS["tenant"],"Test responsible") == []
    with pytest.raises(TradeFieldError,match="active person"): book(connection,request(traderPersonId=person))
