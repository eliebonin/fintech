"""Focused metadata reads on disposable PostgreSQL, not operating data."""
from copy import deepcopy
from uuid import uuid4
from sqlalchemy import select
from apps.reference_api.db import get_engine
from apps.reference_api.valuation_presentation import decorate_batch
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued,service


def add_isin(c,node,value,*,primary=True,valid_from=None,valid_to=None):
    scheme=c.scalar(select(m.identifier_scheme.c.identifier_scheme_id).where(m.identifier_scheme.c.scheme_code=='ISIN'))
    c.execute(m.financial_reference_identifier.insert().values(reference_node_id=node,identifier_scheme_id=scheme,
        identifier_value=value,is_primary=primary,valid_from=valid_from,valid_to=valid_to))


def test_bond_labels_prefer_current_primary_isin_over_internal_import_code():
    from datetime import date
    engine=get_engine(); assert engine.url.database.startswith('platform_isolated_tests_')
    with engine.connect() as c:
        node=ids['bond_instrument_node']
        c.execute(m.financial_reference_node.update().where(m.financial_reference_node.c.reference_node_id==node).values(
            canonical_name='Example government bill',internal_code='IMPORT_BOND_20828'))
        add_isin(c,node,'GB00BSGRV302')
        add_isin(c,node,'GB00B1234567',primary=False)
        add_isin(c,node,'GB00B7654321',valid_to=date(2000,1,1))
        add_isin(c,node,'GB00B9999999',valid_from=date(2999,1,1))
        batch={'batch_id':uuid4(),'summary':{},'items':[{'subject_id':node,'components':{},'evidence':{}}]}
        before=deepcopy(batch)
        result=decorate_batch(c,ids['tenant'],batch)
        assert result['presentation']['instrumentDisplays'][str(node)]['primaryName']=='Example government bill'
        assert result['presentation']['instrumentDisplays'][str(node)]['identifier']==dict(scheme='ISIN',value='GB00BSGRV302')
        assert 'IMPORT_BOND' not in result['presentation']['references'][str(node)]
        assert batch==before


def test_bond_listing_inherits_parent_isin_without_losing_listing_identity():
    engine=get_engine(); assert engine.url.database.startswith('platform_isolated_tests_')
    with engine.connect() as c:
        node=ids['hsbc_xlon_listing_node'];parent=ids['bond_instrument_node']
        c.execute(m.listing.update().where(m.listing.c.listing_node_id==node).values(instrument_node_id=parent,trading_symbol='SYNTHETIC_BILL'))
        add_isin(c,parent,'GB00BSGRV302')
        batch={'batch_id':uuid4(),'summary':{},'items':[{'subject_id':node,'components':{},'evidence':{}}]}
        result=decorate_batch(c,ids['tenant'],batch)
        assert 'GB00BSGRV302' in result['presentation']['references'][str(node)]
        assert 'SYNTHETIC_BILL' not in result['presentation']['references'][str(node)]
        assert result['presentation']['instrumentTypes'][str(node)]['code']=='BOND'
        # The displayed label and instrument link still belong to the listing.
        assert str(parent) not in result['presentation']['references']


def test_equity_listing_keeps_ticker_and_missing_bond_isin_does_not_promote_internal_code():
    engine=get_engine(); assert engine.url.database.startswith('platform_isolated_tests_')
    with engine.connect() as c:
        stock=ids['hsbc_xlon_listing_node'];bond=ids['bond_instrument_node']
        add_isin(c,ids['hsbc_instrument_node'],'GB00B1234567')
        batch={'batch_id':uuid4(),'summary':{},'items':[{'subject_id':node,'components':{},'evidence':{}} for node in [stock,bond]]}
        names=decorate_batch(c,ids['tenant'],batch)['presentation']['references']
        symbol=c.scalar(select(m.listing.c.trading_symbol).where(m.listing.c.listing_node_id==stock))
        assert symbol in names[str(stock)] and 'GB00B1234567' not in names[str(stock)]
        assert 'Platform Demo 3.25% 2031 Note' in names[str(bond)]
        assert 'BOND_DEMO_2031' not in names[str(bond)]


def test_projection_labels_full_population_without_rewriting_evidence():
    engine=get_engine(); assert engine.url.database.startswith('platform_isolated_tests_')
    with engine.connect() as c:
        node=c.execute(select(m.financial_reference_node).where(m.financial_reference_node.c.status=='ACTIVE')).mappings().first()
        nodes=[dict(reference_node_id=uuid4(),reference_node_type_id=node['reference_node_type_id'],
            canonical_name='Same instrument name',internal_code=f'OPS-{uuid4().hex}',status='ACTIVE',is_tradable=False) for _ in range(27)]
        c.execute(m.financial_reference_node.insert(),nodes)
        batch={'batch_id':uuid4(),'staged_by':ids['demo_user_account'],'reviews':[],
            'summary':{'reportingCurrencyId':str(ids['gbp_currency'])},'items':[
            {'subject_id':record['reference_node_id'],'components':{'PRICE':'1','ACCRUAL':'0.123456789012'},'evidence':{}} for record in nodes]}
        before=deepcopy(batch)
        result=decorate_batch(c,ids['tenant'],batch)
        assert len(result['items'])==27
        assert result['presentation']['currencies'][str(ids['gbp_currency'])]=='GBP'
        assert result['presentation']['totals']['interest']=='3.333333303324'
        assert result['presentation']['pendingAmendments']==0
        assert len(result['presentation']['references'])==27
        # Same-name rows remain distinct by exact identity; internal codes are
        # searchable metadata, not mandatory business labels.
        assert len(set(result['presentation']['references'].values()))==1
        assert all(row['identifier'] is None for row in result['presentation']['instrumentDisplays'].values())
        assert str(nodes[-1]['reference_node_id']) in result['presentation']['references']
        assert batch==before


