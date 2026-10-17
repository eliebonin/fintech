"""Tenant-private presentation, original role eligibility and safe commands."""
import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, insert, update, func
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from apps.reference_api import governed_trade_configuration as g
from apps.reference_api.trade_configuration import ConfigurationConflict

TENANT, ACTOR = DEMO_IDS['tenant'], DEMO_IDS['demo_user_account']
ROLE = 'COUNTERPARTY'

@pytest.fixture
def connection():
    engine = create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as c:
        transaction = c.begin()
        try:
            yield c
        finally:
            transaction.rollback()
    engine.dispose()

def organisation(c, name='Synthetic party'):
    identifier = uuid4()
    parent = c.scalar(select(m.organisation.c.entity_id).limit(1))
    c.execute(insert(m.organisation).values(organisation_id=identifier, entity_id=parent,
        display_name=name, legal_name=name+' Ltd', organisation_type='LEGAL_ENTITY', status='ACTIVE'))
    return identifier

def command(**changes):
    return dict(expectedVersion=0, expectedRoleVersions={'COUNTERPARTY':0,'EXECUTING_BROKER':0},
        label='My party', internalCode='CP-1', notes='Private note', roles={},
        idempotencyKey=str(uuid4()), reason='Synthetic configuration', **changes)

def test_new_register_preserves_legacy_and_old_curated_members(connection):
    from apps.reference_api import tenant_organisations as t
    identifier=organisation(connection)
    initial=t.list_organisations(connection,TENANT,ACTOR)
    assert initial['policies'][ROLE]['mode']=='LEGACY'
    g.publish_selection(connection,TENANT,ACTOR,ROLE,[identifier],0,'Original editor')
    page=t.list_organisations(connection,TENANT,ACTOR)
    assert str(identifier) in {r['organisationId'] for r in page['items']}
    assert t.organisation_detail(connection,TENANT,ACTOR,identifier)['roles'][ROLE]

def test_metadata_does_not_change_eligibility_and_is_private(connection):
    from apps.reference_api import tenant_organisations as t
    identifier=organisation(connection)
    saved=t.save_organisation(connection,TENANT,ACTOR,identifier,command())
    assert saved['notes']=='Private note' and saved['versionNo']==1
    assert g.selection_view(connection,TENANT,ACTOR,ROLE)['mode']=='LEGACY'
    other=DEMO_IDS['second_tenant']
    # Account has a real membership there, but not TRADE_CONFIGURE.
    from security_master_schema.tenant_workspace import TenantActionForbidden
    with pytest.raises(TenantActionForbidden): t.organisation_detail(connection,other,ACTOR,identifier)
    assert not connection.scalar(select(m.tenant_organisation_profile.c.organisation_id).where(
        m.tenant_organisation_profile.c.tenant_id==other))

def test_role_activation_incremental_edits_and_legacy_adapter_share_one_list(connection):
    from apps.reference_api import tenant_organisations as t
    a,b=organisation(connection,'A party'),organisation(connection,'B party')
    t.activate_role(connection,TENANT,ACTOR,ROLE,dict(expectedVersion=0,ids=[str(a)],
        reason='Explicitly restrict new counterparties',idempotencyKey=str(uuid4())))
    data=command();data['expectedRoleVersions'][ROLE]=1;data['roles']={ROLE:True}
    t.save_organisation(connection,TENANT,ACTOR,b,data)
    assert {r['id'] for r in g.selection_view(connection,TENANT,ACTOR,ROLE)['records']}=={str(a),str(b)}
    assert g.selection_view(connection,TENANT,ACTOR,'EXECUTING_BROKER')['mode']=='LEGACY'
    g.publish_selection(connection,TENANT,ACTOR,ROLE,[],2,'Old client removes selections')
    assert not t.organisation_detail(connection,TENANT,ACTOR,b)['roles'][ROLE]
    with pytest.raises(ValueError): g.assert_selection(connection,TENANT,ROLE,b,'counterpartyOrganisationId')

