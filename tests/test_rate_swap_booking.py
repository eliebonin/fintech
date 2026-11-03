"""Native rate-swap approval, retained identities and independent bank marks."""
from copy import deepcopy
from datetime import date,datetime,time,timezone
from dataclasses import replace
from decimal import Decimal as D
from uuid import uuid4
import json
import pytest
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued


def request(c,**changes):
    from tests.test_rate_swap_terms import payload
    from apps.reference_api.swap_creation_contracts import SwapProposalRequest
    p=payload();rate=uuid4()
    seed=dict(c.execute(select(m.financial_reference_node).where(m.financial_reference_node.c.reference_node_id==ids['sonia_rate_index_node'])).mappings().one())
    c.execute(m.financial_reference_node.insert().values(**(seed|dict(reference_node_id=rate,canonical_name='Synthetic USD overnight rate',internal_code='RATE_'+rate.hex))))
    c.execute(m.reference_node_scope.insert().values(reference_node_id=rate,scope_type='TENANT_PRIVATE',owner_tenant_id=ids['tenant'],status='ACTIVE'))
    p.update(notionalCurrencyId=str(ids['gbp_currency']),quoteCurrencyId=str(ids['gbp_currency']))
    for leg,currency,node in zip(p['legs'],[ids['usd_currency'],ids['gbp_currency']],[rate,ids['sonia_rate_index_node']]):
        leg.update(currencyId=str(currency),rateReferenceId=str(node),dayCountConventionId=str(c.scalar(select(m.day_count_convention.c.day_count_convention_id).where(m.day_count_convention.c.code=='ACT_365F'))))
    return SwapProposalRequest(canonicalName='Synthetic rate exchange '+uuid4().hex,terms=p,**changes)


def create(c,req):
    from apps.reference_api.product_booking import submit_proposal,decide_proposal
    p=submit_proposal(c,ids['tenant'],ids['demo_user_account'],req)
    return decide_proposal(c,ids['tenant'],ids['demo_user_account'],p.proposal_id,'APPROVED','Synthetic rate terms reviewed').reference_node_id


def book(c,r,node,*,quantity='100',price='1',side='BUY',key=None,correction=None):
    from apps.reference_api.product_booking import load_context,book as post
    from apps.reference_api.product_booking_contracts import ProductBookingRequest
    context=load_context(c,r.tenant_id,node,as_of=r.opening_cutoff.date())
    assert context.booking_eligible,context
    req=ProductBookingRequest(instrumentId=node,strategyId=r.strategy_id,executionRoute='OTC',side=side,quantity=quantity,executionPrice=price,
        tradeDatetime=datetime.combine(r.opening_cutoff.date(),time(10),timezone.utc),counterpartyOrganisationId=ids['bank_a_organisation'],expectedTermsFingerprint=context.terms_fingerprint,correction=correction)
    return post(c,r.tenant_id,ids['demo_user_account'],req,key or str(uuid4()),'SWAP','synthetic-rate').data


def shell(c,r):
    node,version=uuid4(),uuid4()
    rt=c.scalar(select(m.reference_node_type.c.reference_node_type_id).where(m.reference_node_type.c.type_code=='INSTRUMENT'))
    it=c.scalar(select(m.instrument_type.c.instrument_type_id).where(m.instrument_type.c.type_code=='SWAP'))
    c.execute(m.financial_reference_node.insert().values(reference_node_id=node,reference_node_type_id=rt,canonical_name='Synthetic untradable rate reference',is_tradable=False,status='ACTIVE'))
    c.execute(m.reference_node_scope.insert().values(reference_node_id=node,scope_type='TENANT_PRIVATE',owner_tenant_id=r.tenant_id,status='ACTIVE'))
    values=dict(instrument_node_id=node,instrument_type_id=it,base_currency_id=ids['gbp_currency'],effective_from=date(2020,1,1),sequence_no=1,is_current=True,asset_class='DERIVATIVE')
    c.execute(m.instrument.insert().values(**values))
    source=c.scalar(select(m.source_payload.c.source_payload_id).where(m.source_payload.c.tenant_id==r.tenant_id).limit(1))
    assert source is not None
    c.execute(m.instrument_definition_version.insert().values(**values,instrument_definition_version_id=version,status='APPROVED',source_payload_id=source))
    return node,version


