"""Real database work budgets: no authorization or financial-result shortcuts."""
from contextlib import contextmanager
from datetime import date, datetime, time, timezone, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import event, select, and_, or_, exists
import pytest
from tests.test_access_management import connection
from tests.test_valuation_service import valued
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from security_master_schema.governance_clock import governance_date


@contextmanager
def sql_reads(c):
    statements = []
    def record(conn, cursor, statement, parameters, context, executemany):
        if conn is c:
            statements.append((statement, parameters))
    event.listen(c.engine, 'after_cursor_execute', record)
    try:
        yield statements
    finally:
        event.remove(c.engine, 'after_cursor_execute', record)


def test_rights_sweep_is_batched_and_preserves_foreign_and_inactive_denials(connection):
    from market_data.rights import denied_activity_datasets
    c = connection
    owner = c.scalar(select(m.tenant.c.owning_organisation_id).where(m.tenant.c.tenant_id == ids['tenant']))
    created = set()
    for n in range(8):
        dataset = uuid4()
        created.add(dataset)
        c.execute(m.dataset.insert().values(dataset_id=dataset,provider_product_id=ids['provider_product'],
            dataset_code='QUERY_'+dataset.hex,display_name='Synthetic query test',data_domain='MARKET_DATA',
            valid_from=governance_date()-timedelta(days=1)))
        c.execute(m.dataset_access_profile.insert().values(dataset_id=dataset,licensee_organisation_id=owner,
            permitted_tenant_id=ids['second_tenant'] if n % 2 else ids['tenant'],usage_scope='PERSONAL',
            provider_enabled=True,activation_reference='Synthetic only',status='ACTIVE'))
    with sql_reads(c) as statements:
        denied = set(denied_activity_datasets(c,ids['tenant'],governance_date(),('DISPLAY','NON_DISPLAY')))
    assert created <= denied  # No reviewed requirements: never silently authorized.
    assert len(statements) <= 5


def test_candidate_lookup_constrains_observations_to_matching_series(valued):
    from valuation.service import calculate
    c, request, _ = valued
    with sql_reads(c) as statements:
        result = calculate(c, request)
    assert result.period.market_pnl == Decimal('109.877')
    candidates = [sql for sql, _ in statements
                  if 'FROM md.market_data_observation JOIN md.market_data_series' in sql]
    assert candidates
    # Protect the query boundary against returning to a dataset-wide scan before
    # the subject is known. Full result/rights semantics are covered separately.
    assert all('md.market_data_observation.market_data_series_id IN (' in sql for sql in candidates)


def test_instrument_market_data_detail_batches_latest_marks_per_series(valued):
    from apps.reference_api.repository import _load_market_data
    c,r,_=valued
    before=_load_market_data(c,r.tenant_id,[ids['hsbc_xlon_listing_node']])
    prototype=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one())
    points=[dict(row) for row in c.execute(select(m.market_data_observation).where(
        m.market_data_observation.c.market_data_series_id==ids['market_data_series'],
        m.market_data_observation.c.source_observation_key.like('VAL_%'))).mappings()]
    assert len(points)==2
    for _ in range(6):
        identity=uuid4()
        c.execute(m.market_data_series.insert().values(**(prototype|dict(market_data_series_id=identity))))
        c.execute(m.market_data_observation.insert(),[point|dict(market_data_observation_id=uuid4(),market_data_series_id=identity,
            source_observation_key='QUERY_'+uuid4().hex) for point in points])
    with sql_reads(c) as statements:
        result=_load_market_data(c,r.tenant_id,[ids['hsbc_xlon_listing_node']])
    assert len(result)==len(before)+12
    assert len(statements)<=6