def test_replay_is_exact_and_stale_profile_or_policy_edits_are_rejected(connection):
    from apps.reference_api import tenant_organisations as t
    identifier=organisation(connection);data=command()
    first=t.save_organisation(connection,TENANT,ACTOR,identifier,data)
    assert t.save_organisation(connection,TENANT,ACTOR,identifier,data)==first
    changed={**data,'notes':'Other intent'}
    with pytest.raises(ConfigurationConflict): t.save_organisation(connection,TENANT,ACTOR,identifier,changed)
    changed={**data,'idempotencyKey':str(uuid4())}
    with pytest.raises(ConfigurationConflict): t.save_organisation(connection,TENANT,ACTOR,identifier,changed)
    g.publish_selection(connection,TENANT,ACTOR,ROLE,[],0,'Concurrent policy edit')
    changed={**data,'idempotencyKey':str(uuid4()),'expectedVersion':1,'roles':{ROLE:True}}
    with pytest.raises(ConfigurationConflict): t.save_organisation(connection,TENANT,ACTOR,identifier,changed)

def test_unconfigured_role_cannot_be_enabled_by_saving_notes(connection):
    from apps.reference_api import tenant_organisations as t
    identifier=organisation(connection);data=command();data['roles']={ROLE:True}
    with pytest.raises(ConfigurationConflict): t.save_organisation(connection,TENANT,ACTOR,identifier,data)
    assert g.selection_view(connection,TENANT,ACTOR,ROLE)['mode']=='LEGACY'

def test_inactive_records_remain_inspectable_but_not_newly_enabled(connection):
    from apps.reference_api import tenant_organisations as t
    identifier=organisation(connection);g.publish_selection(connection,TENANT,ACTOR,ROLE,[identifier],0,'Setup')
    connection.execute(update(m.organisation).where(m.organisation.c.organisation_id==identifier).values(status='INACTIVE'))
    assert t.organisation_detail(connection,TENANT,ACTOR,identifier)['status']=='INACTIVE'
    assert not t.list_organisations(connection,TENANT,ACTOR,candidates=True,q='Synthetic party')['items']
    data=command();data['expectedRoleVersions'][ROLE]=1;data['roles']={ROLE:False}
    saved=t.save_organisation(connection,TENANT,ACTOR,identifier,data)
    assert not saved['roles'][ROLE]
    data=command();data['expectedVersion']=1;data['expectedRoleVersions'][ROLE]=2;data['roles']={ROLE:True}
    with pytest.raises(ValueError):t.save_organisation(connection,TENANT,ACTOR,identifier,data)

def test_search_pages_count_the_full_register_and_keep_role_filter(connection):
    from apps.reference_api import tenant_organisations as t
    identifiers=[organisation(connection,f'Synthetic paged {n:02}') for n in range(28)]
    g.publish_selection(connection,TENANT,ACTOR,ROLE,identifiers,0,'Setup pages')
    page=t.list_organisations(connection,TENANT,ACTOR,q='Synthetic paged',offset=25,limit=25,role=ROLE)
    assert page['total']==28 and len(page['items'])==3
    assert [r['legalName'] for r in page['items']]==['Synthetic paged 25 Ltd','Synthetic paged 26 Ltd','Synthetic paged 27 Ltd']

def test_http_contract_forbids_identity_inputs_and_returns_conflicts(connection):
    from fastapi import FastAPI
    from httpx import ASGITransport,AsyncClient
    from apps.reference_api.trade_configuration_routes import configuration_router
    from apps.reference_api.problem_details import configure_problem_details
    app=FastAPI();configure_problem_details(app)
    def dependency():yield connection
    app.include_router(configuration_router(dependency))
    identifier=organisation(connection)
    async def run():
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test',headers={
            'X-Tenant-Id':str(TENANT),'X-User-Account-Id':str(ACTOR)}) as client:
            response=await client.get('/v1/trade-configuration/organisations')
            assert response.status_code==200,response.text
            assert (await client.get(f'/v1/trade-configuration/organisations/{uuid4()}')).status_code==404
            assert (await client.get('/v1/trade-configuration/organisations',headers={
                'X-Tenant-Id':str(DEMO_IDS['second_tenant']),'X-User-Account-Id':str(ACTOR)})).status_code==403
            assert (await client.get('/v1/trade-configuration/organisations?limit=0')).status_code==422
            data=command()
            response=await client.post(f'/v1/trade-configuration/organisations/{identifier}',json={**data,'tenantId':str(TENANT)})
            assert response.status_code==422
            response=await client.post(f'/v1/trade-configuration/organisations/{identifier}',json={**data,'roles':{ROLE:'true'}})
            assert response.status_code==422
            response=await client.post(f'/v1/trade-configuration/organisations/{identifier}',json=data)
            assert response.status_code==200,response.text
            data['idempotencyKey']=str(uuid4())
            assert (await client.post(f'/v1/trade-configuration/organisations/{identifier}',json=data)).status_code==409
    asyncio.run(run())

