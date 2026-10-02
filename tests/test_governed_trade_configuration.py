"""Governed trade data: lightweight tests followed by rollback-backed integration."""
from uuid import uuid4
import pytest
from apps.reference_api.trade_properties import normalize_property_value
from sqlalchemy import create_engine, select, insert, update, func
from sqlalchemy.exc import IntegrityError
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS, load_demo_data
from security_master_schema.tenant_workspace import TenantActionForbidden
from apps.reference_api import governed_trade_configuration as g
from apps.reference_api.trade_configuration import create_property, retire_property, ConfigurationConflict
from apps.reference_api.contracts import TradeBookingRequest
from apps.reference_api.repository import book_listed_cash_trade, get_booked_trade_detail, IdempotencyKeyConflict

TENANT, ACTOR = DEMO_IDS["tenant"], DEMO_IDS["demo_user_account"]

@pytest.fixture(scope="module")
def engine():
    result=create_engine("postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm")
    load_demo_data(result)
    yield result
    result.dispose()

@pytest.fixture
def connection(engine):
    with engine.connect() as connection:
        transaction=connection.begin()
        try: yield connection
        finally: transaction.rollback()

def catalogue(connection):
    values=dict(code="TEST_"+uuid4().hex,label="Investment rationale",description="Reason for execution",reason="Test setup")
    created=g.create_catalogue(connection,TENANT,ACTOR,values)
    assert g.create_catalogue(connection,TENANT,ACTOR,values)==created
    g.catalogue_lifecycle(connection,TENANT,ACTOR,created["catalogueId"],"ACTIVE","Publish test catalogue")
    return created["catalogueId"]

def entry(connection,identifier,code="CORE"):
    return g.create_record(connection,TENANT,ACTOR,identifier,dict(code=code,label="Core allocation",description="Long-term holding",reason="Publish test entry"))

def field(connection,identifier):
    return create_property(connection,TENANT,ACTOR,dict(code="TEST_"+uuid4().hex,label="Rationale",description="Why this trade was executed",valueType="REFERENCE",catalogueId=identifier))

def book(connection,definition,record,key=None):
    request=TradeBookingRequest(listingId=DEMO_IDS["hsbc_xlon_listing_node"],strategyId=DEMO_IDS["strategy"],side="BUY",quantity="1",executionPrice="12.5",tradeDatetime="2026-10-01T10:00:00Z",settlementDate="2026-10-05",properties=[dict(definitionId=definition,value=str(record))])
    return book_listed_cash_trade(connection,TENANT,ACTOR,request,key or str(uuid4()),"governed-test")

def test_governed_demo_provisioning_replays_without_duplicate_fields_or_entries(connection):
    import json
    from pathlib import Path
    from scripts.provision_trade_properties import provision_config
    config=json.loads((Path(__file__).resolve().parents[1]/"docs/examples/trade-properties-demo.json").read_text())
    # Unique codes keep this independent of the operator's edited demo catalogue.
    suffix=uuid4().hex
    for source in config["catalogues"]: source["code"] += "_"+suffix
    for prop in config["properties"]:
        prop["code"] += "_"+suffix
        if "catalogueCode" in prop: prop["catalogueCode"] += "_"+suffix
    config["tags"]=[]
    provision_config(connection,DEMO_IDS["tenant"],DEMO_IDS["demo_user_account"],config)
    before=connection.scalar(select(func.count()).select_from(m.trade_configuration_event))
    provision_config(connection,DEMO_IDS["tenant"],DEMO_IDS["demo_user_account"],config)
    assert connection.scalar(select(func.count()).select_from(m.trade_configuration_event))==before
    assert len(connection.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.code.in_([p["code"].upper() for p in config["properties"]]))).all())==5


def test_invalid_config_rolls_back_catalogue_publication(connection):
    from scripts.provision_trade_properties import provision_config
    code="ROLLBACK_"+uuid4().hex
    config={"catalogues":[{"code":code,"label":"Rollback","records":[]}],"properties":[{"code":"BAD_"+uuid4().hex,"label":"Bad","valueType":"REFERENCE","catalogueCode":"UNDECLARED"}]}
    with pytest.raises(ValueError,match="must be declared"):
        provision_config(connection,DEMO_IDS["tenant"],DEMO_IDS["demo_user_account"],config)
    assert not connection.scalar(select(m.reference_catalogue.c.catalogue_id).where(m.reference_catalogue.c.code==code))