def test_tenant_access_overview_batches_roster_but_keeps_per_user_authority(connection):
    from security_master_schema import access_management as am
    c = connection
    for n in range(5):
        group = am.save_group(c, ids['tenant'], ids['demo_user_account'],code='QUERY_'+uuid4().hex,
            name=f'Synthetic query group {n}',actions=['TRADE_READ'])
        user = am.add_user(c, ids['tenant'], ids['demo_user_account'],name=f'Synthetic query user {n}',role='MEMBER')
        am.set_user_groups(c, ids['tenant'], ids['demo_user_account'],user,[group])
    with sql_reads(c) as statements:
        view = am.tenant_access_view(c,ids['tenant'],ids['demo_user_account'])
    synthetic = [u for u in view['users'] if u['name'].startswith('Synthetic query user')]
    assert len(synthetic) == 5
    assert all(u['permissions'] == ['TRADE_READ'] for u in synthetic)
    active=sum(u['status']=='ACTIVE' and u['accountStatus']=='ACTIVE' for u in view['users'])
    assert len(statements) <= 15+5*active
    roster_queries=[sql for sql,_ in statements if sql.startswith('SELECT ten.access_group_grant.tenant_id')
        or sql.startswith('SELECT ten.access_group_strategy.tenant_id') or sql.startswith('SELECT ten.access_group_member.tenant_id')]
    assert len(roster_queries)==3


def test_access_overview_preserves_union_but_never_widens_action_strategy_scope(connection):
    from security_master_schema import access_management as am
    from security_master_schema.tenant_workspace import resolve_tenant_workspace, TenantActionForbidden
    from security_master_schema.strategy_access import require_strategy_action
    c=connection; tenant=ids['tenant']; admin=ids['demo_user_account']
    user=am.add_user(c,tenant,admin,name='Synthetic selected-scope trader')
    read=am.save_group(c,tenant,admin,code='QUERY_'+uuid4().hex,name='All read',actions=['TRADE_READ'])
    write=am.save_group(c,tenant,admin,code='QUERY_'+uuid4().hex,name='Selected write',actions=['TRADE_WRITE'],
        scope_mode='SELECTED',strategy_ids=[ids['strategy']])
    empty=am.save_group(c,tenant,admin,code='QUERY_'+uuid4().hex,name='Empty selected valuation',actions=['VALUATION_RUN'],
        scope_mode='SELECTED')
    am.set_user_groups(c,tenant,admin,user,[read,write,empty])
    expected=resolve_tenant_workspace(c,tenant,user,governance_date()).permission_codes
    view=am.tenant_access_view(c,tenant,admin)
    overview=next(row for row in view['users'] if row['userId']==str(user))
    assert set(overview['permissions'])==expected=={'TRADE_READ','TRADE_WRITE','VALUATION_RUN'}
    selected=next(g for g in view['groups'] if g['groupId']==str(write))
    assert selected['scopeMode']=='SELECTED' and selected['strategyIds']==[str(ids['strategy'])]
    require_strategy_action(c,tenant,user,'TRADE_WRITE',ids['strategy'])
    require_strategy_action(c,tenant,user,'TRADE_READ',ids['uk_fund_strategy'])
    with pytest.raises(TenantActionForbidden):
        require_strategy_action(c,tenant,user,'TRADE_WRITE',ids['uk_fund_strategy'])
    with pytest.raises(TenantActionForbidden):
        require_strategy_action(c,tenant,user,'VALUATION_RUN',ids['strategy'])


def test_history_projection_preserves_disclosure_and_batches_headers(valued):
    from apps.reference_api.db import get_engine
    from valuation import storage, tables as t
    from valuation.service import calculate
    from valuation.evidence_access import assert_batch_display
    c,r,_=valued
    result=calculate(c,r)
    attempt=storage.begin_attempt(get_engine(),r,ids['demo_user_account'],str(uuid4()))
    batch=storage.stage(c,attempt,ids['demo_user_account'],result)
    full=storage.batch_view(c,r.tenant_id,batch)
    with sql_reads(c) as statements:
        minimal=storage.batch_disclosure_views(c,r.tenant_id,[batch])[batch]
    assert len(statements)==2
    assert minimal['summary']==full['summary']
    assert minimal['items']==[{key:item[key] for key in ('position_key','evidence')} for item in full['items']]
    assert_batch_display(c,r.tenant_id,minimal)
    c.execute(m.tenant_dataset_entitlement.update().where(m.tenant_dataset_entitlement.c.tenant_id==r.tenant_id)
        .values(status='SUSPENDED'))
    with pytest.raises(PermissionError): assert_batch_display(c,r.tenant_id,minimal)
    assert storage.batch_disclosure_views(c,ids['second_tenant'],[batch])=={}


