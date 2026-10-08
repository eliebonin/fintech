"""Real API boundary: instrument-backed trades, not synthetic listings."""
import asyncio
from uuid import UUID, uuid4
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update, func, text
from apps.reference_api.main import create_app
from apps.reference_api.db import get_engine
from security_master_schema.demo_data import DEMO_IDS, load_demo_data
from security_master_schema import models as m

def request(method, path, payload=None, key=None, tenant="tenant"):
    async def run():
        async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
            return await client.request(method, path, json=payload, headers={"X-Tenant-Id":str(DEMO_IDS[tenant]), "X-User-Account-Id":str(DEMO_IDS["demo_user_account"]), "Idempotency-Key":key or str(uuid4())})
    return asyncio.run(run())

@pytest.fixture(scope="module")
def instrument():
    load_demo_data(get_engine())
    proposed = request("POST", "/v1/fx-forward-proposals", {"canonicalName":f"Booking EUR/USD {uuid4()}", "effectiveFrom":"2026-09-01", "baseCurrencyId":str(DEMO_IDS["eur_currency"]), "quoteCurrencyId":str(DEMO_IDS["usd_currency"]), "quoteConvention":"USD_PER_EUR", "agreedForwardRate":"1.10", "settlementType":"DELIVERABLE", "maturityDate":"2026-12-15", "submissionMode":"MANUAL"})
    assert proposed.status_code == 201, proposed.text
    approved = request("POST", f"/v1/reference-data-proposals/{proposed.json()['data']['proposalId']}/decision", {"decision":"APPROVED", "reason":"Verified terms for synthetic booking tests."})
    assert approved.status_code == 200, approved.text
    return approved.json()["data"]["referenceNodeId"]

def payload(instrument, **changes):
    view = request("GET", f"/v1/trades/fx-forward-instruments/{instrument}")
    assert view.status_code == 200, view.text
    return {"instrumentId":instrument, "strategyId":str(DEMO_IDS["strategy"]), "side":"BUY", "quantity":"1000000", "tradeDatetime":"2026-10-01T10:00:00Z", "counterpartyOrganisationId":str(DEMO_IDS["bank_a_organisation"]), "expectedTermsFingerprint":view.json()["data"]["termsFingerprint"]} | changes

@pytest.mark.parametrize("side,receive,pay", [("BUY","EUR","USD"),("SELL","USD","EUR")])
def test_books_one_forward_with_inherited_economics(instrument, side, receive, pay):
    response = request("POST", "/v1/trades/fx-forwards", payload(instrument, side=side))
    assert response.status_code == 201, response.text
    trade = response.json()["data"]["trade"]
    assert trade["listingId"] is None
    assert trade["instrumentId"] == instrument
    assert trade["quantityUnit"] == "CURRENCY_AMOUNT"
    assert trade["priceBasis"] == "RATE"
    assert trade["priceCurrency"] == "USD"
    assert trade["executionPrice"].rstrip("0").rstrip(".") == "1.1"
    assert trade["settlementDate"] == "2026-12-15"
    economics = trade["fxForwardEconomics"]
    assert economics["receiveCurrency"] == receive
    assert economics["payCurrency"] == pay
    assert economics["receiveAmount"] == ("1000000" if side == "BUY" else "1100000")
    assert economics["payAmount"] == ("1100000" if side == "BUY" else "1000000")

@pytest.mark.parametrize("field,value", [("executionPrice","1.20"),("settlementDate","2027-01-01"),("listingId",str(uuid4())),("marketActivity","SECONDARY"),("tradeDatetime","2026-10-01T10:00:00"),("quantity","0")])
def test_rejects_overrides_and_invalid_inputs(instrument, field, value):
    assert request("POST", "/v1/trades/fx-forwards", payload(instrument, **{field:value})).status_code == 422

def test_counterparty_is_required(instrument):
    data = payload(instrument)
    data.pop("counterpartyOrganisationId")
    assert request("POST", "/v1/trades/fx-forwards", data).status_code == 422


