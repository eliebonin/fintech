"""Source-only completion assumptions never redefine native swap semantics."""
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4
import pytest


def bundle():
    data=dict(all_instruments=[dict(instrument_id='1',unique_identifier='ASWAP_TEST',instrument_type='ASWAP',currency='GBP',maturity_date='2027-11-15'),
        dict(instrument_id='2',unique_identifier='ASWAP_TESTUSD',instrument_type='ASWAP',currency='USD',maturity_date='2027-11-15'),
        dict(instrument_id='3',unique_identifier='USD overnight',currency='USD',instrument_type='INDEX'),dict(instrument_id='4',unique_identifier='GBP overnight',currency='GBP',instrument_type='INDEX')],
        swaps=[dict(instrument_id='1',funding_instrument_id='3.0',funded_instrument_id='',floating_spread_bps='0',swap_payment_per_year='4',leverage='-1'),
            dict(instrument_id='1',funding_instrument_id='4.0',funded_instrument_id='',floating_spread_bps='13.5',swap_payment_per_year='4',leverage='1')])
    positions=[dict(instrument_id=i,trade_id='source-'+i,unique_identifier=code,trade_currency=currency,quantity=q,price='1',quote_factor='1',unit_multiplier='1',price_type='notional',trade_datetime_utc='2026-10-01 12:30:00',settlement_date='2026-10-05')
        for i,code,currency,q in [('1','ASWAP_TEST','GBP','26000000'),('2','ASWAP_TESTUSD','USD','-34700000')]]
    return SimpleNamespace(tables=data,positions=positions,digest='synthetic-bundle')


def test_rate_plan_retains_companion_notional_and_separate_source_identity():
    from tooling.reconciliation_csv.fcpgf_rate_swaps import rate_plan
    b=bundle();before=deepcopy(b)
    refs={str(i):uuid4() for i in (1,2,3,4)};ccy={c:uuid4() for c in ('GBP','USD')};days={c:uuid4() for c in ('ACT_360','ACT_365F')}
    terms,evidence=rate_plan(b,'1',refs,ccy,days)
    assert terms.swap_kind=='RATE_EXCHANGE' and terms.quote_currency_id==ccy['GBP']
    assert [(leg.direction,leg.currency_id,str(leg.contractual_notional),str(leg.spread)) for leg in terms.legs]==[
        ('PAY',ccy['USD'],'34700000.000000000000','0'),('RECEIVE',ccy['GBP'],'26000000.000000000000','0.00135')]
    assert evidence['companionInstrumentId']=='2' and terms.principal_exchange=='UNSPECIFIED'
    assert b.tables==before.tables and b.positions==before.positions
    b.positions.pop()
    with pytest.raises(ValueError):rate_plan(b,'1',refs,ccy,days)