def test_batched_history_health_matches_detailed_health_and_detects_late_changes(valued):
    from apps.reference_api.db import get_engine
    from valuation import storage,tables as t
    from valuation.service import calculate
    from valuation.ledger_impacts import source_health, source_health_statuses
    c,r,trade=valued
    result=calculate(c,r)
    attempt=storage.begin_attempt(get_engine(),r,ids['demo_user_account'],str(uuid4()))
    batch=storage.stage(c,attempt,ids['demo_user_account'],result)
    header=dict(c.execute(select(t.batch).where(t.batch.c.batch_id==batch)).mappings().one())
    headers=[header,header|dict(batch_id=uuid4(),summary={}),header|dict(batch_id=uuid4(),summary={'ledgerSource':{'version':2}})]
    with sql_reads(c) as statements:
        actual=source_health_statuses(c,headers)
    assert len(statements)==1
    assert actual=={headers[0]['batch_id']:'CURRENT',headers[1]['batch_id']:'UNKNOWN_LEGACY',headers[2]['batch_id']:'UNKNOWN_LEGACY'}
    c.execute(t.ledger_change.insert().values(tenant_id=r.tenant_id,strategy_id=r.strategy_id,trade_id=trade,
        economic_from=r.closing_cutoff.date(),reason='Synthetic late change',actor_id=ids['demo_user_account'],
        revision=999,change_key='QUERY_'+uuid4().hex))
    actual=source_health_statuses(c,headers)
    assert actual[batch]==source_health(c,header)['status']=='REASSESSMENT_REQUIRED'