def test_historical_fx_definition_must_cover_execution(connection,instrument):
    from datetime import date
    from apps.reference_api.fx_forward_booking import load_fx_forward_booking_terms
    from security_master_schema.fx_forward_booking import FxForwardBookingError
    with pytest.raises(FxForwardBookingError):
        load_fx_forward_booking_terms(connection,DEMO_IDS['tenant'],UUID(instrument),as_of=date(2026,8,31))

def test_execution_after_settlement_rejected(instrument):
    response = request("POST", "/v1/trades/fx-forwards", payload(instrument, tradeDatetime="2026-12-16T10:00:00Z"))
    assert response.status_code == 422

def test_search_returns_visible_contract_without_listing(instrument):
    response = request("GET", "/v1/trades/fx-forward-instruments?q=Booking%20EUR%2FUSD")
    assert response.status_code == 200
    item = next(item for item in response.json()["data"] if item["instrumentId"] == instrument)
    assert item["bookingEligible"] is True
    assert item["settlementDate"] == "2026-12-15"

@pytest.fixture
def connection():
    with get_engine().connect() as c:
        tx=c.begin()
        try: yield c
        finally: tx.rollback()

def direct_payload(connection,instrument,**changes):
    from apps.reference_api.fx_forward_booking import get_fx_forward_booking_instrument
    from apps.reference_api.contracts import FxForwardBookingRequest
    view=get_fx_forward_booking_instrument(connection,DEMO_IDS["tenant"],UUID(instrument))
    return FxForwardBookingRequest.model_validate({"instrumentId":instrument,"strategyId":str(DEMO_IDS["strategy"]),"side":"BUY","quantity":"1000000","tradeDatetime":"2026-10-01T10:00:00Z","counterpartyOrganisationId":str(DEMO_IDS["bank_a_organisation"]),"expectedTermsFingerprint":view.terms_fingerprint}|changes)

def direct_book(connection,data,key=None):
    from apps.reference_api.fx_forward_booking import book_fx_forward_trade
    return book_fx_forward_trade(connection,DEMO_IDS["tenant"],DEMO_IDS["demo_user_account"],data,key or str(uuid4()),"fx-test")

@pytest.mark.parametrize("table,column,value",[
    (m.fx_forward_terms,"settlement_type","NDF"),(m.fx_forward_terms,"settlement_type","CASH"),
    (m.fx_forward_terms,"quote_convention","EUR_PER_USD"),(m.instrument_dates,"settlement_date",__import__("datetime").date(2026,12,16)),
    (m.instrument,"is_current",False),(m.financial_reference_node,"status","INACTIVE")])
def test_ineligible_terms_do_not_create_a_trade(connection,instrument,table,column,value):
    from security_master_schema.fx_forward_booking import FxForwardBookingError
    data=direct_payload(connection,instrument)
    id_column=table.c.reference_node_id if table is m.financial_reference_node else table.c.instrument_node_id
    connection.execute(update(table).where(id_column==UUID(instrument)).values({column:value}))
    before=connection.scalar(select(func.count()).select_from(m.trade))
    with pytest.raises(FxForwardBookingError):direct_book(connection,data)
    assert connection.scalar(select(func.count()).select_from(m.trade))==before

def test_stale_terms_and_changed_key_conflict_do_not_duplicate(connection,instrument):
    from apps.reference_api.repository import IdempotencyKeyConflict
    from security_master_schema.fx_forward_booking import FxForwardBookingError
    data=direct_payload(connection,instrument);key=str(uuid4())
    first=direct_book(connection,data,key)
    assert direct_book(connection,data,key).data.trade.trade_id==first.data.trade.trade_id
    with pytest.raises(IdempotencyKeyConflict):direct_book(connection,data.model_copy(update={"quantity":data.quantity+1}),key)
    before=connection.scalar(select(func.count()).select_from(m.trade))
    connection.execute(update(m.fx_forward_terms).where(m.fx_forward_terms.c.instrument_node_id==UUID(instrument)).values(agreed_forward_rate="1.25"))
    with pytest.raises(FxForwardBookingError,match="terms changed"):direct_book(connection,data)
    assert connection.scalar(select(func.count()).select_from(m.trade))==before