def test_audit_failure_rolls_back_profile_and_role_change(connection,monkeypatch):
    from apps.reference_api import tenant_organisations as t
    identifier=organisation(connection)
    g.publish_selection(connection,TENANT,ACTOR,ROLE,[],0,'Initial curated list')
    data=command();data['expectedRoleVersions'][ROLE]=1;data['roles']={ROLE:True}
    def unavailable(*args,**kwargs):raise RuntimeError('Synthetic audit failure')
    monkeypatch.setattr(t,'audit',unavailable)
    with pytest.raises(RuntimeError,match='Synthetic audit failure'):
        t.save_organisation(connection,TENANT,ACTOR,identifier,data)
    assert t.organisation_detail(connection,TENANT,ACTOR,identifier)['versionNo']==0
    assert g.selection_view(connection,TENANT,ACTOR,ROLE)['records']==[]
    assert g.selection_view(connection,TENANT,ACTOR,ROLE)['versionNo']==1

def test_disabling_counterparty_rejects_new_trade_but_preserves_booked_party(connection):
    from apps.reference_api import tenant_organisations as t
    from apps.reference_api.contracts import TradeBookingRequest
    from apps.reference_api.repository import book_listed_cash_trade,get_booked_trade_detail
    identifier=DEMO_IDS['bank_a_organisation']
    g.publish_selection(connection,TENANT,ACTOR,ROLE,[identifier],0,'Initial counterparties')
    request=TradeBookingRequest(listingId=DEMO_IDS['hsbc_xlon_listing_node'],strategyId=DEMO_IDS['strategy'],
        side='BUY',quantity='10',executionPrice='12.5',tradeDatetime='2026-09-30T10:00:00Z',
        settlementDate='2026-10-02',counterpartyOrganisationId=identifier)
    booked=book_listed_cash_trade(connection,TENANT,ACTOR,request,str(uuid4()),'organisation-test').data
    data=command();data['expectedRoleVersions'][ROLE]=1;data['roles']={ROLE:False}
    t.save_organisation(connection,TENANT,ACTOR,identifier,data)
    count=connection.scalar(select(func.count()).select_from(m.trade))
    with pytest.raises(ValueError):
        book_listed_cash_trade(connection,TENANT,ACTOR,request,str(uuid4()),'organisation-test')
    assert connection.scalar(select(func.count()).select_from(m.trade))==count
    historical=get_booked_trade_detail(connection,TENANT,booked.trade.trade_id,'v1','organisation-history-test').data
    assert historical.parties[0].organisation_id==identifier

