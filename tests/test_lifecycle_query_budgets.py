"""Native distinct-contract and repeated-trade read budgets on disposable state."""
from datetime import date
from uuid import UUID,uuid4
from copy import deepcopy
import json,time
import pytest
from sqlalchemy import select,event
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued
from tests.test_option_booking_api import listing
from tests.test_option_worklist import option_context,cash_listing
from tests.test_product_booking_api import future
from tests.test_future_measure_inputs import future_inputs
from tests.test_future_worklist import enabled,events
from tests.test_fx_maturity_service import setup
from tests.test_fx_maturity_worklist import read as fx_read
from tests.test_structured_batch_reads import QueryCounter


def clone_shell(c,parent,tenant,prefix):
    target=uuid4();definition_map={}
    for table,key in [(m.financial_reference_node,'reference_node_id'),(m.instrument,'instrument_node_id'),(m.instrument_definition_version,'instrument_node_id'),(m.instrument_dates,'instrument_node_id'),(m.instrument_booking_convention,'instrument_node_id')]:
        for record in c.execute(select(table).where(table.c[key]==parent)).mappings().all():
            row=dict(record);row[key]=target
            for pk in table.primary_key.columns:
                if pk.name!=key:row[pk.name]=uuid4()
            if table is m.financial_reference_node:row.update(canonical_name=prefix+' '+target.hex,internal_code=prefix+'_'+target.hex)
            if table is m.instrument_definition_version:definition_map[record['instrument_definition_version_id']]=row['instrument_definition_version_id']
            c.execute(table.insert().values(**row))
    c.execute(m.reference_node_scope.insert().values(reference_node_id=target,scope_type='TENANT_PRIVATE',owner_tenant_id=tenant,status='ACTIVE'))
    return target


def clone_listing(c,listing,parent,tenant):
    target=uuid4()
    for table,key in [(m.financial_reference_node,'reference_node_id'),(m.listing,'listing_node_id'),(m.listing_definition_version,'listing_node_id')]:
        for record in c.execute(select(table).where(table.c[key]==listing)).mappings().all():
            row=dict(record);row[key]=target
            for pk in table.primary_key.columns:
                if pk.name!=key:row[pk.name]=uuid4()
            if table is m.financial_reference_node:row.update(canonical_name='Read-budget listing '+target.hex,internal_code='READ_LIST_'+target.hex)
            if 'instrument_node_id' in row:row['instrument_node_id']=parent
            if 'trading_symbol' in row:row['trading_symbol']='R'+target.hex[:10]
            c.execute(table.insert().values(**row))
    c.execute(m.reference_node_scope.insert().values(reference_node_id=target,scope_type='TENANT_PRIVATE',owner_tenant_id=tenant,status='ACTIVE'))
    return target


def clone_contract(c,parent,listing,tenant,kind):
    target=clone_shell(c,parent,tenant,'READ_'+kind)
    tables=[m.option_terms,m.instrument_contract_unit_terms] if kind=='OPTION' else [m.future_terms]
    for table in tables:
        for record in c.execute(select(table).where(table.c.instrument_node_id==parent)).mappings().all():
            row=dict(record);row['instrument_node_id']=target
            for pk in table.primary_key.columns:
                if pk.name!='instrument_node_id':row[pk.name]=uuid4()
            if kind=='FUTURE':
                family=dict(c.execute(select(m.future_family).where(m.future_family.c.future_family_id==row['future_family_id'])).mappings().one())
                old_family_node=family['family_node_id'];family_node=uuid4()
                node=dict(c.execute(select(m.financial_reference_node).where(m.financial_reference_node.c.reference_node_id==old_family_node)).mappings().one())
                node.update(reference_node_id=family_node,canonical_name='Read-budget family '+family_node.hex,internal_code='READ_FAMILY_'+family_node.hex)
                c.execute(m.financial_reference_node.insert().values(**node))
                c.execute(m.reference_node_scope.insert().values(reference_node_id=family_node,scope_type='TENANT_PRIVATE',owner_tenant_id=tenant,status='ACTIVE'))
                family.update(future_family_id=uuid4(),family_node_id=family_node)
                c.execute(m.future_family.insert().values(**family));row['future_family_id']=family['future_family_id']
            c.execute(table.insert().values(**row))
    return target,clone_listing(c,listing,target,tenant)


def timed(c,callback):
    with QueryCounter(c) as queries:
        start=time.perf_counter();result=callback();elapsed=time.perf_counter()-start
    return result,queries.count,round(elapsed,4)


