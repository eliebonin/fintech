"""Disposable reporting commands never submit reports or alter trades."""
from uuid import uuid4,UUID
from sqlalchemy import select,func
import pytest
from tests.test_access_api import client,headers
from tests.test_strategy_scopes_api import scoped_user
from security_master_schema.demo_data import DEMO_IDS as ids
from apps.reference_api.db import get_engine
from security_master_schema import models as m

def profile_payload():
    stem='TEST00000000000000'
    expanded=''.join(str(ord(c)-55) if c.isalpha() else c for c in stem)
    return dict(name='Synthetic reporting entity',lei=stem+str(98-int(expanded+'00')%97).zfill(2),
        firmCategory='MIFID_FIRM',firmScope='IN_SCOPE',reason='Synthetic compliance assessment')

@pytest.fixture
def reporting(client):
    root={'X-User-Account-Id':str(ids['platform_admin_user_account'])}
    r=client.put(f"/v1/platform/tenants/{ids['tenant']}/modules/REGULATORY_REPORTING",headers=root,json={'enabled':True})
    assert r.status_code==200,r.text
    h,g=scoped_user(client,['REPORTING_READ','REPORTING_CONFIGURE','REPORTING_PREPARE','REPORTING_REVIEW','REPORTING_EXPORT'],[ids['strategy']])
    p=client.post('/v1/regulatory-reporting/profiles',headers=h,json=profile_payload())
    assert p.status_code==201,p.text
    return h,g,p.json()['profileId']

def prepare_payload(profile):
    return dict(profileId=profile,strategyId=str(ids['strategy']),fromDate='2026-09-30',toDate='2026-09-30')

def booking():
    from tests.test_cash_booking_integrity import payload,book
    with get_engine().begin() as c:return book(c,payload())

def test_module_is_required_even_for_admin(client):
    assert client.post('/v1/regulatory-reporting/profiles',headers=headers(),json=profile_payload()).status_code==403

def test_prepare_is_repeatable_preserves_precise_facts_and_review_history(client,reporting):
    h,g,p=reporting;booking();data=prepare_payload(p)
    r=client.post('/v1/regulatory-reporting/prepare',headers=h,json=data)
    assert r.status_code==200,r.text
    assert r.json()['created']>=1
    assert client.post('/v1/regulatory-reporting/prepare',headers=h,json=data).json()['created']==0
    items=client.get('/v1/regulatory-reporting/candidates',headers=h,params=data).json()['items']
    row=next(x for x in items if x['facts']['executionPrice']=='1.230000000000')
    assert row['facts']['executionTime']=='2026-09-30T10:00:00+00:00'
    mapping=dict(instrumentIsin='GB0002634946',buyerId='SYNTHETIC_BUYER',sellerId='SYNTHETIC_SELLER',
        capacity='AOTC',venueMic='XLON',investmentDecisionId='SYNTHETIC_DECISION',executionDecisionId='SYNTHETIC_EXECUTION')
    review={'expectedRevision':row['revision'],'action':'REPORTABLE','reason':'Scope checked for synthetic execution','mapping':mapping}
    r=client.post(f"/v1/regulatory-reporting/candidates/{row['candidateId']}/review",headers=h,json=review)
    assert r.status_code==200,r.text
    assert r.json()['included']
    assert client.post(f"/v1/regulatory-reporting/candidates/{row['candidateId']}/review",headers=h,json=review).status_code==409
    history=client.get(f"/v1/regulatory-reporting/candidates/{row['candidateId']}",headers=h).json()
    assert len(history['history'])==2 and history['history'][-1]['reason']==review['reason']
    assert client.post('/v1/regulatory-reporting/prepare',headers=h,json=data).json()['changed']==0

def test_guessed_strategy_and_candidate_denied(client,reporting):
    h,g,p=reporting;booking();data=prepare_payload(p)
    client.post('/v1/regulatory-reporting/prepare',headers=h,json=data)
    result=client.get('/v1/regulatory-reporting/candidates',headers=h,params=data).json()
    limited,_=scoped_user(client,['REPORTING_READ'],[ids['uk_fund_strategy']])
    assert client.get('/v1/regulatory-reporting/candidates',headers=limited,params=data).status_code==403
    assert client.get('/v1/regulatory-reporting/candidates/'+result['items'][0]['candidateId'],headers=limited).status_code==403
    assert client.post('/v1/regulatory-reporting/prepare',headers=limited,json=data).status_code==403

