"""Native booking and real governed price resolution in an owned disposable DB."""
from dataclasses import replace,asdict
from datetime import date,datetime,time,timezone
from decimal import Decimal as D
from uuid import uuid4,UUID
import json
import pytest
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued


def setup_swap(valued,tmp_path):
    from tests.test_swap_creation_api import proposal,create_reference
    from apps.reference_api.product_booking import submit_proposal,decide_proposal
    from apps.reference_api.swap_creation_contracts import SwapProposalRequest
    from apps.reference_api.product_booking import book,load_context
    from apps.reference_api.product_booking_contracts import ProductBookingRequest
    c,request,_=valued;tenant=ids['tenant'];actor=ids['demo_user_account']
    # Native synthetic contract: no external CSV loader, source mapping or
    # source-specific mockup-term completion is needed to exercise valuation.
    terms=proposal(create_reference(),quantityUnit='UNITS',contractualUnits='1000',
        notionalPerUnit='100',contractualNotional='100000',quoteFactor='1')
    view=submit_proposal(c,tenant,actor,SwapProposalRequest.model_validate(terms))
    view=decide_proposal(c,tenant,actor,view.proposal_id,'APPROVED','Synthetic native valuation fixture')
    assert view.status=='APPROVED'
    node=view.reference_node_id
    context=load_context(c,tenant,node,as_of=date(2026,9,29))
    ticket=ProductBookingRequest(instrumentId=node,executionRoute='OTC',strategyId=request.strategy_id,side='BUY',
        quantity='100',executionPrice='-3',tradeDatetime='2026-09-29T10:00:00Z',
        counterpartyOrganisationId=ids['bank_a_organisation'],expectedTermsFingerprint=context.terms_fingerprint)
    # Keep the valued fixture's unrelated legacy equity outside this request.
    row=dict(c.execute(select(m.strategy).where(m.strategy.c.strategy_id==request.strategy_id)).mappings().one())
    strategy=uuid4();c.execute(m.strategy.insert().values(**(row|dict(strategy_id=strategy,strategy_code='SWAP_'+strategy.hex))))
    # Native writer into the separate population, never a direct trade-table mutation.
    ticket=ticket.model_copy(update={'strategy_id':strategy})
    detail=book(c,tenant,actor,ticket,str(uuid4()),'SWAP','test-swap')
    trade=detail.data.trade.trade_id
    request=replace(request,strategy_id=strategy)
    series=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one())
    sid=uuid4()
    c.execute(m.market_data_series.insert().values(**(series|dict(market_data_series_id=sid,reference_node_id=node,series_type='MARK',closing_method='UNKNOWN'))))
    for code,value in [('SWAP_PRICE_BASIS','WHOLE_SWAP_MTM_PER_UNIT'),('QUANTITY_UNIT','UNITS'),('QUOTE_FACTOR','1')]:
        c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=sid,dimension_code=code,dimension_value=value))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule'])
        .values(subject_type='INSTRUMENT',instrument_type_id=None,subject_reference_node_id=node,market_data_series_id=sid,
            series_type='MARK',value_basis='RAW',require_official_close=False,price_requirement=None,allow_split_conversion=False,
            pricing_convention='EXPLICIT_TIME',pricing_cut_id=ids['valuation_cut']))
    original=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    for day,value in [(date(2026,9,29),'-2'),(date(2026,10,1),'0')]:
        stamp=datetime.combine(day,time(14),timezone.utc)
        c.execute(m.market_data_observation.insert().values(**(original|dict(market_data_observation_id=uuid4(),market_data_series_id=sid,
            market_date=day,value=D(value),market_data_vintage_id=None,received_at_utc=stamp,
            source_published_at_utc=stamp,observed_at_utc=stamp,source_observation_key='SWAP_'+uuid4().hex))))
    return c,request,trade,sid