def test_restricted_batch_never_resolves_or_adds_labels():
    batch={'summary':{'evidenceAccess':'DENIED'}}
    assert decorate_batch(None,ids['tenant'],batch)==batch


def test_private_parent_labels_do_not_cross_tenants():
    engine=get_engine(); assert engine.url.database.startswith('platform_isolated_tests_')
    with engine.connect() as c, c.begin():
        listing=c.execute(select(m.listing)).mappings().first()
        # Test transaction only; rollback below restores the disposable seed.
        c.execute(m.reference_node_scope.delete().where(m.reference_node_scope.c.reference_node_id==listing['instrument_node_id']))
        c.execute(m.reference_node_scope.insert().values(reference_node_id=listing['instrument_node_id'],
            scope_type='TENANT_PRIVATE',owner_tenant_id=ids['second_tenant'],status='ACTIVE'))
        batch={'batch_id':uuid4(),'summary':{},'items':[{'subject_id':listing['listing_node_id'],'evidence':{},'components':{}}]}
        result=decorate_batch(c,ids['tenant'],batch)
        assert str(listing['listing_node_id']) not in result['presentation']['references']
        assert str(listing['listing_node_id']) not in result['presentation']['instrumentTypes']
        c.rollback()


def test_instrument_types_use_canonical_parents_without_mutating_stored_financials():
    engine=get_engine(); assert engine.url.database.startswith('platform_isolated_tests_')
    with engine.connect() as c:
        subjects=[ids['hsbc_xlon_listing_node'],ids['hsbc_instrument_node'],ids['bond_instrument_node'],ids['gbp_currency']]
        batch={'batch_id':uuid4(),'summary':{},'items':[
            {'subject_id':subject,'components':{'PRICE':'1'},'evidence':{}} for subject in subjects]}
        before=deepcopy(batch)
        result=decorate_batch(c,ids['tenant'],batch)
        types=result['presentation']['instrumentTypes']
        assert types[str(ids['hsbc_xlon_listing_node'])]==types[str(ids['hsbc_instrument_node'])]
        assert types[str(ids['hsbc_xlon_listing_node'])]['code']=='EQUITY'
        assert types[str(ids['hsbc_xlon_listing_node'])]['label']
        assert types[str(ids['bond_instrument_node'])]['code']=='BOND'
        assert str(ids['gbp_currency']) not in types
        assert batch==before


def test_real_staged_evidence_gets_dataset_and_rule_labels_without_financial_changes(valued):
    from valuation import storage
    c,request,_=valued
    result=service().calculate(c,request)
    attempt=storage.begin_attempt(get_engine(),request,ids['demo_user_account'],str(uuid4()))
    batch_id=storage.stage(c,attempt,ids['demo_user_account'],result)
    batch=storage.batch_view(c,request.tenant_id,batch_id)
    before=deepcopy(batch)
    projected=decorate_batch(c,request.tenant_id,batch)
    assert projected['presentation']['datasets']
    assert projected['presentation']['rules']
    assert projected['presentation']['references']
    coverage=projected['presentation']['sourceCoverage']
    assert coverage['reconciliation']=='MATCH'
    assert coverage['recordedNet']==before['summary']['netPnl']
    assert next(row for row in coverage['rows'] if row['code']=='CASH_BALANCE_FX')['amount'] is None
    assert projected['summary']==before['summary']
    for original,presented in zip(before['items'],projected['items']):
        assert original['components']==presented['components']
        assert original['evidence']==presented['evidence']
        assert original['net_pnl']==presented['net_pnl']
    assert batch==before


def test_cash_account_labels_are_business_names_and_bound_to_the_result_strategy(valued):
    from tests.test_cash_fx_storage import add_account,add_balance,daily,stage
    from dataclasses import replace
    from datetime import date
    from valuation import storage
    c,r,_=valued;account=add_account(c,r,'Custody')
    foreign=add_account(c,replace(r,strategy_id=ids['strategy']),'Do not disclose')
    for day in (date(2026,9,29),date(2026,9,30),date(2026,10,1)):add_balance(c,r,account,day,'100')
    r=daily(r);view=storage.batch_view(c,r.tenant_id,stage(c,r,service().calculate(c,r)))
    before=deepcopy(view)
    # Even a foreign account embedded in malformed display-only coverage must
    # not resolve outside the result's tenant/strategy.
    view['summary']['cashCoverage']['scopes'].append(dict(accountId=str(foreign),currencyId=str(ids['gbp_currency'])))
    projected=decorate_batch(c,r.tenant_id,view)
    assert 'Custody' in projected['presentation']['cashAccounts'][str(account)]
    assert str(foreign) not in projected['presentation']['cashAccounts']
    for original,presented in zip(before['items'],projected['items']):
        for field in ('evidence','components','cash_account_id','cash_currency_id','net_pnl'):
            assert original[field]==presented[field]
    cash=next(row for row in projected['presentation']['sourceCoverage']['rows'] if row['code']=='CASH_BALANCE_FX')
    assert cash['cashAccountCount']==1 and cash['positionCount']==0
