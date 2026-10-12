"""Controlled additions preserve original immutable components and lineage."""
from decimal import Decimal as D
from uuid import uuid4
import pytest
from tests.test_valuation_service import valued,service
from tests.test_position_attribution_storage import staged,reviewer
from valuation import storage
from security_master_schema.demo_data import DEMO_IDS as ids


def test_pending_change_blocks_publish_and_independent_approval_stages_new_version(valued):
    from valuation.amendments import request_component_change,approve_component_change
    c,r,_=valued
    original=staged(c,r,service().calculate(c,r))
    before=storage.batch_view(c,r.tenant_id,original);owner=before['items'][0]['attribution_id']
    payload=dict(component='ADJUSTMENT',amount=D('-10'),reason='Synthetic correction',sourceReference='OPS NOTICE')
    key=str(uuid4())
    request=request_component_change(c,r.tenant_id,original,owner,ids['demo_user_account'],payload,key)
    assert request_component_change(c,r.tenant_id,original,owner,ids['demo_user_account'],payload,key)==request
    actor=reviewer(c)
    with pytest.raises(ValueError,match='pending'): storage.publish(c,r.tenant_id,original,actor,'Reviewed')
    with pytest.raises(ValueError,match='independent'): approve_component_change(c,r.tenant_id,request,ids['demo_user_account'],'Approved')
    revised=approve_component_change(c,r.tenant_id,request,actor,'Adjustment evidence reviewed')
    after=storage.batch_view(c,r.tenant_id,revised)
    assert after['items'][0]['market_pnl']==before['items'][0]['market_pnl']
    assert after['items'][0]['gross_pnl']==before['items'][0]['gross_pnl']
    assert after['items'][0]['net_pnl']==before['items'][0]['net_pnl']-10
    assert storage.batch_view(c,r.tenant_id,original)['items'][0]['components']==before['items'][0]['components']
    assert after['items'][0]['lineage']==before['items'][0]['lineage'] or {e['event_id'] for e in after['items'][0]['lineage']}=={e['event_id'] for e in before['items'][0]['lineage']}
    storage.publish(c,r.tenant_id,revised,actor,'Reviewed new candidate')
    assert storage.batch_view(c,r.tenant_id,revised)['status']=='PUBLISHED'


def test_published_results_cannot_be_amended_and_foreign_requests_are_hidden(valued):
    from valuation.amendments import request_component_change,approve_component_change
    c,r,_=valued
    batch=staged(c,r,service().calculate(c,r));owner=storage.batch_view(c,r.tenant_id,batch)['items'][0]['attribution_id']
    payload=dict(component='ADJUSTMENT',amount=D('-10'),reason='Synthetic correction',sourceReference='OPS')
    with pytest.raises(LookupError): request_component_change(c,ids['second_tenant'],batch,owner,ids['demo_user_account'],payload,str(uuid4()))
    storage.publish(c,r.tenant_id,batch,reviewer(c),'Reviewed')
    with pytest.raises(ValueError,match='staged'): request_component_change(c,r.tenant_id,batch,owner,ids['demo_user_account'],payload,str(uuid4()))


def test_another_candidate_makes_old_requests_stale_and_rejected_requests_unblock_publish(valued):
    from valuation.amendments import request_component_change,approve_component_change,reject_component_change
    from valuation import tables as t
    from sqlalchemy import select
    from dataclasses import replace
    c,r,_=valued;result=service().calculate(c,r)
    batch=staged(c,r,result);owner=storage.batch_view(c,r.tenant_id,batch)['items'][0]['attribution_id']
    payload=dict(component='OTHER_COST',amount=D('-10'),reason='Synthetic fee',sourceReference='OPS')
    request=request_component_change(c,r.tenant_id,batch,owner,ids['demo_user_account'],payload,str(uuid4()));actor=reviewer(c)
    new=staged(c,r,replace(result,input_hash='a'*64))
    assert c.scalar(select(t.amendment.c.status).where(t.amendment.c.request_id==request))=='STALE'
    assert approve_component_change(c,r.tenant_id,request,actor,'Base changed') is None
    assert c.scalar(select(t.amendment.c.status).where(t.amendment.c.request_id==request))=='STALE'
    owner=storage.batch_view(c,r.tenant_id,new)['items'][0]['attribution_id']
    request=request_component_change(c,r.tenant_id,new,owner,ids['demo_user_account'],payload,str(uuid4()))
    reject_component_change(c,r.tenant_id,request,actor,'Not justified')
    storage.publish(c,r.tenant_id,new,actor,'No outstanding changes')


def test_amendment_api_is_tenant_scoped_and_rejects_binary_float_amounts():
    from tests.test_composite_policy_api import call
    data=dict(attributionId=str(uuid4()),component='ADJUSTMENT',amount=1.1,reason='Synthetic',sourceReference='OPS')
    assert call('POST',f'/v1/valuation/batches/{uuid4()}/amendments',data,str(uuid4())).status_code==422
    data['amount']='1.1'
    assert call('POST',f'/v1/valuation/batches/{uuid4()}/amendments',data,str(uuid4())).status_code==404