def test_replay_after_contract_and_counterparty_retirement(connection,instrument):
    data=direct_payload(connection,instrument);key=str(uuid4());first=direct_book(connection,data,key)
    connection.execute(update(m.instrument).where(m.instrument.c.instrument_node_id==UUID(instrument)).values(is_current=False))
    connection.execute(update(m.organisation).where(m.organisation.c.organisation_id==DEMO_IDS["bank_a_organisation"]).values(status="INACTIVE"))
    replay=direct_book(connection,data,key)
    assert replay.data.trade.trade_id==first.data.trade.trade_id
    assert replay.data.trade.fx_forward_economics==first.data.trade.fx_forward_economics

@pytest.mark.parametrize("field",["strategyId","counterpartyOrganisationId"])
def test_unknown_tenant_references_fail_atomically(connection,instrument,field):
    from apps.reference_api.repository import RepositoryNotFound
    from apps.reference_api.trade_properties import TradeFieldError
    data=direct_payload(connection,instrument,**{field:str(uuid4())})
    before=connection.scalar(select(func.count()).select_from(m.trade))
    with pytest.raises((RepositoryNotFound,TradeFieldError,ValueError)):direct_book(connection,data)
    assert connection.scalar(select(func.count()).select_from(m.trade))==before

def test_annotation_and_duplicate_reference_failures_rollback(connection,instrument):
    from apps.reference_api.trade_properties import TradeFieldError
    source=f"fx-{uuid4()}";data=direct_payload(connection,instrument,externalReferences=[{"referenceType":"SOURCE_TRADE_ID","referenceValue":source,"sourceSystemId":"FX_TEST"}])
    direct_book(connection,data)
    before=connection.scalar(select(func.count()).select_from(m.trade))
    with pytest.raises(TradeFieldError):direct_book(connection,data)
    with pytest.raises(TradeFieldError):direct_book(connection,direct_payload(connection,instrument,properties=[{"definitionId":str(uuid4()),"value":"Unknown"}]))
    assert connection.scalar(select(func.count()).select_from(m.trade))==before

def test_inactive_currency_and_absent_terms_are_rejected(connection,instrument):
    from security_master_schema.fx_forward_booking import FxForwardBookingError
    data=direct_payload(connection,instrument)
    connection.execute(update(m.currency).where(m.currency.c.currency_id==DEMO_IDS["eur_currency"]).values(status="INACTIVE"))
    with pytest.raises(FxForwardBookingError):direct_book(connection,data)
    connection.execute(update(m.currency).where(m.currency.c.currency_id==DEMO_IDS["eur_currency"]).values(status="ACTIVE"))
    connection.execute(m.fx_forward_terms.delete().where(m.fx_forward_terms.c.instrument_node_id==UUID(instrument)))
    with pytest.raises(FxForwardBookingError):direct_book(connection,data)

@pytest.mark.parametrize("column,value",[("status","DRAFT"),("status","RETIRED"),("is_current",False),("effective_from",__import__("datetime").date(2027,1,1)),("effective_to",__import__("datetime").date(2026,9,30))])
def test_only_current_approved_effective_definition_can_be_booked(connection,instrument,column,value):
    from apps.reference_api.fx_forward_booking import get_fx_forward_booking_instrument
    from security_master_schema.fx_forward_booking import FxForwardBookingError
    data=direct_payload(connection,instrument)
    # Approved versions are immutable. Build a separate fixture in the target state,
    # rather than bypassing production immutability triggers.
    clone=uuid4()
    for table,key in [(m.financial_reference_node,"reference_node_id"),(m.instrument,"instrument_node_id"),(m.fx_forward_terms,"instrument_node_id"),(m.instrument_dates,"instrument_node_id")]:
        row=dict(connection.execute(select(table).where(table.c[key]==UUID(instrument))).mappings().one())
        row[key]=clone
        for primary in table.primary_key.columns:
            if primary.name!=key:row[primary.name]=uuid4()
        if table is m.financial_reference_node:row.update(internal_code=f"FX_TEST_{clone.hex}",canonical_name=f"FX clone {clone}")
        connection.execute(table.insert().values(**row))
    version=dict(connection.execute(select(m.instrument_definition_version).where(m.instrument_definition_version.c.instrument_node_id==UUID(instrument))).mappings().one())
    version.update(instrument_definition_version_id=uuid4(),instrument_node_id=clone)
    version[column]=value
    connection.execute(m.instrument_definition_version.insert().values(**version))
    view=get_fx_forward_booking_instrument(connection,DEMO_IDS["tenant"],clone)
    assert not view.booking_eligible
    with pytest.raises(FxForwardBookingError):direct_book(connection,data.model_copy(update={"instrument_id":clone}))

