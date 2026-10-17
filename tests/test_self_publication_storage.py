from datetime import datetime,timedelta,timezone
from uuid import uuid4
from decimal import Decimal
import pytest
from sqlalchemy import select
from tests.test_valuation_service import valued,service
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from valuation import storage as k,tables as t

def staged(valued):
    c,request,_=valued
    result=service().calculate(c,request)
    run=k.begin_attempt(get_engine(),request,ids['demo_user_account'],str(uuid4()))
    return c,request,k.stage(c,run,ids['demo_user_account'],result),run

def allow(c,tenant,expiry=None):
    c.execute(t.publication_policy.insert().values(tenant_id=tenant,revision=1,enabled=True,
        valid_until=expiry,reason='Synthetic single-person operations',updated_by=ids['demo_user_account']))
    group=c.scalar(select(m.access_group_grant.c.group_id).join(m.access_group_member,
        (m.access_group_member.c.group_id==m.access_group_grant.c.group_id)&(m.access_group_member.c.tenant_id==tenant))
        .where(m.access_group_grant.c.tenant_id==tenant,m.access_group_grant.c.action_code=='VALUATION_REVIEW',
               m.access_group_member.c.user_account_id==ids['demo_user_account']).limit(1))
    c.execute(m.access_group_grant.insert().values(tenant_id=tenant,group_id=group,action_code='VALUATION_SELF_PUBLISH'))

def test_missing_opt_in_does_not_waive_independent_review(valued):
    c,request,batch,_=staged(valued)
    with pytest.raises(PermissionError,match='disabled'):
        k.publish(c,request.tenant_id,batch,ids['demo_user_account'],'Single-person desk',self_publication=True)

def test_self_publication_records_its_mode_permission_and_policy_evidence(valued):
    c,request,batch,run=staged(valued);allow(c,request.tenant_id)
    k.publish(c,request.tenant_id,batch,ids['demo_user_account'],'Single-person desk',self_publication=True)
    view=k.batch_view(c,request.tenant_id,batch)
    assert view['status']=='PUBLISHED' and view['publicationReviewMode']=='SELF_REVIEWED'
    evidence=c.execute(select(t.run_event.c.details).where(t.run_event.c.attempt_id==run,t.run_event.c.event_code=='PUBLISHED')).scalar_one()
    assert evidence['reviewMode']=='SELF_REVIEWED' and evidence['policyRevision']==1
    assert evidence['permission']=='VALUATION_SELF_PUBLISH' and evidence['realOperatorId']==str(ids['demo_user_account'])
    assert view['reviews'][-1]['action']=='SELF_PUBLISHED'

def test_expired_cover_is_rejected(valued):
    c,request,batch,_=staged(valued);allow(c,request.tenant_id,datetime.now(timezone.utc)-timedelta(hours=1))
    with pytest.raises(PermissionError,match='expired'):
        k.publish(c,request.tenant_id,batch,ids['demo_user_account'],'Holiday cover',self_publication=True)

def test_impersonation_does_not_manufacture_real_operator_authority(valued):
    c,request,batch,_=staged(valued);allow(c,request.tenant_id)
    with pytest.raises(PermissionError):
        k.publish(c,request.tenant_id,batch,ids['demo_user_account'],'Selected identity',self_publication=True,real_operator_id=ids['platform_admin_user_account'])

def test_self_publication_still_blocks_pending_amendments(valued):
    from valuation.amendments import request_component_change
    c,request,batch,_=staged(valued);allow(c,request.tenant_id)
    item=k.batch_view(c,request.tenant_id,batch)['items'][0]
    request_component_change(c,request.tenant_id,batch,item['attribution_id'],ids['demo_user_account'],
        {'component':'ADJUSTMENT','amount':Decimal('1'),'reason':'Synthetic fee','sourceReference':'TEST'},uuid4().hex)
    with pytest.raises(ValueError,match='pending'):
        k.publish(c,request.tenant_id,batch,ids['demo_user_account'],'Pending fee',self_publication=True)