def test_amended_candidate_retains_original_operator_independence(valued):
    from apps.reference_api.access_boundary import assert_independent_operator
    from security_master_schema import models as m
    from valuation.amendments import request_component_change,approve_component_change
    c,r,_=valued
    from valuation import tables as t
    from valuation.economics import evidence_hash,canonical_payload
    # A legacy attempt predates persisted real-operator STARTED evidence.
    attempt=c.scalar(t.attempt.insert().values(tenant_id=r.tenant_id,strategy_id=r.strategy_id,
        initiated_by=ids['demo_user_account'],request_key=str(uuid4()),
        request_hash=evidence_hash(dict(request=storage.request_identity(r),actor=ids['demo_user_account'])),
        request_payload=canonical_payload(storage.request_identity(r)),correlation_id=str(uuid4()),status='RUNNING')
        .returning(t.attempt.c.attempt_id))
    batch=storage.stage(c,attempt,ids['demo_user_account'],service().calculate(c,r))
    owner=storage.batch_view(c,r.tenant_id,batch)['items'][0]['attribution_id']
    operator=ids['platform_admin_user_account']
    request=request_component_change(c,r.tenant_id,batch,owner,ids['demo_user_account'],
        dict(component='ADJUSTMENT',amount=D('-10'),reason='Synthetic correction',sourceReference='OPS'),str(uuid4()),real_operator_id=operator)
    # Historical candidates use the pre-fix audit evidence; do not rewrite them.
    c.execute(m.access_audit_event.insert().values(tenant_id=r.tenant_id,actor_id=operator,
        subject_id=ids['demo_user_account'],action='TENANT_REQUEST',
        details={'resourceIds':[str(batch),str(request)],'permission':'VALUATION_RUN'}))
    revised=approve_component_change(c,r.tenant_id,request,reviewer(c),'Independent approval')
    with pytest.raises(PermissionError,match='real operator'):
        assert_independent_operator(c,r.tenant_id,operator,str(revised))


@pytest.mark.parametrize('decision',['approve','reject'])
def test_request_operator_cannot_review_by_switching_selected_user(valued,decision):
    from valuation.amendments import request_component_change,approve_component_change,reject_component_change
    c,r,_=valued
    batch=staged(c,r,service().calculate(c,r))
    owner=storage.batch_view(c,r.tenant_id,batch)['items'][0]['attribution_id']
    operator=ids['platform_admin_user_account']
    key=str(uuid4());payload=dict(component='ADJUSTMENT',amount=D('-10'),reason='Synthetic',sourceReference='OPS')
    request=request_component_change(c,r.tenant_id,batch,owner,ids['demo_user_account'],payload,key,real_operator_id=operator)
    assert request_component_change(c,r.tenant_id,batch,owner,ids['demo_user_account'],payload,key,real_operator_id=operator)==request
    with pytest.raises(ValueError,match='real operator'):
        request_component_change(c,r.tenant_id,batch,owner,ids['demo_user_account'],payload,key,real_operator_id=reviewer(c))
    decide=approve_component_change if decision=='approve' else reject_component_change
    with pytest.raises(PermissionError,match='real operator'):
        decide(c,r.tenant_id,request,reviewer(c),'Selected a different user',real_operator_id=operator)


def test_replacement_retains_calculator_and_requester_without_supplemental_audit(valued):
    from apps.reference_api.db import get_engine
    from valuation.amendments import request_component_change,approve_component_change
    from valuation import tables as t
    from sqlalchemy import select
    c,r,_=valued
    calculator=ids['platform_admin_user_account']
    key=str(uuid4())
    attempt=storage.begin_attempt(get_engine(),r,ids['demo_user_account'],key,real_operator_id=calculator)
    assert storage.begin_attempt(get_engine(),r,ids['demo_user_account'],key,real_operator_id=calculator)==attempt
    with pytest.raises(ValueError,match='real operator'):
        storage.begin_attempt(get_engine(),r,ids['demo_user_account'],key,real_operator_id=ids['demo_user_account'])
    original=storage.stage(c,attempt,ids['demo_user_account'],service().calculate(c,r))
    requester=reviewer(c);approver=reviewer(c)
    owner=storage.batch_view(c,r.tenant_id,original)['items'][0]['attribution_id']
    request=request_component_change(c,r.tenant_id,original,owner,ids['demo_user_account'],
        dict(component='ADJUSTMENT',amount=D('-10'),reason='Synthetic',sourceReference='OPS'),str(uuid4()),real_operator_id=requester)
    revised=approve_component_change(c,r.tenant_id,request,approver,'Independent amendment approval',real_operator_id=approver)
    assert approve_component_change(c,r.tenant_id,request,approver,'Retry approval',real_operator_id=approver)==revised
    for operator in (calculator,requester):
        with pytest.raises(PermissionError,match='real operator'):
            storage.publish(c,r.tenant_id,revised,reviewer(c),'Switched selected user',real_operator_id=operator)
    event=c.scalar(select(t.run_event.c.event_id).where(t.run_event.c.attempt_id==attempt,t.run_event.c.event_code=='STARTED'))
    with pytest.raises(Exception,match='immutable'):
        with c.begin_nested(): c.execute(t.run_event.update().where(t.run_event.c.event_id==event).values(details={}))
    storage.publish(c,r.tenant_id,revised,approver,'Independent publication',real_operator_id=approver)
    assert storage.batch_view(c,r.tenant_id,revised)['status']=='PUBLISHED'
    new_attempt=storage.batch_view(c,r.tenant_id,revised)['attempt_id']
    for code in ('AMENDMENT_APPROVED','PUBLISHED'):
        retained=c.scalar(select(t.run_event.c.details).where(t.run_event.c.attempt_id==new_attempt,t.run_event.c.event_code==code))
        assert retained['realOperatorId']==str(approver)