def test_private_scope_cannot_be_read_or_booked_by_other_tenant(connection,instrument):
    from apps.reference_api.fx_forward_booking import get_fx_forward_booking_instrument,search_fx_forward_booking_instruments,load_fx_forward_booking_terms
    from apps.reference_api.repository import RepositoryNotFound
    connection.execute(update(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id==UUID(instrument)).values(scope_type="TENANT_PRIVATE",owner_tenant_id=DEMO_IDS["tenant"]))
    assert get_fx_forward_booking_instrument(connection,DEMO_IDS["tenant"],UUID(instrument)).booking_eligible
    with pytest.raises(RepositoryNotFound):load_fx_forward_booking_terms(connection,DEMO_IDS["second_tenant"],UUID(instrument),for_update=True)
    data,total=search_fx_forward_booking_instruments(connection,DEMO_IDS["second_tenant"],"Booking EUR/USD",100,0)
    assert not any(str(row.instrument_id)==instrument for row in data)

def test_concurrent_same_key_creates_exactly_one_trade(instrument):
    from concurrent.futures import ThreadPoolExecutor
    data=payload(instrument);key=str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda _:request("POST","/v1/trades/fx-forwards",data,key),range(2)))
    assert [r.status_code for r in responses]==[201,201]
    ids={r.json()["data"]["trade"]["tradeId"] for r in responses}
    assert len(ids)==1
    with get_engine().connect() as c:
        assert c.scalar(select(func.count()).select_from(m.trade_booking_idempotency).where(m.trade_booking_idempotency.c.idempotency_key==key))==1

def test_missing_or_inactive_actor_has_no_booking_access(instrument):
    data=payload(instrument)
    async def run():
        async with AsyncClient(transport=ASGITransport(app=create_app()),base_url="http://test") as client:
            return await client.post("/v1/trades/fx-forwards",json=data,headers={"X-Tenant-Id":str(DEMO_IDS["tenant"]),"X-User-Account-Id":str(uuid4()),"Idempotency-Key":str(uuid4())})
    assert asyncio.run(run()).status_code==403

def test_current_draft_does_not_shadow_or_duplicate_approved_definition(connection,instrument):
    from apps.reference_api.fx_forward_booking import get_fx_forward_booking_instrument,search_fx_forward_booking_instruments
    version=dict(connection.execute(select(m.instrument_definition_version).where(m.instrument_definition_version.c.instrument_node_id==UUID(instrument))).mappings().one())
    version.update(instrument_definition_version_id=uuid4(),sequence_no=version["sequence_no"]+1,status="DRAFT",is_current=True)
    connection.execute(m.instrument_definition_version.insert().values(**version))
    view=get_fx_forward_booking_instrument(connection,DEMO_IDS["tenant"],UUID(instrument))
    assert view.booking_eligible
    rows,total=search_fx_forward_booking_instruments(connection,DEMO_IDS["tenant"],"Booking EUR/USD",100,0)
    assert sum(str(row.instrument_id)==instrument for row in rows)==1
    assert direct_book(connection,direct_payload(connection,instrument)).data.trade.instrument_id==UUID(instrument)