def test_option_read_budget_includes_repeated_trades_and_distinct_contracts(option_context):
    from apps.reference_api.option_booking import load,book
    from apps.reference_api.contracts import OptionBookingRequest
    from tests.test_option_worklist import read
    c,r,parent,trade,execute,kind=option_context
    initial,small,_=timed(c,lambda:read(c,r));subject=c.scalar(select(m.trade.c.trade_subject_reference_node_id).where(m.trade.c.trade_id==trade))
    for _ in range(8):execute()
    for _ in range(12):
        target,listed=clone_contract(c,parent,subject,r.tenant_id,'OPTION');_,terms=load(c,r.tenant_id,listed,as_of=date(2026,10,1))
        request=OptionBookingRequest(listingId=listed,strategyId=r.strategy_id,side='BUY',quantity='10',executionPrice='2.5',tradeDatetime='2026-10-01T10:00:00Z',settlementDate='2026-10-05',positionEffect='OPEN',counterpartyOrganisationId=ids['bank_a_organisation'],expectedTermsFingerprint=terms.terms_fingerprint)
        book(c,r.tenant_id,ids['demo_user_account'],request,str(uuid4()),'option-read-budget')
    result,large,elapsed=timed(c,lambda:read(c,r))
    assert result['total']==initial['total']*13
    print('OPTION',kind,dict(small=small,large=large,seconds=elapsed,total=result['total']))
    assert large<=small+8,(small,large)


def test_future_read_budget_includes_many_distinct_original_contracts(future_inputs):
    from apps.reference_api.product_booking import load_context,book
    from apps.reference_api.product_booking_contracts import ProductBookingRequest
    c,r,parent,execute=enabled(future_inputs)
    original,small,_=timed(c,lambda:events(c,r));subject=c.scalar(select(m.trade.c.trade_subject_reference_node_id).where(m.trade.c.strategy_id==r.strategy_id,m.trade.c.quantity_unit=='CONTRACTS'))
    for _ in range(12):
        target,listed=clone_contract(c,parent,subject,r.tenant_id,'FUTURE');terms=load_context(c,r.tenant_id,target,listed,date(2026,10,1))
        request=ProductBookingRequest.model_validate(dict(instrumentId=str(target),listingId=str(listed),strategyId=str(r.strategy_id),executionRoute='LISTED',side='BUY',quantity='10',executionPrice='6000',tradeDatetime='2026-10-01T10:00:00Z',positionEffect='OPEN',expectedTermsFingerprint=terms.terms_fingerprint))
        book(c,r.tenant_id,ids['demo_user_account'],request,str(uuid4()),'FUTURE','future-read-budget')
    result,large,elapsed=timed(c,lambda:events(c,r))
    assert result['total']==original['total']*13
    print('FUTURE',dict(small=small,large=large,seconds=elapsed,total=result['total']))
    assert large<=small+8,(small,large)


def test_forward_read_budget_batches_distinct_contracts(valued):
    from security_master_schema.fx_forward_reference import load_fx_forward_booking_terms
    from security_master_schema.fx_forward_booking import fx_forward_terms_fingerprint
    from apps.reference_api.fx_forward_booking import book_fx_forward_trade
    from apps.reference_api.contracts import FxForwardBookingRequest
    c,r,_=valued;parent,*_=setup(c,r)
    original,small,_=timed(c,lambda:fx_read(c,r))
    for _ in range(12):
        target=clone_shell(c,parent,r.tenant_id,'READ_FX')
        term=dict(c.execute(select(m.fx_forward_terms).where(m.fx_forward_terms.c.instrument_node_id==parent)).mappings().one());term['instrument_node_id']=target
        c.execute(m.fx_forward_terms.insert().values(**term));terms=load_fx_forward_booking_terms(c,r.tenant_id,target,as_of=date(2026,9,30))
        request=FxForwardBookingRequest.model_validate(dict(instrumentId=str(target),strategyId=str(r.strategy_id),side='BUY',quantity='1000000',tradeDatetime='2026-09-30T10:00:00Z',counterpartyOrganisationId=str(ids['bank_a_organisation']),expectedTermsFingerprint=fx_forward_terms_fingerprint(terms)))
        book_fx_forward_trade(c,r.tenant_id,ids['demo_user_account'],request,str(uuid4()),'forward-read-budget')
    result,large,elapsed=timed(c,lambda:fx_read(c,r))
    assert result['total']==13 and all(row['positionAssessed'] for row in result['items'])
    print('FX_FORWARD',dict(small=small,large=large,seconds=elapsed,total=result['total']))
    assert large<=small+10,(small,large)


def test_historical_identity_pages_preserve_all_original_option_facts(option_context,monkeypatch):
    from dataclasses import replace
    from positions import repository
    from positions.identity_sources import HistoricalIdentitySources
    from positions.contracts import PositionError
    from tests.test_position_repository import projection_request
    c,r,parent,trade,execute,kind=option_context
    for _ in range(4):execute()
    request=projection_request(r)
    original=list(repository.iter_ledger_facts(c,request))
    monkeypatch.setattr(repository,'CHUNK_SIZE',2)
    assert list(repository.iter_ledger_facts(c,request))==original
    rows=c.execute(select(m.trade).where(m.trade.c.strategy_id==r.strategy_id)).mappings().all()
    with QueryCounter(c) as queries:
        source=HistoricalIdentitySources(c,request,rows)
    assert queries.count==0
    with pytest.raises(PositionError,match='different ledger'):
        source.require_scope(c,dict(rows[0])|dict(strategy_id=uuid4()))
    with pytest.raises(PositionError,match='not included'):
        source.require_scope(c,dict(rows[0])|dict(reference_instrument_node_id=uuid4()))