def test_export_freezes_revisions_retries_and_rechecks_access(client,reporting):
    h,g,p=reporting;booking();data=prepare_payload(p)
    client.post('/v1/regulatory-reporting/prepare',headers=h,json=data)
    rows=client.get('/v1/regulatory-reporting/candidates',headers=h,params=data).json()['items']
    target=rows[0]
    r=client.post('/v1/regulatory-reporting/candidates/'+target['candidateId']+'/review',headers=h,
        json=dict(expectedRevision=target['revision'],action='REPORTABLE',reason='Synthetic scope confirmed',
        mapping=dict(instrumentIsin='GB0002634946',buyerId='B',sellerId='S',capacity='AOTC',venueMic='XLON',investmentDecisionId='I',executionDecisionId='E')))
    assert r.status_code==200,r.text
    revisions={target['candidateId']:r.json()['revision']}
    key=str(uuid4());payload=data|{'expectedRevisions':revisions}
    r=client.post('/v1/regulatory-reporting/exports',headers=h|{'Idempotency-Key':key},json=payload)
    assert r.status_code==201,r.text
    export=r.json();assert export['manifest']['validationLevel']=='PREPARATION_ONLY'
    again=client.post('/v1/regulatory-reporting/exports',headers=h|{'Idempotency-Key':key},json=payload)
    assert again.json()['exportId']==export['exportId']
    downloaded=client.get('/v1/regulatory-reporting/exports/'+export['exportId'],headers=h)
    assert downloaded.status_code==200 and downloaded.json()['contentHash']==export['contentHash']
    limited,_=scoped_user(client,['REPORTING_READ'],[ids['uk_fund_strategy']])
    assert client.get('/v1/regulatory-reporting/exports/'+export['exportId'],headers=limited).status_code==403
    assert client.post('/v1/regulatory-reporting/exports',headers=h|{'Idempotency-Key':key},json=payload|{'toDate':'2026-10-01'}).status_code==409

def test_profile_revisions_stale_save_and_evidence_immutability(client,reporting):
    from regulatory_reporting import tables as t
    h,g,p=reporting
    data=profile_payload()|{'name':'Changed entity','expectedRevision':1}
    assert client.post('/v1/regulatory-reporting/profiles/'+p,headers=h,json=data).status_code==200
    assert client.post('/v1/regulatory-reporting/profiles/'+p,headers=h,json=data).status_code==409
    with get_engine().begin() as c:
        assert c.scalar(select(func.count()).select_from(t.profile_revision).where(t.profile_revision.c.profile_id==UUID(p)))==2
        with pytest.raises(Exception,match='immutable'):
            with c.begin_nested():c.execute(t.profile_revision.delete().where(t.profile_revision.c.profile_id==UUID(p)))

def ready_row(client,h,p):
    booking();data=prepare_payload(p)
    assert client.post('/v1/regulatory-reporting/prepare',headers=h,json=data).status_code==200
    row=client.get('/v1/regulatory-reporting/candidates',headers=h,params=data).json()['items'][0]
    request=dict(expectedRevision=row['revision'],action='REPORTABLE',reason='Synthetic reportability confirmed',
        mapping=dict(instrumentIsin='GB0002634946',buyerId='B',sellerId='S',capacity='AOTC',venueMic='XLON',investmentDecisionId='I',executionDecisionId='E'))
    r=client.post('/v1/regulatory-reporting/candidates/'+row['candidateId']+'/review',headers=h,json=request)
    assert r.status_code==200,r.text
    return r.json(),data

def test_profile_changes_block_export_and_keep_human_choices_on_reprepare(client,reporting):
    h,g,p=reporting;row,data=ready_row(client,h,p)
    update=profile_payload()|dict(name='Reassessed firm',expectedRevision=1)
    assert client.post('/v1/regulatory-reporting/profiles/'+p,headers=h,json=update).status_code==200
    revisions=client.get('/v1/regulatory-reporting/export-preview',headers=h,params=data).json()['expectedRevisions']
    r=client.post('/v1/regulatory-reporting/exports',headers=h|{'Idempotency-Key':str(uuid4())},json=data|{'expectedRevisions':revisions})
    assert r.status_code==409,r.text
    assert client.post('/v1/regulatory-reporting/prepare',headers=h,json=data).json()['changed']>=1
    changed=client.get('/v1/regulatory-reporting/candidates/'+row['candidateId'],headers=h).json()
    assert changed['needsReassessment'] and not changed['included']
    assert changed['mapping']==row['mapping'] and changed['reportability']=='NEEDS_ASSESSMENT'
    assert changed['history'][-1]['decision']=='REPORTABLE'
    assert client.post('/v1/regulatory-reporting/candidates/'+row['candidateId']+'/review',headers=h,
        json=dict(expectedRevision=changed['revision'],action='UPDATE_MAPPING',reason='Confirmed new entity assessment')).json()['included']

