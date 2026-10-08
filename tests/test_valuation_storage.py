"""Attribution review behaviour against disposable PostgreSQL."""
import importlib
from decimal import Decimal as D
from uuid import uuid4
import pytest
from sqlalchemy import select, func
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued, service

def store():
    try: return importlib.import_module('valuation.storage')
    except ModuleNotFoundError: pytest.fail('Attribution storage and review are not implemented')

def test_population_identity_is_order_independent_and_version_sensitive():
    k=store()
    assert k.population_hash([{'trade_id':'a','attribution_id':'1'},{'trade_id':'b','attribution_id':'2'}]) == k.population_hash([{'trade_id':'b','attribution_id':'2'},{'trade_id':'a','attribution_id':'1'}])
    assert k.population_hash([{'trade_id':'a','attribution_id':'1'}]) != k.population_hash([{'trade_id':'a','attribution_id':'2'}])

def test_identical_staging_is_idempotent_and_not_official(valued):
    c,request,_=valued;k=store();result=service().calculate(c,request)
    run=k.begin_attempt(get_engine(),request,ids['demo_user_account'],str(uuid4()))
    batch=k.stage(c,run,ids['demo_user_account'],result)
    assert k.stage(c,run,ids['demo_user_account'],result)==batch
    assert k.batch_view(c,request.tenant_id,batch)['status']=='STAGED'
    assert k.published(c,request.tenant_id,request.strategy_id,request.closing_cutoff.date())==[]

def test_publication_requires_independent_reviewer_and_retains_history(valued):
    c,request,_=valued;k=store();result=service().calculate(c,request)
    run=k.begin_attempt(get_engine(),request,ids['demo_user_account'],str(uuid4()))
    batch=k.stage(c,run,ids['demo_user_account'],result)
    with pytest.raises(ValueError,match='independent'): k.publish(c,request.tenant_id,batch,ids['demo_user_account'],'Reviewed')
    # Low-level workflow checks identity independence; API checks reviewer membership.
    reviewer=uuid4()
    c.execute(m.user_account.insert().values(user_account_id=reviewer,account_type='HUMAN',status='ACTIVE'))
    k.publish(c,request.tenant_id,batch,reviewer,'Inputs and bridge reviewed')
    official=k.published(c,request.tenant_id,request.strategy_id,request.closing_cutoff.date())
    assert len(official)==1 and official[0]['net_pnl']==D('109.877')
    assert k.batch_view(c,request.tenant_id,batch)['status']=='PUBLISHED'

def test_foreign_batch_is_opaque(valued):
    c,request,_=valued;k=store();result=service().calculate(c,request)
    run=k.begin_attempt(get_engine(),request,ids['demo_user_account'],str(uuid4()))
    batch=k.stage(c,run,ids['demo_user_account'],result)
    with pytest.raises(LookupError): k.batch_view(c,ids['second_tenant'],batch)