def test_integer_values_are_exact_and_bounded():
    assert normalize_property_value("+0012", "INTEGER", []) == "12"
    for value in ("1.5", "1e3", "9" * 31, True):
        with pytest.raises(ValueError): normalize_property_value(value, "INTEGER", [])

def test_reference_identity_is_not_a_label():
    identifier = uuid4()
    assert normalize_property_value(str(identifier), "REFERENCE", []) == str(identifier)
    with pytest.raises(ValueError): normalize_property_value("Growth", "REFERENCE", [])

def test_reference_booking_preserves_label_version_and_replays_after_retirement(connection):
    cat=catalogue(connection); old=entry(connection,cat); prop=field(connection,cat)
    key=str(uuid4()); first=book(connection,prop["definitionId"],old["recordVersionId"],key)
    assert first.data.properties[0].display_value == "CORE — Core allocation"
    replacement=g.change_record(connection,TENANT,ACTOR,cat,old["recordVersionId"],dict(label="Core portfolio",description="Long-term holding"),"Label correction only")
    assert replacement["recordId"] == old["recordId"] and replacement["versionNo"] == 2
    assert g.change_record(connection,TENANT,ACTOR,cat,old["recordVersionId"],dict(label="Core portfolio",description="Long-term holding"),"Replay correction") == replacement
    read=get_booked_trade_detail(connection,TENANT,first.data.trade.trade_id,"v1","read")
    assert read.data.properties[0].display_value == "CORE — Core allocation"
    assert read.data.properties[0].record_version == 1
    assert book(connection,prop["definitionId"],old["recordVersionId"],key).data.trade.trade_id == first.data.trade.trade_id
    with pytest.raises(ValueError,match="active record"): book(connection,prop["definitionId"],old["recordVersionId"])
    with pytest.raises(IdempotencyKeyConflict): book(connection,prop["definitionId"],replacement["recordVersionId"],key)
    retire_property(connection,TENANT,ACTOR,prop["definitionId"])
    g.catalogue_lifecycle(connection,TENANT,ACTOR,cat,"RETIRED","Remove catalogue for new bookings")
    assert book(connection,prop["definitionId"],old["recordVersionId"],key).data.trade.trade_id == first.data.trade.trade_id

def test_wrong_catalogue_selection_leaves_no_partial_trade(connection):
    first,second=catalogue(connection),catalogue(connection)
    record=entry(connection,second);prop=field(connection,first)
    before=connection.scalar(select(func.count()).select_from(m.trade))
    with pytest.raises(ValueError): book(connection,prop["definitionId"],record["recordVersionId"])
    assert connection.scalar(select(func.count()).select_from(m.trade)) == before

def test_catalogue_retirement_blocks_active_bindings_and_republication(connection):
    cat=catalogue(connection);prop=field(connection,cat)
    with pytest.raises(ConfigurationConflict,match="active fields"): g.catalogue_lifecycle(connection,TENANT,ACTOR,cat,"RETIRED","Retire in use")
    retire_property(connection,TENANT,ACTOR,prop["definitionId"])
    g.catalogue_lifecycle(connection,TENANT,ACTOR,cat,"RETIRED","No longer in use")
    with pytest.raises(ConfigurationConflict,match="republished"): g.catalogue_lifecycle(connection,TENANT,ACTOR,cat,"ACTIVE","Try to resurrect")

def test_record_codes_cannot_be_recycled_for_new_meanings(connection):
    cat=catalogue(connection);old=entry(connection,cat)
    g.change_record(connection,TENANT,ACTOR,cat,old["recordVersionId"],reason="Retire meaning")
    with pytest.raises(ConfigurationConflict): entry(connection,cat)
    new=entry(connection,cat,"NEW_MEANING")
    assert new["recordId"] != old["recordId"]

def test_catalogue_draft_and_cross_tenant_boundaries(connection):
    cat=g.create_catalogue(connection,TENANT,ACTOR,dict(code="TEST_"+uuid4().hex,label="Draft",description="Unpublished",reason="Prepare"))["catalogueId"]
    entry(connection,cat)
    assert g.list_records(connection,TENANT,ACTOR,cat)==[]
    with pytest.raises(ValueError,match="Publish"): field(connection,cat)
    with pytest.raises(LookupError): g.find_catalogue(connection,DEMO_IDS["second_tenant"],cat)
    with pytest.raises(TenantActionForbidden): g.list_catalogues(connection,DEMO_IDS["second_tenant"],ACTOR)