def test_catalogue_visibility_does_not_rescan_active_nodes_per_series(connection):
    from apps.reference_api import market_data_workspace as workspace
    c=connection
    prototype=dict(c.execute(select(m.financial_reference_node).where(
        m.financial_reference_node.c.reference_node_id==ids['hsbc_xlon_listing_node'])).mappings().one())
    series=dict(c.execute(select(m.market_data_series).where(
        m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one())
    nodes=[uuid4() for _ in range(200)]
    c.execute(m.financial_reference_node.insert(),[prototype|dict(reference_node_id=node,internal_code='QUERY_'+node.hex) for node in nodes])
    c.execute(m.market_data_series.insert(),[series|dict(market_data_series_id=uuid4(),reference_node_id=node) for node in nodes])
    # The owned fixture just multiplied both tables. Measure a representative
    # plan with truthful statistics, not the original tiny demo's row estimates.
    c.exec_driver_sql('ANALYZE secm.financial_reference_node')
    c.exec_driver_sql('ANALYZE md.market_data_series')
    with sql_reads(c) as statements:
        result=workspace.market_data_catalogue(c,ids['tenant'],'',governance_date(),25,0,'v1')
    assert result.meta.total>=200
    sql,parameters=statements[-1]
    plan=c.exec_driver_sql('EXPLAIN (ANALYZE, FORMAT JSON) '+sql,parameters).scalar_one()[0]['Plan']
    def node_work(plan):
        own=(plan.get('Actual Rows',0)+plan.get('Rows Removed by Filter',0))*plan.get('Actual Loops',0)
        return (own if plan.get('Relation Name')=='financial_reference_node' and plan['Node Type']=='Seq Scan' else 0)+sum(
            node_work(child) for child in plan.get('Plans',[]))
    assert node_work(plan)<2000


def test_forward_currency_lookup_is_once_per_pair_not_per_fill(valued):
    from tests.test_fx_forward_measure_inputs import book_more
    from tests.test_fx_maturity_service import setup
    from positions.contracts import ProjectionRequest
    from positions.holdings_repository import load_holdings_facts
    from positions.holdings import project_holdings
    from valuation.forward_measures import contractual_legs
    c,r,_=valued
    instrument,_,_,_=setup(c,r)
    for _ in range(4): book_more(c,r,instrument,'BUY','500000')
    request=ProjectionRequest(r.tenant_id,r.strategy_id,r.closing_cutoff,r.information_cutoff)
    facts,_=load_holdings_facts(c,request)
    bucket=next(b for b in project_holdings(facts,request).buckets if b.key.product_basis=='FX_FORWARD')
    with sql_reads(c) as statements:
        legs=contractual_legs(c,r,bucket)
    assert legs['baseAmount']==Decimal('3000000') and legs['quoteAmount']==Decimal('-3300000')
    currency_reads=[sql for sql,_ in statements if 'FROM secm.currency' in sql]
    assert len(currency_reads)==1


def test_forward_population_batches_proof_reads_and_rejects_different_request(valued):
    from dataclasses import replace
    from tests.test_fx_maturity_service import setup
    from positions.contracts import ProjectionRequest
    from positions.holdings_repository import load_holdings_facts
    from positions.holdings import project_holdings
    from valuation.forward_measures import contractual_legs,load_contract_bookings
    c,r,_=valued;setup(c,r)
    facts,_=load_holdings_facts(c,ProjectionRequest(r.tenant_id,r.strategy_id,r.closing_cutoff,r.information_cutoff))
    bucket=next(b for b in project_holdings(facts,ProjectionRequest(r.tenant_id,r.strategy_id,r.closing_cutoff,r.information_cutoff)).buckets
        if b.key.product_basis=='FX_FORWARD')
    expected=contractual_legs(c,r,bucket)
    with sql_reads(c) as statements:
        population=load_contract_bookings(c,r,[bucket,bucket])
        results=[contractual_legs(c,r,bucket,population=population) for _ in range(3)]
    assert results==[expected]*3
    assert len(statements)==3  # trades, BOOKED evidence and one currency pair.
    with pytest.raises(ValueError,match='scope'):
        contractual_legs(c,replace(r,information_cutoff=r.information_cutoff+timedelta(seconds=1)),bucket,population=population)


def test_platform_roster_queries_do_not_grow_per_tenant(connection):
    from security_master_schema.access_management import platform_view
    c=connection
    prototype=dict(c.execute(select(m.tenant).where(m.tenant.c.tenant_id==ids['tenant'])).mappings().one())
    created=[]
    for n in range(5):
        identity=uuid4();created.append(identity)
        c.execute(m.tenant.insert().values(**(prototype|dict(tenant_id=identity,tenant_code='QUERY_'+identity.hex,
            display_name=f'Synthetic query tenant {n}'))))
    with sql_reads(c) as statements:
        view=platform_view(c,ids['platform_admin_user_account'])
    assert set(map(str,created))<={row['tenantId'] for row in view['tenants']}
    assert all(not row['moduleCodes'] and not row['users'] for row in view['tenants'] if row['tenantId'] in set(map(str,created)))
    assert len(statements)==6


def test_forward_proof_batch_size_is_not_a_total_history_cap(valued):
    from tests.test_fx_maturity_service import setup
    from positions.contracts import ProjectionRequest
    from positions.holdings_repository import load_holdings_facts
    from positions.holdings import project_holdings
    from valuation.forward_measures import contractual_legs
    c,r,_=valued
    instrument,_,_,_=setup(c,r)
    trade=dict(c.execute(select(m.trade).where(m.trade.c.strategy_id==r.strategy_id,
        m.trade.c.trade_subject_reference_node_id==instrument)).mappings().one())
    booked=dict(c.execute(select(m.trade_lifecycle_event).where(
        m.trade_lifecycle_event.c.trade_id==trade['trade_id'],m.trade_lifecycle_event.c.event_type=='BOOKED')).mappings().one())
    identities=[uuid4() for _ in range(501)]
    c.execute(m.trade.insert(),[trade|dict(trade_id=identity) for identity in identities])
    c.execute(m.trade_lifecycle_event.insert(),[booked|dict(trade_lifecycle_event_id=uuid4(),trade_id=identity) for identity in identities])
    request=ProjectionRequest(r.tenant_id,r.strategy_id,r.closing_cutoff,r.information_cutoff)
    facts,_=load_holdings_facts(c,request)
    bucket=next(b for b in project_holdings(facts,request).buckets if b.key.product_basis=='FX_FORWARD')
    assert len(bucket.trade_ids)==502
    with sql_reads(c) as statements:
        legs=contractual_legs(c,r,bucket)
    assert legs['baseAmount']==Decimal('502000000') and legs['quoteAmount']==Decimal('-552200000')
    assert len(legs['bookings'])==502
    assert len(statements)==5


def test_holdings_definition_lookups_are_batched_without_dropping_facts(valued):
    import json
    from positions.contracts import ProjectionRequest
    from positions.holdings_repository import load_holdings_facts
    c,r,trade=valued
    prototype=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    event_row=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade)).mappings().one())
    payload=json.loads(event_row['event_payload'])
    definition=dict(c.execute(select(m.instrument_definition_version).where(
        m.instrument_definition_version.c.instrument_definition_version_id==payload['instrumentDefinitionId'])).mappings().one())
    for n in range(5):
        identity=uuid4();definition_id=uuid4()
        day=date(2025,1,1)+timedelta(days=n)
        execution=datetime.combine(day,time(10),timezone.utc)
        c.execute(m.instrument_definition_version.insert().values(**(definition|dict(
            instrument_definition_version_id=definition_id,sequence_no=1000+n,is_current=False,
            effective_from=day,effective_to=day))))
        c.execute(m.trade.insert().values(**(prototype|dict(trade_id=identity,trade_datetime_utc=execution,
            valuation_effective_date=day,valuation_date_basis='UTC_TRADE_DATE'))))
        c.execute(m.trade_lifecycle_event.insert().values(**(event_row|dict(trade_lifecycle_event_id=uuid4(),trade_id=identity,
            event_datetime_utc=execution,event_payload=json.dumps(payload|dict(instrumentDefinitionId=str(definition_id)))))))
    request=ProjectionRequest(r.tenant_id,r.strategy_id,r.closing_cutoff,r.information_cutoff)
    with sql_reads(c) as statements:
        facts,descriptions=load_holdings_facts(c,request)
    assert len(facts)==len(descriptions)==6
    assert all(fact.booking.product_basis=='EQUITY' for fact in facts)
    reads=[sql for sql,_ in statements if 'FROM secm.instrument_type JOIN secm.instrument_definition_version' in sql]
    assert len(reads)==1


