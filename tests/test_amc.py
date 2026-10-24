"""AMC remains a certificate while sharing governed funded-security mechanics."""
from uuid import uuid4, UUID
from decimal import Decimal
import pytest
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS


def draft(**changes):
    return dict(idempotencyKey=str(uuid4()),canonicalName='Example managed certificate',issuerOrganisationId=str(DEMO_IDS['bank_a_organisation']),
        baseCurrencyId=str(DEMO_IDS['gbp_currency']),effectiveFrom='2024-01-01',redemptionModel='OPEN_ENDED',
        distributionPolicy='UNKNOWN',sourceReference='Synthetic signed terms',
        convention=dict(kind='ACTIVELY_MANAGED_CERTIFICATE',effectiveFrom='2024-01-01',
            priceCurrencyId=str(DEMO_IDS['gbp_currency']),quoteFactor='1',sourceReference='Synthetic unit quote',
            funding='FULLY_FUNDED',quantityUnit='UNITS',priceBasis='UNIT_PRICE',quantityMinimum='0.01',
            quantityIncrement='0.01',accrual='NONE',otcAllowed=True)) | changes


def test_amc_has_explicit_identity_without_fund_nav_or_etp_defaults():
    from apps.reference_api.amc_contracts import AmcProposalRequest
    request=AmcProposalRequest.model_validate(draft())
    assert request.convention.kind=='ACTIVELY_MANAGED_CERTIFICATE'
    assert request.pricing_frequency is None and request.publication_lag_business_days is None
    assert request.adviser_organisation_id is None and request.reference_node_id is None
    assert request.maturity_date is None
    for changes in (dict(redemptionModel='FIXED_MATURITY'),dict(maturityDate='2023-01-01'),
                    dict(canonicalName='  '),dict(baseCurrencyId=str(uuid4()))):
        with pytest.raises(ValueError):AmcProposalRequest.model_validate(draft(**changes))


def test_amc_approval_booking_and_position_use_native_certificate_type():
    from tests.test_fx_forward_booking_api import request
    from apps.reference_api.db import get_engine
    data=draft(idempotencyKey=str(uuid4()),isin='XS0000000091')
    response=request('POST','/v1/instruments/amc-proposals',data)
    assert response.status_code==201,response.text
    proposal=response.json()['data']['proposalId']
    queue=request('GET','/v1/work-queue').json()['items']
    assert any(i['referenceId']==proposal and i['proposalType']=='CREATE_AMC' and i['reviewPath'] for i in queue)
    decision=request('POST',f'/v1/reference-data-proposals/{proposal}/decision',dict(decision='APPROVED',reason='Synthetic terms checked'))
    assert decision.status_code==200,decision.text
    node=UUID(decision.json()['data']['referenceNodeId'])
    inspection=request('GET',f'/v1/instruments/{node}')
    assert inspection.status_code==200,inspection.text
    assert inspection.json()['data']['amcTerms']['redemptionModel']=='OPEN_ENDED'
    assert inspection.json()['data']['amcTerms']['publicationLagBusinessDays'] is None
    hidden=request('GET',f'/v1/instruments/{node}',tenant='second_tenant')
    assert hidden.status_code in (403,404),hidden.text
    replay=request('POST','/v1/instruments/amc-proposals',data)
    assert replay.status_code==201 and replay.json()['data']['proposalId']==proposal
    duplicate=request('POST','/v1/instruments/amc-proposals',data | dict(idempotencyKey=str(uuid4())))
    assert duplicate.status_code==422,duplicate.text
    context=request('GET',f'/v1/trades/product-instruments/{node}?asOfDate=2026-10-01')
    assert context.status_code==200,context.text
    terms=context.json()['data'];assert terms['bookingEligible'],terms
    assert terms['kind']=='ACTIVELY_MANAGED_CERTIFICATE'
    from tests.test_product_booking_api import payload as booking
    # Reuse shared ticket annotations, but retain this AMC's reviewed terms.
    payload=booking(str(node))
    payload.update(quantity='10.25',executionPrice='102.5',tradeDatetime='2026-10-01T12:00:00Z',settlementDate='2026-10-05')
    booked=request('POST','/v1/trades/amcs',payload,key=str(uuid4()))
    assert booked.status_code==201,booked.text
    with get_engine().connect() as c:
        stored=c.execute(select(m.amc_terms).where(m.amc_terms.c.instrument_node_id==node)).mappings().one()
        assert stored['redemption_model']=='OPEN_ENDED' and stored['pricing_frequency'] is None
        trade=c.execute(select(m.trade).where(m.trade.c.trade_id==UUID(booked.json()['data']['trade']['tradeId']))).mappings().one()
        assert trade['quantity']==Decimal('10.25') and trade['price_basis']=='UNIT_PRICE'
        assert c.scalar(select(m.instrument_type.c.type_code).join(m.instrument).where(m.instrument.c.instrument_node_id==node))=='ACTIVELY_MANAGED_CERTIFICATE'
        from positions.repository import iter_ledger_facts
        from positions.contracts import ProjectionRequest
        from datetime import datetime,timezone
        from sqlalchemy import func
        known_at=c.scalar(select(func.clock_timestamp()))
        facts=list(iter_ledger_facts(c,ProjectionRequest(DEMO_IDS['tenant'],DEMO_IDS['strategy'],
            datetime(2026,10,2,tzinfo=timezone.utc),known_at),subject_ids=[node]))
        assert facts,dict(created=trade['created_at_utc'],known_at=known_at,subject=trade['trade_subject_reference_node_id'],recognition=trade['valuation_effective_date'])
        opening=next(f.booking for f in facts if f.booking)
        assert opening.product_basis=='ACTIVELY_MANAGED_CERTIFICATE' and opening.quantity==Decimal('10.25')
    sold=request('POST','/v1/trades/amcs',payload | dict(side='SELL',quantity='4.25'),key=str(uuid4()))
    assert sold.status_code==201,sold.text
    with get_engine().connect() as c:
        from sqlalchemy import func
        assert c.scalar(select(func.sum(m.trade.c.quantity)).where(m.trade.c.reference_instrument_node_id==node))==6