def test_standard_eligibility_publication_stale_edits_and_empty_lists(connection):
    role="COUNTERPARTY"; bank=DEMO_IDS["bank_a_organisation"]
    initial=g.selection_view(connection,TENANT,ACTOR,role)
    assert initial["mode"] == "LEGACY"
    saved=g.publish_selection(connection,TENANT,ACTOR,role,[bank],0,"Approve tenant selection")
    assert saved["versionNo"] == 1
    assert g.publish_selection(connection,TENANT,ACTOR,role,[bank],0,"Replay")==saved
    g.assert_selection(connection,TENANT,role,bank,"counterpartyOrganisationId")
    with pytest.raises(ValueError): g.assert_selection(connection,TENANT,role,uuid4(),"counterpartyOrganisationId")
    with pytest.raises(ConfigurationConflict): g.publish_selection(connection,TENANT,ACTOR,role,[],0,"Stale edit")
    g.publish_selection(connection,TENANT,ACTOR,role,[],1,"Disable optional selections")
    assert g.selection_candidates(connection,TENANT,ACTOR,role)==[]
    with pytest.raises(ValueError): g.assert_selection(connection,TENANT,role,bank,"counterpartyOrganisationId")
    assert g.selection_candidates(connection,TENANT,ACTOR,role,curated=False)

def test_invalid_selection_does_not_publish_policy(connection):
    with pytest.raises(ValueError): g.publish_selection(connection,TENANT,ACTOR,"TRADER",[uuid4()],0,"Not a tenant member")
    assert g.selection_view(connection,TENANT,ACTOR,"TRADER")["versionNo"]==0

def test_relational_history_and_audit_cannot_be_rewritten(connection):
    cat=catalogue(connection);record=entry(connection,cat);prop=field(connection,cat)
    booked=book(connection,prop["definitionId"],record["recordVersionId"])
    with pytest.raises(IntegrityError),connection.begin_nested():
        connection.execute(update(m.trade_property_reference).where(m.trade_property_reference.c.trade_id==booked.data.trade.trade_id).values(record_version_id=uuid4()))
    with pytest.raises(IntegrityError),connection.begin_nested():
        connection.execute(update(m.reference_catalogue_record).where(m.reference_catalogue_record.c.record_version_id==record["recordVersionId"]).values(label="Different meaning"))
    with pytest.raises(IntegrityError),connection.begin_nested():
        connection.execute(update(m.trade_configuration_event).where(m.trade_configuration_event.c.tenant_id==TENANT).values(reason="Rewritten"))
    with pytest.raises(IntegrityError),connection.begin_nested():
        connection.execute(insert(m.trade_property_value).values(trade_id=booked.data.trade.trade_id,tenant_id=TENANT,definition_id=prop["definitionId"],value=str(record["recordVersionId"])))

def test_record_search_is_bounded_and_history_is_explicit(connection):
    cat=catalogue(connection)
    for i in range(30): entry(connection,cat,f"ENTRY_{i:02}")
    assert len(g.list_records(connection,TENANT,ACTOR,cat))==25
    assert len(g.list_records(connection,TENANT,ACTOR,cat,offset=25))==5
    assert len(g.list_records(connection,TENANT,ACTOR,cat,q="ENTRY_01"))==1

def test_required_catalogue_needs_a_value_and_cannot_lose_last_entry(connection):
    cat=catalogue(connection)
    payload=dict(code="TEST_"+uuid4().hex,label="Required rationale",valueType="REFERENCE",catalogueId=cat,required=True,acknowledgeRequiredImpact=True)
    with pytest.raises(ValueError,match="at least one"): create_property(connection,TENANT,ACTOR,payload)
    record=entry(connection,cat)
    prop=create_property(connection,TENANT,ACTOR,payload)
    with pytest.raises(ConfigurationConflict,match="last selectable"):g.change_record(connection,TENANT,ACTOR,cat,record["recordVersionId"],reason="Remove last entry")
    retire_property(connection,TENANT,ACTOR,prop["definitionId"])
    g.change_record(connection,TENANT,ACTOR,cat,record["recordVersionId"],reason="Field retired")