def test_active_member_without_trade_write_cannot_book(instrument):
    data=payload(instrument)
    clause=(m.tenant_user_account.c.tenant_id==DEMO_IDS["tenant"]) & (m.tenant_user_account.c.user_account_id==DEMO_IDS["demo_user_account"])
    with get_engine().begin() as c:
        original=c.scalar(select(m.tenant_user_account.c.membership_role).where(clause))
        before=c.scalar(select(func.count()).select_from(m.trade))
        c.execute(update(m.tenant_user_account).where(clause).values(membership_role="VIEWER"))
    try:
        response=request("POST","/v1/trades/fx-forwards",data)
        assert response.status_code==403,response.text
        with get_engine().connect() as c:assert c.scalar(select(func.count()).select_from(m.trade))==before
    finally:
        with get_engine().begin() as c:c.execute(update(m.tenant_user_account).where(clause).values(membership_role=original))


@pytest.mark.parametrize("scope_type", ["TENANT_PRIVATE", "SHARED_CANONICAL"])
def test_inactive_scope_is_hidden_and_stale_ticket_cannot_book(connection, instrument, scope_type):
    from apps.reference_api.fx_forward_booking import get_fx_forward_booking_instrument, search_fx_forward_booking_instruments
    from apps.reference_api.repository import RepositoryNotFound
    data = direct_payload(connection, instrument)
    connection.execute(update(m.reference_node_scope).where(
        m.reference_node_scope.c.reference_node_id == UUID(instrument)).values(
            scope_type=scope_type, owner_tenant_id=DEMO_IDS["tenant"] if scope_type == "TENANT_PRIVATE" else None,
            status="INACTIVE"))
    before = connection.scalar(select(func.count()).select_from(m.trade))
    with pytest.raises(RepositoryNotFound):
        get_fx_forward_booking_instrument(connection, DEMO_IDS["tenant"], UUID(instrument))
    rows, _ = search_fx_forward_booking_instruments(connection, DEMO_IDS["tenant"], "Booking EUR/USD", 100, 0)
    assert not any(str(row.instrument_id) == instrument for row in rows)
    with pytest.raises(RepositoryNotFound):
        direct_book(connection, data)
    assert connection.scalar(select(func.count()).select_from(m.trade)) == before


def test_inactive_scope_preserves_existing_trade_detail_history_and_replay(connection, instrument):
    from apps.reference_api.repository import get_booked_trade_detail, list_booked_trades
    data = direct_payload(connection, instrument)
    key = str(uuid4())
    first = direct_book(connection, data, key)
    connection.execute(update(m.reference_node_scope).where(
        m.reference_node_scope.c.reference_node_id == UUID(instrument)).values(status="INACTIVE"))
    detail = get_booked_trade_detail(connection, DEMO_IDS["tenant"], first.data.trade.trade_id, "v1", "scope-test")
    assert detail.data.trade.fx_forward_economics == first.data.trade.fx_forward_economics
    history = list_booked_trades(connection, DEMO_IDS["tenant"], None, None, None, 100, 0, "v1", "scope-test", trade_id=first.data.trade.trade_id)
    assert any(trade.trade_id == first.data.trade.trade_id for trade in history.data)
    assert direct_book(connection, data, key).data.trade.trade_id == first.data.trade.trade_id


def test_inactive_scope_is_hidden_from_current_reference_catalogue(connection, instrument):
    from apps.reference_api.repository import get_instrument, _visible_reference_node, RepositoryNotFound
    assert get_instrument(connection, DEMO_IDS["tenant"], UUID(instrument)) is not None
    connection.execute(update(m.reference_node_scope).where(
        m.reference_node_scope.c.reference_node_id == UUID(instrument)).values(status="INACTIVE"))
    assert get_instrument(connection, DEMO_IDS["tenant"], UUID(instrument)) is None
    with pytest.raises(RepositoryNotFound):
        _visible_reference_node(connection, DEMO_IDS["tenant"], UUID(instrument))


