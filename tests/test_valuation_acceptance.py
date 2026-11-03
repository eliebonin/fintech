"""Successful HTTP calculation/retry/review on an independently owned database."""
import asyncio
from dataclasses import asdict,replace
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from httpx import AsyncClient,ASGITransport as RawTransport
from tests.api_client import FixtureASGITransport as ASGITransport
from sqlalchemy import create_engine,text,select,event
from security_master_schema import models as m
from sqlalchemy.engine import make_url
from apps.reference_api.main import create_app
from apps.reference_api.config import Settings
from security_master_schema.governance_clock import governance_date
from security_master_schema.demo_data import DEMO_IDS as ids,load_demo_data


def test_successful_http_calculation_retry_and_self_review_guard(monkeypatch):
    base=make_url(os.environ['DATABASE_URL'])
    assert base.database.startswith('platform_isolated_tests_')
    name='platform_isolated_tests_'+uuid4().hex
    admin=create_engine(base.set(database='postgres'),isolation_level='AUTOCOMMIT')
    with admin.connect() as c: c.execute(text(f'CREATE DATABASE "{name}"'))
    target=base.set(database=name);engine=create_engine(target)
    database_errors=[]
    setup=None
    def capture_error(context):
        exception=context.original_exception
        database_errors.append((getattr(exception,'sqlstate',None),getattr(getattr(exception,'diag',None),'message_primary',None)))
    event.listen(engine,'handle_error',capture_error)
    try:
        subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=Path(__file__).resolve().parents[1],
            env=dict(os.environ,DATABASE_URL=target.render_as_string(hide_password=False)),check=True,capture_output=True)
        load_demo_data(engine)
        from tests import test_valuation_service as fixture
        monkeypatch.setattr(fixture,'get_engine',lambda:engine)
        setup=fixture.valued.__wrapped__()
        c,request,trade=next(setup)
        c.commit()  # Only this child database contains committed mock financial rows.
        # Keep the fixture alive: closing it restores its original policy rule.
        # The API calculation must still see the synthetic RAW/session policy.
        payload=dict(strategyId=str(request.strategy_id),policyId=str(request.policy_id),cutId=str(request.cut_id),
            reportingCurrencyId=str(request.reporting_currency_id),openingCutoff=request.opening_cutoff.isoformat(),
            closingCutoff=request.closing_cutoff.isoformat(),informationCutoff=request.information_cutoff.isoformat())
        app=create_app(engine=engine);key=str(uuid4())
        from security_master_schema.access_management import add_user,save_group,set_user_groups
        with engine.begin() as c:
            reviewer=add_user(c,ids['tenant'],ids['demo_user_account'],name='Independent reviewer',role='TENANT_ADMIN')
            # An independent local operator is an explicit fixture identity,
            # not a caller-supplied header or an implicit tenant-admin privilege.
            c.execute(m.platform_user_account.insert().values(user_account_id=reviewer,
                platform_role='PLATFORM_ADMIN',status='ACTIVE',valid_from=governance_date()))
            group=save_group(c,ids['tenant'],ids['demo_user_account'],code='REVIEW_'+uuid4().hex,
                name='Synthetic independent review',actions=['VALUATION_READ','VALUATION_REVIEW','MARKET_DATA_READ'],scope_mode='ALL')
            set_user_groups(c,ids['tenant'],ids['demo_user_account'],reviewer,[group])
        independent_key='synthetic-independent-local-operator-bootstrap-key'
        independent_app=create_app(engine=engine,settings=replace(Settings.from_environment(),
            local_operator_id=reviewer,local_operator_key=independent_key))
        headers={'X-Tenant-Id':str(ids['tenant']),'X-User-Account-Id':str(ids['demo_user_account']),'Idempotency-Key':key}
        async def acceptance():
            async with AsyncClient(transport=RawTransport(app=independent_app),base_url='http://test') as operator:
                login=await operator.post('/v1/local-session',headers={'X-Local-Operator-Key':independent_key,
                    'X-User-Account-Id':str(reviewer)},json={'tenantId':str(ids['tenant']),'userId':str(reviewer)})
                assert login.status_code==201,login.text
                independent_token=login.json()['token']
            async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
                operator_headers={'X-User-Account-Id':str(ids['platform_admin_user_account']),
                    'X-Local-Operator-Key':os.environ['LOCAL_ACCESS_OPERATOR_KEY']}
                session=await client.post('/v1/local-session',headers=operator_headers,
                    json={'tenantId':str(ids['tenant']),'userId':str(ids['demo_user_account'])})
                assert session.status_code==201,session.text
                headers['X-Local-Access-Token']=session.json()['token']
                first,concurrent=await asyncio.gather(*[
                    client.post('/v1/valuation/attempts',json=payload,headers=headers) for _ in range(2)])
                if first.status_code in (409,429):
                    first,concurrent=concurrent,first
                if first.status_code!=201:
                    from valuation import tables as v
                    with engine.connect() as evidence:
                        failed=evidence.scalar(select(v.attempt.c.attempt_id).where(v.attempt.c.request_key==key))
                        reasons=list(evidence.scalars(select(v.run_event.c.details).where(v.run_event.c.attempt_id==failed)))
                    pytest_message=f'{first.text}; runEvidence={reasons}; databaseErrors={database_errors}'
                else:pytest_message=first.text
                assert first.status_code==201,pytest_message
                assert concurrent.status_code in (201,409,429),f'{concurrent.text}; databaseErrors={database_errors}'
                if concurrent.status_code==201:
                    assert concurrent.json()['attempt']['attempt_id']==first.json()['attempt']['attempt_id']
                elif concurrent.status_code==429:
                    assert concurrent.json()['code']=='workload.busy' and concurrent.json()['notStarted'] is True
                    assert concurrent.headers['Retry-After']=='5'
                    retried=await client.post('/v1/valuation/attempts',json=payload,headers=headers)
                    assert retried.status_code==201,retried.text
                    assert retried.json()['attempt']['attempt_id']==first.json()['attempt']['attempt_id']
                else:
                    assert concurrent.json()['code']=='valuation.in_progress'
                result=first.json();batch=result['batch'];attempt=result['attempt']['attempt_id']
                assert result['attempt']['status']=='COMPLETED'
                assert batch['status']=='STAGED' and batch['summary']['marketPnl']=='109.877'
                assert batch['summary']['externalComparison']=='NOT_COMPARED'
                assert batch['summary']['resultFormat']=='POSITION_V2'
                assert len(batch['items'])==1 and batch['items'][0]['trade_id'] is None
                assert batch['items'][0]['subject_id']==str(ids['hsbc_xlon_listing_node'])
                assert batch['items'][0]['lineage'][0]['trade_id']==str(trade)
                retry=await client.post('/v1/valuation/attempts',json=payload,headers=headers)
                assert retry.status_code==201,retry.text
                assert retry.json()['attempt']['attempt_id']==attempt
                assert retry.json()['batch']['batch_id']==batch['batch_id']
                detail=await client.get('/v1/valuation/attempts/'+attempt,headers=headers)
                assert detail.status_code==200 and detail.json()['events'][-1]['event_code']=='COMPLETED'
                path='/v1/valuation/batches/'+batch['batch_id']
                explanation=await client.post(path+'/explanations',json={'comment':'Synthetic input bridge reviewed'},headers=headers)
                assert explanation.status_code==200,explanation.text
                denied=await client.post(path+'/publish',json={'comment':'Self-review is forbidden'},headers=headers)
                assert denied.status_code==403 and 'independent' in denied.text.lower()
                change=await client.post(path+'/amendments',headers=headers|{'Idempotency-Key':str(uuid4())},json={
                    'attributionId':batch['items'][0]['attribution_id'],'component':'ADJUSTMENT','amount':'-10',
                    'reason':'Synthetic adjustment','sourceReference':'OPS'})
                assert change.status_code==201,change.text
                amendment=change.json()['requestId']
                switched=await client.post('/v1/local-session',headers=operator_headers|{'X-Local-Access-Token':headers['X-Local-Access-Token']},
                    json={'tenantId':str(ids['tenant']),'userId':str(reviewer)})
                assert switched.status_code==201,switched.text
                switched_headers=headers|{'X-User-Account-Id':str(reviewer),'X-Local-Access-Token':switched.json()['token']}
                decision='/v1/valuation/amendments/'+amendment+'/approve'
                denied=await client.post(decision,headers=switched_headers,json={'comment':'Same operator, different selected user'})
                assert denied.status_code==403,denied.text
                independent={'X-Tenant-Id':str(ids['tenant']),'X-User-Account-Id':str(reviewer),
                    'X-Local-Access-Token':independent_token}
                approved=await client.post(decision,headers=independent,json={'comment':'Independent review of adjustment'})
                assert approved.status_code==200,approved.text
                revised=approved.json()['batch']['batch_id']
                revised_path='/v1/valuation/batches/'+revised+'/publish'
                denied=await client.post(revised_path,headers=switched_headers,json={'comment':'Original operator tries amended candidate'})
                assert denied.status_code==403 and 'real operator' in denied.text,denied.text
                published=await client.post(revised_path,headers=independent,json={'comment':'Independent publication'})
                assert published.status_code==200,published.text
                assert published.json()['status']=='PUBLISHED' and published.json()['summary']['netPnl']=='99.877'
                restored=await client.post('/v1/local-session',headers=operator_headers|{'X-Local-Access-Token':switched.json()['token']},
                    json={'tenantId':str(ids['tenant']),'userId':str(ids['demo_user_account'])})
                assert restored.status_code==201,restored.text
                headers['X-Local-Access-Token']=restored.json()['token']
                # Calculation authority is not perpetual display authority.
                with engine.begin() as c:
                    c.execute(m.licence_activity_grant.update().where(m.licence_activity_grant.c.activity=='DISPLAY',
                        m.licence_activity_grant.c.dataset_licence_assignment_id.in_(select(m.dataset_licence_assignment.c.dataset_licence_assignment_id)
                            .where(m.dataset_licence_assignment.c.dataset_id==ids['dataset']))).values(status='SUSPENDED'))
                restricted=await client.get('/v1/valuation/attempts/'+attempt,headers=headers)
                assert restricted.status_code==200,restricted.text
                safe=restricted.json()
                assert safe['attempt']['status']=='COMPLETED'
                assert safe['batch']['items']==[] and safe['batch']['summary']['evidenceAccess']=='DENIED'
                assert '109.877' not in restricted.text and 'selected_value' not in restricted.text
                retry=await client.post('/v1/valuation/attempts',json=payload,headers=headers)
                assert retry.status_code==201 and retry.json()['batch']['summary']['evidenceAccess']=='DENIED'
                for action in ['explanations','publish']:
                    forbidden=await client.post(path+'/'+action,json={'comment':'Restricted review'},headers=headers)
                    assert forbidden.status_code==403,forbidden.text
                snapshot=batch['items'][0]['evidence']['resolutionSnapshotIds'][0]
                hidden=await client.get('/v1/market-data-resolution-snapshots/'+snapshot,headers=headers)
                assert hidden.status_code==403,hidden.text
        asyncio.run(acceptance())
    finally:
        if setup is not None:setup.close()
        engine.dispose()
        assert name.startswith('platform_isolated_tests_') and len(name.rsplit('_',1)[1])==32
        with admin.connect() as c: c.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()