def test_changed_calendar_evidence_creates_a_new_attribution_version(valued):
    from market_data.calendar_store import publish_reference_calendar
    c,request,_=valued;k=store()
    first=service().calculate(c,request)
    run=k.begin_attempt(get_engine(),request,ids['demo_user_account'],str(uuid4()))
    batch=k.stage(c,run,ids['demo_user_account'],first)
    original=k.batch_view(c,request.tenant_id,batch)['items'][0]
    source=c.scalar(select(m.valuation_policy_rule.c.market_calendar_id).where(
        m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']))
    published=publish_reference_calendar(c,source,ids['platform_admin_user_account'],'Synthetic new calendar evidence')
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']).values(market_calendar_id=published))
    second=service().calculate(c,request)
    assert second.period.market_pnl==first.period.market_pnl
    run=k.begin_attempt(get_engine(),request,ids['demo_user_account'],str(uuid4()))
    replacement=k.stage(c,run,ids['demo_user_account'],second)
    revised=k.batch_view(c,request.tenant_id,replacement)['items'][0]
    assert revised['version']==original['version']+1
    assert revised['attribution_id']!=original['attribution_id']
    assert revised['evidence']['selections'][0]['pricing_evidence']['calendarEvidence']['calendarId']==str(published)

def test_financial_evidence_cannot_be_overwritten(valued):
    c,request,_=valued;k=store();result=service().calculate(c,request)
    run=k.begin_attempt(get_engine(),request,ids['demo_user_account'],str(uuid4()))
    batch=k.stage(c,run,ids['demo_user_account'],result)
    from valuation import tables as t
    attribution=k.batch_view(c,request.tenant_id,batch)['items'][0]['attribution_id']
    with pytest.raises(Exception,match='immutable'):
        with c.begin_nested(): c.execute(t.attribution.update().where(t.attribution.c.attribution_id==attribution).values(net_pnl=0))

def test_failure_attempt_survives_financial_rollback(valued):
    c,request,_=valued;k=store()
    run=k.begin_attempt(get_engine(),request,ids['demo_user_account'],str(uuid4()))
    k.fail_attempt(get_engine(),request.tenant_id,run,'INPUT_MISSING')
    from valuation import tables as t
    with get_engine().connect() as fresh:
        row=fresh.execute(select(t.attempt).where(t.attempt.c.attempt_id==run)).mappings().one()
        assert row['status']=='FAILED' and row['error_code']=='INPUT_MISSING'
        events=fresh.execute(select(t.run_event).where(t.run_event.c.attempt_id==run)).mappings().all()
        assert [event['event_code'] for event in events]==['STARTED','FAILED']

def test_stale_population_prevents_publication(valued):
    c,request,_=valued;k=store();result=service().calculate(c,request)
    run=k.begin_attempt(get_engine(),request,ids['demo_user_account'],str(uuid4()))
    first=k.stage(c,run,ids['demo_user_account'],result)
    # Stale base hash is tested through real publication, not mock call counts.
    from valuation import tables as t
    c.execute(t.batch.update().where(t.batch.c.batch_id==first).values(base_population_hash='0'*64))
    reviewer=uuid4();c.execute(m.user_account.insert().values(user_account_id=reviewer,account_type='HUMAN'))
    with pytest.raises(ValueError,match='changed'): k.publish(c,request.tenant_id,first,reviewer,'Reviewed')

def test_reused_batch_is_linked_in_new_attempt_operational_events(valued):
    c,request,_=valued;k=store();result=service().calculate(c,request)
    first=k.begin_attempt(get_engine(),request,ids['demo_user_account'],str(uuid4()))
    batch=k.stage(c,first,ids['demo_user_account'],result)
    second=k.begin_attempt(get_engine(),request,ids['demo_user_account'],str(uuid4()))
    assert k.stage(c,second,ids['demo_user_account'],result)==batch
    from valuation import tables as t
    events=c.execute(select(t.run_event).where(t.run_event.c.attempt_id==second).order_by(t.run_event.c.recorded_at)).mappings().all()
    assert events[-1]['event_code']=='COMPLETED'
    assert events[-1]['details']['batchId']==str(batch)


def test_incomplete_incremental_population_is_not_accepted(valued):
    c,request,_=valued;k=store();result=service().calculate(c,request)
    run=k.begin_attempt(get_engine(),request,ids['demo_user_account'],str(uuid4()))
    with pytest.raises(ValueError,match='authoritative'):
        k.stage(c,run,ids['demo_user_account'],result,mode='INCREMENTAL')


def test_publication_rechecks_summary_against_selected_evidence(valued):
    c,request,_=valued;k=store();result=service().calculate(c,request)
    run=k.begin_attempt(get_engine(),request,ids['demo_user_account'],str(uuid4()))
    batch=k.stage(c,run,ids['demo_user_account'],result)
    from valuation import tables as t
    summary=k.batch_view(c,request.tenant_id,batch)['summary']
    c.execute(t.batch.update().where(t.batch.c.batch_id==batch).values(summary=dict(summary,marketPnl='1')))
    reviewer=uuid4();c.execute(m.user_account.insert().values(user_account_id=reviewer,account_type='HUMAN'))
    with pytest.raises(ValueError,match='reconcile'):
        k.publish(c,request.tenant_id,batch,reviewer,'Reviewed')