def test_private_metadata_is_not_disclosed_to_an_authorized_other_tenant(connection):
    from datetime import date
    from apps.reference_api import tenant_organisations as t
    other=DEMO_IDS['second_tenant'];identifier=organisation(connection)
    t.save_organisation(connection,TENANT,ACTOR,identifier,command())
    # Explicit grants in the disposable fixture; not an authorization mock.
    group=uuid4()
    connection.execute(insert(m.access_group).values(group_id=group,tenant_id=other,code='ORG_TEST',
        display_name='Organisation test operators',scope_mode='ALL'))
    connection.execute(insert(m.access_group_grant).values(tenant_id=other,group_id=group,action_code='TRADE_CONFIGURE'))
    connection.execute(insert(m.access_group_member).values(tenant_id=other,group_id=group,user_account_id=ACTOR))
    module=connection.scalar(select(m.platform_module.c.platform_module_id).where(m.platform_module.c.module_code=='TRADING'))
    entitlement=connection.scalar(select(m.tenant_module_entitlement.c.tenant_module_entitlement_id).where(
        m.tenant_module_entitlement.c.tenant_id==other,m.tenant_module_entitlement.c.platform_module_id==module))
    if entitlement:
        connection.execute(update(m.tenant_module_entitlement).where(m.tenant_module_entitlement.c.tenant_module_entitlement_id==entitlement).values(
            entitlement_state='GRANTED',valid_from=date(2020,1,1),valid_to=None))
    else:
        connection.execute(insert(m.tenant_module_entitlement).values(tenant_id=other,platform_module_id=module,
            entitlement_state='GRANTED',entitlement_source='MANUAL',valid_from=date(2020,1,1)))
    view=t.organisation_detail(connection,other,ACTOR,identifier)
    assert view['notes'] is None and view['label'] is None and view['internalCode'] is None
    assert view['history']==[] and view['versionNo']==0
    assert t.list_organisations(connection,other,ACTOR,q='Synthetic party')['items']==[]

def test_internal_codes_are_tenant_unique_and_bad_inputs_leave_no_profile(connection):
    from apps.reference_api import tenant_organisations as t
    a,b=organisation(connection,'First'),organisation(connection,'Second')
    t.save_organisation(connection,TENANT,ACTOR,a,command())
    with pytest.raises(ConfigurationConflict,match='Internal code'):
        t.save_organisation(connection,TENANT,ACTOR,b,command())
    data=command();data['internalCode']='Another';data['reason']='   '
    with pytest.raises(ValueError):t.save_organisation(connection,TENANT,ACTOR,b,data)
    assert t.organisation_detail(connection,TENANT,ACTOR,b)['versionNo']==0

@pytest.mark.parametrize('audit_failure',[False,True])
def test_full_api_retains_request_audit_or_rolls_back_the_whole_command(monkeypatch,audit_failure):
    from fastapi.testclient import TestClient
    from apps.reference_api.main import create_app
    from security_master_schema import access_management as am
    engine=create_engine(os.environ['DATABASE_URL'])
    with engine.begin() as c:identifier=organisation(c,'HTTP audited '+uuid4().hex)
    original=am.audit
    if audit_failure:
        def unavailable(c,actor,tenant,action,details,subject=None):
            if action=='TENANT_REQUEST':raise RuntimeError('Synthetic mandatory audit failure')
            return original(c,actor,tenant,action,details,subject)
        monkeypatch.setattr(am,'audit',unavailable)
    data=command();data['internalCode']=None
    try:
        with TestClient(create_app(engine=engine),raise_server_exceptions=False) as client:
            response=client.post(f'/v1/trade-configuration/organisations/{identifier}',json=data,headers={
                'X-Tenant-Id':str(TENANT),'X-User-Account-Id':str(ACTOR)})
        with engine.connect() as c:
            profile=c.scalar(select(m.tenant_organisation_profile.c.version_no).where(
                m.tenant_organisation_profile.c.tenant_id==TENANT,m.tenant_organisation_profile.c.organisation_id==identifier))
            events=c.scalar(select(func.count()).select_from(m.trade_configuration_event).where(
                m.trade_configuration_event.c.subject_id==identifier))
            if audit_failure:
                assert response.status_code==500 and 'Synthetic mandatory' not in response.text
                assert profile is None and events==0
            else:
                assert response.status_code==200,response.text
                assert profile==1 and events==1
                request_event=c.execute(select(m.access_audit_event).where(m.access_audit_event.c.action=='TENANT_REQUEST',
                    m.access_audit_event.c.details['resourceIds'].contains([str(identifier)]))).mappings().one()
                assert request_event['details']['permission']=='TRADE_CONFIGURE'
                assert request_event['details']['requestId']==response.headers['X-Request-Id']
    finally:engine.dispose()
