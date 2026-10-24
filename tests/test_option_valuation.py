"""Contract-count option P&L, not underlying exposure or an option model."""
from decimal import Decimal as D
from uuid import UUID
import pytest
from tests.test_position_reconstruction import booked,request,OPEN,CLOSE,CURRENCY
from positions.reconstruction import reconstruct
from valuation.position_calculation import attribute_projection,required_marks,MarkKey


def option(n,quantity,when,price='23.8',**changes):
    return booked(n,quantity,when,price,**(dict(product_basis='OPTION',quantity_unit='CONTRACTS',unit_multiplier=D(100))|changes))


@pytest.mark.parametrize('quantity,expected',[('20','5936'),('-20','-5936')])
def test_option_multiplier_once_with_price_and_fx_changes(quantity,expected):
    p=reconstruct([option(1,quantity,OPEN)],request());subject=p.buckets[0].key.subject_id
    r=attribute_projection(p,{MarkKey(subject,OPEN):D('23.8'),MarkKey(subject,CLOSE):D(28)},UUID(int=200),
        {(CURRENCY,OPEN):D('.8'),(CURRENCY,CLOSE):D('.786')})
    assert r.market_pnl==D(expected)  # 20*100*(28*.786-23.8*.8)


def test_new_option_uses_execution_premium_not_previous_close():
    p=reconstruct([option(1,'20',CLOSE)],request());subject=p.buckets[0].key.subject_id
    assert len(required_marks(p))==1
    r=attribute_projection(p,{MarkKey(subject,CLOSE):D(28)},CURRENCY)
    assert r.market_pnl==8400 and r.execution_value==47600


def test_zero_premium_is_real_but_missing_or_negative_is_not_zero():
    p=reconstruct([option(1,'20',OPEN,'0')],request());subject=p.buckets[0].key.subject_id
    assert attribute_projection(p,{MarkKey(subject,OPEN):D(1),MarkKey(subject,CLOSE):D(0)},CURRENCY).market_pnl==-2000
    with pytest.raises(ValueError):attribute_projection(p,{MarkKey(subject,OPEN):D(1)},CURRENCY)
    with pytest.raises(ValueError):attribute_projection(p,{MarkKey(subject,OPEN):D(1),MarkKey(subject,CLOSE):D(-1)},CURRENCY)


def test_full_option_close_needs_only_opening_mark_and_keeps_pnl():
    p=reconstruct([option(1,'20',OPEN),option(2,'-20',CLOSE,'28')],request());subject=p.buckets[0].key.subject_id
    assert len(required_marks(p))==1
    assert attribute_projection(p,{MarkKey(subject,OPEN):D('23.8')},CURRENCY).market_pnl==8400


def test_partial_close_uses_actual_sale_premium_and_remaining_contracts():
    p=reconstruct([option(1,'20',OPEN),option(2,'-5',CLOSE,'26')],request());subject=p.buckets[0].key.subject_id
    r=attribute_projection(p,{MarkKey(subject,OPEN):D('23.8'),MarkKey(subject,CLOSE):D(28)},CURRENCY)
    assert r.market_pnl==7400 and p.buckets[0].closing_quantity==15


def test_quote_factor_applies_once_and_contracts_cannot_be_fractional():
    p=reconstruct([option(1,'20',OPEN,quote_factor=D(100))],request());subject=p.buckets[0].key.subject_id
    assert attribute_projection(p,{MarkKey(subject,OPEN):D(20),MarkKey(subject,CLOSE):D(25)},CURRENCY).market_pnl==100
    with pytest.raises(ValueError):reconstruct([option(1,'20.5',OPEN)],request())


def test_option_marks_bind_canonical_premium_identity_not_underlying():
    from valuation.product_inputs import option_mark_context
    from datetime import timedelta
    canonical=UUID(int=700)
    p=reconstruct([option(1,'20',OPEN,product_evidence=dict(instrumentId=str(canonical),optionPriceBasis='PREMIUM_POINTS',expiryDate='2026-12-18'))],request())
    subject,dimensions=option_mark_context(p,p.buckets[0].key.subject_id,CLOSE)
    assert subject==canonical and dict(dimensions)==dict(OPTION_PRICE_BASIS='PREMIUM_POINTS',PREMIUM_MULTIPLIER='100',QUOTE_FACTOR='1',QUANTITY_UNIT='CONTRACTS')
    with pytest.raises(ValueError,match='expiry'):option_mark_context(p,p.buckets[0].key.subject_id,CLOSE+timedelta(days=100))