@pytest.mark.parametrize('legacy',[False,True])
def test_native_swap_negative_and_zero_marks_use_whole_quote_once(valued,tmp_path,legacy):
    from valuation.service import calculate_position
    from valuation.decisions import applied_decisions
    c,request,trade,_=setup_swap(valued,tmp_path)
    event=c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade)).mappings().one()
    assert json.loads(event['event_payload'])['valuationConventions']['unitMultiplier']=='1'
    if legacy:
        # Retained old-format fixture in an owned DB, not a rewrite of any event.
        row=dict(c.execute(select(m.strategy).where(m.strategy.c.strategy_id==request.strategy_id)).mappings().one())
        strategy=uuid4();c.execute(m.strategy.insert().values(**(row|dict(strategy_id=strategy,strategy_code='LEGACY_'+strategy.hex))))
        booked=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
        trade=uuid4();c.execute(m.trade.insert().values(**(booked|dict(trade_id=trade,strategy_id=strategy))))
        payload=json.loads(event['event_payload']);payload.pop('valuationConventions')
        c.execute(m.trade_lifecycle_event.insert().values(**(dict(event)|dict(trade_lifecycle_event_id=uuid4(),trade_id=trade,
            source_event_id=str(uuid4()),event_payload=json.dumps(payload)))))
        event=c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade)).mappings().one()
        request=replace(request,strategy_id=strategy)
    before=event['event_payload']
    result=calculate_position(c,request)
    assert result.period.market_pnl==200 and result.period.closing_value==0
    assert result.projection.buckets[0].closing_quantity==100
    assert len(result.resolution_snapshot_ids)==2
    assert c.scalar(select(m.trade_lifecycle_event.c.event_payload).where(m.trade_lifecycle_event.c.trade_id==trade))==before
    rules=applied_decisions(dict(identity=dict(bucket=dict(key=dict(product_basis='SWAP',quote_factor='1',unit_multiplier='1',quantity_unit='UNITS')))))
    assert any(r['code']=='SWAP_WHOLE_MARK' for r in rules)
    from valuation import storage,tables as t
    from valuation.economics import canonical_payload,evidence_hash
    # Attempt fixture shares the test transaction; independent begin_attempt
    # cannot see the deliberately uncommitted synthetic strategy parent.
    actor=ids['demo_user_account']
    attempt=c.execute(t.attempt.insert().values(tenant_id=request.tenant_id,strategy_id=request.strategy_id,initiated_by=actor,
        request_key=str(uuid4()),request_hash=evidence_hash(dict(request=storage.request_identity(request),actor=actor)),
        request_payload=canonical_payload(asdict(request)),correlation_id=str(uuid4()),status='RUNNING').returning(t.attempt.c.attempt_id)).scalar_one()
    batch=storage.stage(c,attempt,actor,result)
    view=storage.batch_view(c,request.tenant_id,batch)
    assert view['status']=='STAGED' and D(view['summary']['marketPnl'])==200
    assert any(r['code']=='SWAP_WHOLE_MARK' for r in view['items'][0]['evidence']['appliedRules'])
    assert storage.published(c,request.tenant_id,request.strategy_id,request.closing_cutoff.date())==[]


@pytest.mark.parametrize('ambiguous',[False,True])
def test_wrong_swap_mark_dimension_is_not_substituted(valued,tmp_path,ambiguous):
    from valuation.service import calculate_position,ValuationBlocked
    c,request,_,sid=setup_swap(valued,tmp_path)
    if ambiguous:
        c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=sid,dimension_code='SWAP_PRICE_BASIS',dimension_value='UNDERLYING_INDEX'))
    else:
        c.execute(m.market_data_series_dimension.update().where(m.market_data_series_dimension.c.market_data_series_id==sid,
            m.market_data_series_dimension.c.dimension_code=='SWAP_PRICE_BASIS').values(dimension_value='UNDERLYING_INDEX'))
    with pytest.raises(ValuationBlocked):calculate_position(c,request)