def test_http_configuration_roundtrip_and_validation(connection):
    import asyncio
    from fastapi import FastAPI
    from httpx import ASGITransport,AsyncClient
    from apps.reference_api.trade_configuration_routes import configuration_router
    from apps.reference_api.problem_details import configure_problem_details
    app=FastAPI();configure_problem_details(app)
    def dependency():yield connection
    app.include_router(configuration_router(dependency))
    headers={"X-Tenant-Id":str(TENANT),"X-User-Account-Id":str(ACTOR)}
    async def run():
        async with AsyncClient(transport=ASGITransport(app=app),base_url="http://test",headers=headers) as client:
            result=await client.post("/v1/trade-configuration/catalogues",json=dict(code="TEST_"+uuid4().hex,label="HTTP catalogue",description="Test",reason="Create"))
            assert result.status_code==201,result.text
            identifier=result.json()["data"]["catalogueId"]
            opened=await client.get(f"/v1/trade-configuration/catalogues/{identifier}")
            assert opened.status_code==200 and opened.json()["data"]["catalogueId"]==identifier
            foreign=await client.get(f"/v1/trade-configuration/catalogues/{identifier}",headers={"X-Tenant-Id":str(DEMO_IDS["second_tenant"]),"X-User-Account-Id":str(ACTOR)})
            assert foreign.status_code==403  # This account is not an administrator there.
            result=await client.post(f"/v1/trade-configuration/catalogues/{identifier}/records",json=dict(code="HTTP_ENTRY",label="HTTP entry",description="Entry",reason="Publish entry"))
            assert result.status_code==201,result.text
            result=await client.post(f"/v1/trade-configuration/catalogues/{identifier}/publish",json={"reason":"Publish catalogue"})
            assert result.status_code==200,result.text
            result=await client.post("/v1/trade-configuration/properties",json=dict(code="TEST_"+uuid4().hex,label="HTTP property",description="Controlled field",valueType="REFERENCE",catalogueId=identifier))
            assert result.status_code==201,result.text
            assert result.json()["data"]["catalogueId"]==identifier
            assert (await client.get(f"/v1/trade-configuration/catalogues/{identifier}/records")).json()["data"][0]["label"]=="HTTP entry"
            assert (await client.get("/v1/trade-configuration/catalogues?limit=101")).status_code==422
            assert (await client.get("/v1/trade-configuration/catalogues",headers={"X-Tenant-Id":str(DEMO_IDS["second_tenant"])})).status_code==403
            assert (await client.post("/v1/trade-configuration/properties",json=dict(code="BAD",label="Bad",valueType="REFERENCE",catalogueId=str(uuid4())))).status_code==404
    asyncio.run(run())

def test_real_foreign_tenant_catalogue_cannot_bind_or_supply_values(connection):
    foreign=uuid4(); foreign_record=uuid4()
    connection.execute(insert(m.reference_catalogue).values(catalogue_id=foreign,tenant_id=DEMO_IDS["second_tenant"],code="FOREIGN_"+uuid4().hex,label="Private foreign catalogue",status="ACTIVE",created_by_user_account_id=ACTOR))
    connection.execute(insert(m.reference_catalogue_record).values(record_version_id=foreign_record,record_id=uuid4(),catalogue_id=foreign,code="PRIVATE",label="Private foreign value",created_by_user_account_id=ACTOR))
    with pytest.raises(LookupError): g.get_catalogue(connection,TENANT,ACTOR,foreign)
    with pytest.raises(LookupError): field(connection,foreign)
    with pytest.raises(IntegrityError),connection.begin_nested():
        connection.execute(insert(m.trade_property_definition).values(tenant_id=TENANT,code="TEST_"+uuid4().hex,label="Forged binding",value_type="REFERENCE",catalogue_id=foreign,created_by_user_account_id=ACTOR))
    own=catalogue(connection);prop=field(connection,own)
    with pytest.raises(ValueError): book(connection,prop["definitionId"],foreign_record)
    assert foreign not in {c["catalogueId"] for c in g.list_catalogues(connection,TENANT,ACTOR,limit=100)}

def test_management_and_booking_serialise_with_same_tenant_lock(connection,engine):
    import hashlib
    from sqlalchemy import text
    catalogue(connection)
    key=int.from_bytes(hashlib.sha256(f"trade-catalogue:{TENANT}".encode()).digest()[:8],"big",signed=True)
    with engine.begin() as competing:
        assert competing.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"),{"key":key}) is False

def test_revoked_membership_cannot_manage_existing_catalogue(connection):
    cat=catalogue(connection)
    connection.execute(update(m.tenant_user_account).where(m.tenant_user_account.c.tenant_id==TENANT,m.tenant_user_account.c.user_account_id==ACTOR).values(status="SUSPENDED"))
    with pytest.raises(TenantActionForbidden):g.create_record(connection,TENANT,ACTOR,cat,dict(code="FORGED",label="No access",reason="Attempt"))