def test_two_rate_legs_book_with_independent_currencies_and_native_retry(valued):
    c,r,_=valued;node=create(c,request(c));key=str(uuid4())
    detail=book(c,r,node,quantity='13000000',price='-0.01',key=key)
    assert detail.trade.quantity=='13000000.000000000000'
    assert detail.trade.product_economics['amount']=='-130000'
    assert book(c,r,node,quantity='13000000',price='-0.01',key=key).trade.trade_id==detail.trade.trade_id
    payload=detail.trade.product_economics['terms']['swapDetails']['genericTerms']
    assert payload['swapKind']=='RATE_EXCHANGE' and len(payload['legs'])==2
    legs=c.execute(select(m.swap_leg).where(m.swap_leg.c.swap_instrument_node_id==node).order_by(m.swap_leg.c.leg_number)).mappings().all()
    assert [x['currency_id'] for x in legs]==[ids['usd_currency'],ids['gbp_currency']]
    assert all(x['return_profile_id'] is None for x in legs)
    assert c.scalar(select(m.swap_terms.c.swap_type).where(m.swap_terms.c.instrument_node_id==node))=='CROSS_CURRENCY'


def test_first_completion_keeps_reference_and_price_series_identity(valued):
    c,r,_=valued;node,old=shell(c,r)
    series=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one())
    sid=uuid4();c.execute(m.market_data_series.insert().values(**(series|dict(market_data_series_id=sid,reference_node_id=node))))
    req=request(c,existingReferenceId=node,expectedReferenceDefinitionId=old)
    assert create(c,req)==node
    assert c.scalar(select(m.market_data_series.c.reference_node_id).where(m.market_data_series.c.market_data_series_id==sid))==node
    assert c.scalar(select(m.instrument_definition_version.c.sequence_no).where(m.instrument_definition_version.c.instrument_definition_version_id==old))==1
    assert c.scalar(select(m.instrument.c.sequence_no).where(m.instrument.c.instrument_node_id==node))==2
    trade=book(c,r,node).trade.trade_id
    assert c.scalar(select(m.trade.c.reference_instrument_node_id).where(m.trade.c.trade_id==trade))==node
    with pytest.raises(ValueError):create(c,req)


def test_approval_rechecks_rate_status_and_refuses_a_foreign_or_stale_shell(valued):
    from apps.reference_api.product_booking import submit_proposal,decide_proposal
    c,r,_=valued;req=request(c)
    p=submit_proposal(c,r.tenant_id,ids['demo_user_account'],req)
    c.execute(m.financial_reference_node.update().where(m.financial_reference_node.c.reference_node_id==req.terms.legs[0].rate_reference_id).values(status='INACTIVE'))
    with pytest.raises((ValueError,LookupError)):
        with c.begin_nested():decide_proposal(c,r.tenant_id,ids['demo_user_account'],p.proposal_id,'APPROVED','Must revalidate')
    node,old=shell(c,r)
    with pytest.raises(ValueError):create(c,request(c,existingReferenceId=node,expectedReferenceDefinitionId=uuid4()))
    c.execute(m.reference_node_scope.update().where(m.reference_node_scope.c.reference_node_id==node).values(owner_tenant_id=ids['second_tenant']))
    with pytest.raises((ValueError,LookupError)):create(c,request(c,existingReferenceId=node,expectedReferenceDefinitionId=old))