def test_active_node_set_preserves_subject_and_listing_parent_visibility(connection):
    from apps.reference_api.repository import _market_data_visible_node_clause
    c=connection;subject=ids['hsbc_xlon_listing_node'];parent=ids['hsbc_instrument_node']
    def legacy_exists(reference,tenant):
        def direct(identity,suffix):
            scope=m.reference_node_scope.alias('proof_scope_'+suffix)
            node=m.financial_reference_node.alias('proof_node_'+suffix)
            return and_(exists(select(1).where(node.c.reference_node_id==identity,node.c.status=='ACTIVE')),
                or_(~exists(select(1).where(scope.c.reference_node_id==identity)),
                    exists(select(1).where(scope.c.reference_node_id==identity,scope.c.status=='ACTIVE',
                        or_(scope.c.scope_type=='SHARED_CANONICAL',and_(scope.c.scope_type=='TENANT_PRIVATE',scope.c.owner_tenant_id==tenant))))))
        listing=m.listing.alias('proof_listing')
        return and_(direct(reference,'subject'),~exists(select(1).where(listing.c.listing_node_id==reference,
            ~direct(listing.c.instrument_node_id,'parent'))))
    def visible(predicate,tenant):
        return set(c.scalars(select(m.financial_reference_node.c.reference_node_id).where(
            predicate(m.financial_reference_node.c.reference_node_id,tenant))))
    # Both boundaries vary independently: a shared listing never exposes its
    # foreign/private or inactive parent. No scopes remains legacy-visible.
    variants=[None,('SHARED_CANONICAL',None,'ACTIVE'),('TENANT_PRIVATE',ids['tenant'],'ACTIVE'),
        ('TENANT_PRIVATE',ids['second_tenant'],'ACTIVE'),('SHARED_CANONICAL',None,'RETIRED'),
        ('RESTRICTED_SHARED',ids['tenant'],'ACTIVE')]
    for subject_scope in variants:
        for parent_scope in variants:
            with c.begin_nested():
                for identity,scope in ((subject,subject_scope),(parent,parent_scope)):
                    c.execute(m.reference_node_scope.delete().where(m.reference_node_scope.c.reference_node_id==identity))
                    if scope:
                        c.execute(m.reference_node_scope.insert().values(reference_node_id=identity,scope_type=scope[0],
                            owner_tenant_id=scope[1],status=scope[2]))
                for tenant in (ids['tenant'],ids['second_tenant']):
                    expected=visible(legacy_exists,tenant)
                    assert visible(_market_data_visible_node_clause,tenant)==expected
    c.execute(m.financial_reference_node.update().where(m.financial_reference_node.c.reference_node_id==parent).values(status='RETIRED'))
    for tenant in (ids['tenant'],ids['second_tenant']):
        expected=visible(legacy_exists,tenant)
        assert subject not in expected
        assert visible(_market_data_visible_node_clause,tenant)==expected