def test_booking_terms_lock_scope_against_concurrent_revocation(connection, instrument):
    from sqlalchemy.exc import OperationalError
    from apps.reference_api.fx_forward_booking import load_fx_forward_booking_terms
    load_fx_forward_booking_terms(connection, DEMO_IDS["tenant"], UUID(instrument), for_update=True)
    with get_engine().begin() as other:
        other.execute(text("SET LOCAL lock_timeout = '200ms'"))
        with pytest.raises(OperationalError) as error:
            other.execute(update(m.reference_node_scope).where(
                m.reference_node_scope.c.reference_node_id == UUID(instrument)).values(status="INACTIVE"))
        assert error.value.orig.sqlstate == "55P03"


def test_legacy_unscoped_forward_remains_bookable(connection, instrument):
    connection.execute(m.reference_node_scope.delete().where(
        m.reference_node_scope.c.reference_node_id == UUID(instrument)))
    assert direct_book(connection, direct_payload(connection, instrument)).data.trade.instrument_id == UUID(instrument)


def test_http_refuses_inactive_scope_without_writing_trade(connection, instrument):
    data = direct_payload(connection, instrument)
    connection.execute(update(m.reference_node_scope).where(
        m.reference_node_scope.c.reference_node_id == UUID(instrument)).values(status="INACTIVE"))
    before = connection.scalar(select(func.count()).select_from(m.trade))
    app = create_app()
    # Cash and included FX routes share this dependency; included routers may be
    # expanded lazily by FastAPI, so locate it on the directly registered route.
    route = next(route for route in app.routes if getattr(route, "path", None) == "/v1/trades" and "POST" in getattr(route, "methods", set()))
    dependency = next(item.call for item in route.dependant.dependencies if item.call.__name__ == "connection_dependency")
    def injected():
        yield connection
    app.dependency_overrides[dependency] = injected
    async def run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.post("/v1/trades/fx-forwards", json=data.model_dump(mode="json", by_alias=True), headers={
                "X-Tenant-Id": str(DEMO_IDS["tenant"]), "X-User-Account-Id": str(DEMO_IDS["demo_user_account"]),
                "Idempotency-Key": str(uuid4())})
    response = asyncio.run(run())
    assert response.status_code == 404, response.text
    assert connection.scalar(select(func.count()).select_from(m.trade)) == before


def test_revocation_while_waiting_for_scope_lock_is_rechecked(instrument):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from time import monotonic, sleep
    from apps.reference_api.fx_forward_booking import load_fx_forward_booking_terms
    from apps.reference_api.repository import RepositoryNotFound
    ready = Event()
    worker_pid = []
    def load():
        with get_engine().begin() as worker:
            worker_pid.append(worker.scalar(text("SELECT pg_backend_pid()")))
            ready.set()
            with pytest.raises(RepositoryNotFound):
                load_fx_forward_booking_terms(worker, DEMO_IDS["tenant"], UUID(instrument), for_update=True)
    with get_engine().connect() as revoker, ThreadPoolExecutor(max_workers=1) as pool:
        transaction = revoker.begin()
        try:
            original = revoker.scalar(select(m.reference_node_scope.c.status).where(
                m.reference_node_scope.c.reference_node_id == UUID(instrument)))
            revoker.execute(update(m.reference_node_scope).where(
                m.reference_node_scope.c.reference_node_id == UUID(instrument)).values(status="INACTIVE"))
            future = pool.submit(load)
            assert ready.wait(5), "Booking worker did not start"
            deadline = monotonic() + 5
            with get_engine().connect() as observer:
                while monotonic() < deadline:
                    if observer.scalar(text("SELECT cardinality(pg_blocking_pids(:pid))"), {"pid": worker_pid[0]}):
                        break
                    sleep(0.01)
                else:
                    pytest.fail("Booking did not wait for the scope revocation lock")
            transaction.commit()
        finally:
            if transaction.is_active:
                transaction.rollback()
            # Release the lock before joining, including on diagnostic failures.
            if ready.is_set():
                try:
                    future.result(timeout=5)
                finally:
                    with get_engine().begin() as restore:
                        restore.execute(update(m.reference_node_scope).where(
                            m.reference_node_scope.c.reference_node_id == UUID(instrument)).values(status=original))