def test_all_pages_count_and_export_preview_are_server_side(client,reporting):
    from tests.test_cash_booking_integrity import book
    h,g,p=reporting
    with get_engine().begin() as c:
        for _ in range(27):book(c)
    data=prepare_payload(p)
    client.post('/v1/regulatory-reporting/prepare',headers=h,json=data)
    first=client.get('/v1/regulatory-reporting/candidates',headers=h,params=data|{'limit':25}).json()
    second=client.get('/v1/regulatory-reporting/candidates',headers=h,params=data|{'limit':25,'offset':25}).json()
    assert first['total']>=27 and first['totals']['total']==first['total']
    assert len(first['items'])==25 and second['items']
    assert set(r['candidateId'] for r in first['items']).isdisjoint(r['candidateId'] for r in second['items'])
    last=second['items'][-1]
    assert client.post('/v1/regulatory-reporting/candidates/'+last['candidateId']+'/review',headers=h,
        json=dict(expectedRevision=last['revision'],action='HOLD',reason='Waiting for supporting evidence')).status_code==200
    held=client.get('/v1/regulatory-reporting/candidates',headers=h,params=data|{'status':'HELD'}).json()
    assert held['total']==1 and held['items'][0]['candidateId']==last['candidateId']
    assert held['totals']['total']==first['total']

def test_export_replay_and_download_fail_after_strategy_revocation(client,reporting):
    h,g,p=reporting;row,data=ready_row(client,h,p);key=str(uuid4())
    preview=client.get('/v1/regulatory-reporting/export-preview',headers=h,params=data).json()
    body=data|{'expectedRevisions':preview['expectedRevisions']}
    artifact=client.post('/v1/regulatory-reporting/exports',headers=h|{'Idempotency-Key':key},json=body).json()
    with get_engine().begin() as c:c.execute(m.access_group_strategy.delete().where(m.access_group_strategy.c.group_id==UUID(g)))
    assert client.post('/v1/regulatory-reporting/exports',headers=h|{'Idempotency-Key':key},json=body).status_code==403
    assert client.get('/v1/regulatory-reporting/exports/'+artifact['exportId'],headers=h).status_code==403
    assert client.get('/v1/regulatory-reporting/exports',headers=h).json()['total']==0

def test_failed_request_audit_rolls_back_profile(client,reporting,monkeypatch):
    from regulatory_reporting import tables as t
    h,g,p=reporting
    with get_engine().connect() as c:before=c.scalar(select(func.count()).select_from(t.profile))
    def fail(*args,**kwargs):raise RuntimeError('Synthetic audit failure')
    monkeypatch.setattr('security_master_schema.access_management.audit',fail)
    assert client.post('/v1/regulatory-reporting/profiles',headers=h,json=profile_payload()).status_code==500
    with get_engine().connect() as c:assert c.scalar(select(func.count()).select_from(t.profile))==before

def test_cancelled_source_requires_repreparation_and_cannot_be_new_export(client,reporting):
    h,g,p=reporting;row,data=ready_row(client,h,p)
    with get_engine().begin() as c:
        original=c.execute(select(m.trade).where(m.trade.c.trade_id==UUID(row['tradeId']))).mappings().one()
        c.execute(m.trade_lifecycle_event.insert().values(trade_id=original['trade_id'],sequence_no=2,
            event_type='CANCELLED',event_datetime_utc=original['trade_datetime_utc'],event_payload='{}',recorded_by_user_account_id=ids['demo_user_account']))
    preview=client.get('/v1/regulatory-reporting/export-preview',headers=h,params=data).json()
    response=client.post('/v1/regulatory-reporting/exports',headers=h|{'Idempotency-Key':str(uuid4())},json=data|{'expectedRevisions':preview['expectedRevisions']})
    assert response.status_code==409
    assert client.post('/v1/regulatory-reporting/prepare',headers=h,json=data).status_code==200
    candidate=client.get('/v1/regulatory-reporting/candidates/'+row['candidateId'],headers=h).json()
    assert not candidate['included'] and 'lifecycleReview' in candidate['missingFields']

def test_current_reference_visibility_protects_retained_download_and_rows(client,reporting):
    h,g,p=reporting;row,data=ready_row(client,h,p)
    preview=client.get('/v1/regulatory-reporting/export-preview',headers=h,params=data).json()
    artifact=client.post('/v1/regulatory-reporting/exports',headers=h|{'Idempotency-Key':str(uuid4())},json=data|{'expectedRevisions':preview['expectedRevisions']}).json()
    with get_engine().begin() as c:
        old=dict(c.execute(select(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id==ids['hsbc_instrument_node'])).mappings().one())
        c.execute(m.reference_node_scope.update().where(m.reference_node_scope.c.reference_node_id==ids['hsbc_instrument_node']).values(
            scope_type='TENANT_PRIVATE',owner_tenant_id=ids['second_tenant']))
    try:
        assert client.get('/v1/regulatory-reporting/candidates/'+row['candidateId'],headers=h).status_code==403
        assert client.get('/v1/regulatory-reporting/candidates',headers=h,params=data).json()['items']==[]
        assert client.get('/v1/regulatory-reporting/exports/'+artifact['exportId'],headers=h).status_code==403
    finally:
        with get_engine().begin() as c:c.execute(m.reference_node_scope.update().where(
            m.reference_node_scope.c.reference_node_id==ids['hsbc_instrument_node']).values(scope_type=old['scope_type'],owner_tenant_id=old['owner_tenant_id']))