def test_market_data_visibility_preserves_literal_uuid_policy_callers(connection):
    from apps.reference_api.repository import _market_data_visible_node_clause
    c=connection;subject=ids['hsbc_xlon_listing_node']
    assert c.scalar(select(1).where(_market_data_visible_node_clause(subject,ids['tenant'])))==1
    c.execute(m.reference_node_scope.delete().where(m.reference_node_scope.c.reference_node_id==subject))
    c.execute(m.reference_node_scope.insert().values(reference_node_id=subject,
        scope_type='TENANT_PRIVATE',owner_tenant_id=ids['second_tenant']))
    assert c.scalar(select(1).where(_market_data_visible_node_clause(subject,ids['tenant']))) is None
    assert c.scalar(select(1).where(_market_data_visible_node_clause(subject,ids['second_tenant'])))==1


def test_catalogue_query_budget_is_no_worse_than_previous_rights_loader(connection,monkeypatch):
    from apps.reference_api import market_data_workspace as workspace
    from tests.test_api_reference_authority import request
    from market_data.rights import load_rights
    c=connection
    with sql_reads(c) as statements:
        response=request(c,'GET','/v1/market-data/catalogue?limit=25')
    assert response.status_code==200,response.text
    actual=len(statements)
    def previous(c,tenant,on_date):
        profiles=c.execute(select(m.dataset_access_profile)).mappings().all()
        return [p['dataset_id'] for p in profiles if p['permitted_tenant_id'] not in (None,tenant)
            or not load_rights(c,p['dataset_id'],'DISPLAY',on_date).allowed]
    monkeypatch.setattr(workspace,'denied_display_datasets',previous)
    with sql_reads(c) as statements:
        old=request(c,'GET','/v1/market-data/catalogue?limit=25')
    assert old.status_code==200,old.text
    assert old.json()['data']==response.json()['data']
    print(f'catalogue complete HTTP SQL: previous={len(statements)}, optimized={actual}')
    assert actual<=len(statements)