def test_separate_rate_contracts_keep_separate_bank_marks_and_staged_pnl(valued):
    from datetime import timedelta
    from valuation.service import calculate_position
    from valuation.storage import batch_view
    from tests.test_cash_product_pnl_integration import stage
    c,r,_=valued
    row=dict(c.execute(select(m.strategy).where(m.strategy.c.strategy_id==r.strategy_id)).mappings().one())
    strategy=uuid4();c.execute(m.strategy.insert().values(**(row|dict(strategy_id=strategy,strategy_code='RATE_MARKS_'+strategy.hex))))
    r=replace(r,strategy_id=strategy,opening_cutoff=r.closing_cutoff-timedelta(days=1),daily=True)
    nodes=[]
    for sequence,prices in enumerate([('0.995','0.997'),('1.004','1.003')]):
        node=create(c,request(c));nodes.append(node);book(c,r,node)
        original=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one())
        series=uuid4()
        c.execute(m.market_data_series.insert().values(**(original|dict(market_data_series_id=series,reference_node_id=node,series_type='MARK',closing_method='UNKNOWN',is_official=False))))
        for code,value in [('SWAP_PRICE_BASIS','WHOLE_SWAP_MTM_PER_NOTIONAL'),('QUANTITY_UNIT','NOMINAL'),('QUOTE_FACTOR','1')]:
            c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=series,dimension_code=code,dimension_value=value))
        rule=dict(c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule'])).mappings().one())
        c.execute(m.valuation_policy_rule.insert().values(**(rule|dict(valuation_policy_rule_id=uuid4(),rule_sequence=240+sequence,
            subject_type='INSTRUMENT',subject_reference_node_id=node,instrument_type_id=None,market_venue_id=None,is_default=False,
            market_data_series_id=series,series_type='MARK',value_basis='RAW',price_requirement=None,require_official_close=False,
            pricing_convention='EXPLICIT_TIME',pricing_cut_id=ids['valuation_cut']))))
        observation=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
        for day,price in zip([r.opening_cutoff.date(),r.closing_cutoff.date()],prices):
            stamp=datetime.combine(day,time(14),timezone.utc)
            c.execute(m.market_data_observation.insert().values(**(observation|dict(market_data_observation_id=uuid4(),market_data_series_id=series,
                market_date=day,value=D(price),value_basis='RAW',market_data_vintage_id=None,observed_at_utc=stamp,received_at_utc=stamp,
                source_published_at_utc=stamp,source_observation_key='RATE_MARK_'+uuid4().hex))))
    result=calculate_position(c,r)
    assert {line.bucket.key.subject_id:line.attribution.market_pnl for line in result.period.lines}=={nodes[0]:D('.2'),nodes[1]:D('-.1')}
    assert result.period.market_pnl==D('.1')
    batch=stage(c,r,result);view=batch_view(c,r.tenant_id,batch)
    assert view['status']=='STAGED' and len(view['items'])==2
    assert {item['subject_id'] for item in view['items']}==set(nodes)


def test_rate_booking_correction_and_cancellation_retain_original_evidence(valued):
    from tests.test_trade_corrections import cancel
    c,r,_=valued;node=create(c,request(c))
    original=book(c,r,node)
    corrected=book(c,r,node,quantity='80',correction=dict(tradeId=original.trade.trade_id,expectedSequenceNo=1,reason='Synthetic quantity correction'))
    assert corrected.trade.quantity=='80.000000000000'
    assert c.scalar(select(m.trade.c.lifecycle_status).where(m.trade.c.trade_id==original.trade.trade_id))=='SUPERSEDED'
    cancelled=cancel(c,corrected.trade.trade_id,sequence=2).data
    assert cancelled.trade.lifecycle_status=='CANCELLED'
    assert json.loads(cancelled.lifecycle_events[0].event_payload)['economics']['terms']['swapDetails']['genericTerms']['swapKind']=='RATE_EXCHANGE'


def test_changed_currency_population_is_refused_before_late_currency_locks(valued):
    from apps.reference_api.generic_swap_booking import load_generic_swap_context
    c,r,_=valued;node=create(c,request(c))
    with pytest.raises(ValueError,match='currency roles changed'):
        load_generic_swap_context(c,r.tenant_id,node,r.opening_cutoff.date(),lock=True,currency_locks=(ids['gbp_currency'],frozenset({ids['gbp_currency']})))


def test_http_rate_swap_creation_booking_and_cancellation_wire_contract(valued):
    from tests.test_fx_forward_booking_api import request as http
    c,r,_=valued;proposal=request(c)
    # Only this owned disposable fixture is committed for independent HTTP reads.
    c.commit()
    submitted=http('POST','/v1/instruments/swap-proposals',proposal.model_dump(mode='json',by_alias=True))
    assert submitted.status_code==201,submitted.text
    pid=submitted.json()['data']['proposalId']
    approved=http('POST',f'/v1/reference-data-proposals/{pid}/decision',dict(decision='APPROVED',reason='Synthetic floating-leg confirmation reviewed'))
    assert approved.status_code==200,approved.text
    node=approved.json()['data']['referenceNodeId']
    context=http('GET',f'/v1/trades/product-instruments/{node}?asOfDate=2026-10-01')
    assert context.status_code==200,context.text
    terms=context.json()['data'];assert terms['bookingEligible']
    assert terms['swapDetails']['genericTerms']['swapKind']=='RATE_EXCHANGE'
    response=http('POST','/v1/trades/swaps',dict(instrumentId=node,strategyId=str(r.strategy_id),executionRoute='OTC',side='SELL',quantity='100',executionPrice='-0.01',
        tradeDatetime='2026-10-01T10:00:00Z',counterpartyOrganisationId=str(ids['bank_a_organisation']),expectedTermsFingerprint=terms['termsFingerprint']),key=str(uuid4()))
    assert response.status_code==201,response.text
    trade=response.json()['data']['trade'];assert trade['quantity']=='-100.000000000000'
    assert trade['productEconomics']['amount']=='1'
    cancelled=http('POST',f"/v1/trades/{trade['tradeId']}/cancel-booking",dict(expectedSequenceNo=1,reason='Synthetic wire acceptance complete'),key=str(uuid4()))
    assert cancelled.status_code==200,cancelled.text
    assert cancelled.json()['data']['trade']['lifecycleStatus']=='CANCELLED'