def test_amc_approval_rechecks_inactive_issuer():
    from apps.reference_api.amc_contracts import AmcProposalRequest
    from apps.reference_api.product_booking import submit_proposal,decide_proposal
    from apps.reference_api.db import get_engine
    tenant=DEMO_IDS['tenant'];actor=DEMO_IDS['demo_user_account']
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            view=submit_proposal(c,tenant,actor,AmcProposalRequest.model_validate(draft(idempotencyKey=str(uuid4()))))
            c.execute(m.organisation.update().where(m.organisation.c.organisation_id==DEMO_IDS['bank_a_organisation']).values(status='INACTIVE'))
            with pytest.raises(ValueError,match='active'):
                decide_proposal(c,tenant,actor,view.proposal_id,'APPROVED','Synthetic')
        finally:tx.rollback()


def test_amc_price_capability_is_not_fund_nav():
    from valuation.product_inputs import supported_product
    assert supported_product('ACTIVELY_MANAGED_CERTIFICATE','UNITS')=='PRICE'
    assert supported_product('ACTIVELY_MANAGED_CERTIFICATE','NOMINAL')=='PRICE'


def test_amc_market_bridge_reuses_unit_arithmetic_without_nav_or_fee_inference():
    from datetime import datetime,timezone
    from positions.contracts import ProjectionRequest,PositionKey,PositionBucket,PositionProjection,Booking,ExecutionEffect
    from valuation.position_calculation import attribute_projection,MarkKey
    tenant,strategy,subject,currency,trade,definition=(uuid4() for _ in range(6))
    opening=datetime(2026,10,1,tzinfo=timezone.utc);closing=datetime(2026,10,2,tzinfo=timezone.utc)
    req=ProjectionRequest(tenant,strategy,closing,closing,opening_cutoff=opening,mode='PERIOD')
    key=PositionKey(tenant,strategy,subject,currency,'UNITS','ACTIVELY_MANAGED_CERTIFICATE',Decimal(1),Decimal(1))
    bucket=PositionBucket(key,Decimal(10),Decimal(15),(trade,),(definition,))
    fill=Booking(trade,subject,currency,'UNITS',Decimal(5),Decimal(101),Decimal(1),Decimal(1),definition,'ACTIVELY_MANAGED_CERTIFICATE')
    projection=PositionProjection(req,(bucket,),(ExecutionEffect(key,fill,uuid4(),closing,closing),),(),(),0,True,'synthetic')
    result=attribute_projection(projection,{MarkKey(subject,opening):Decimal(100),MarkKey(subject,closing):Decimal(103)},currency)
    assert result.opening_value==1000 and result.closing_value==1545 and result.execution_value==505
    assert result.market_pnl==40  # 10 existing units earn 3; 5 new units earn 2.
