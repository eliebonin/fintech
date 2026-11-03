"""Rate exchange is its own strict contract, not an equity return profile."""
from copy import deepcopy
from decimal import Decimal as D
from uuid import uuid4
import pytest


def payload():
    gbp,usd,rate1,rate2,day1,day2=[str(uuid4()) for _ in range(6)]
    def leg(direction,rate,currency,notional,day,spread):
        return dict(direction=direction,rateReferenceId=rate,currencyId=currency,contractualNotional=notional,
            spread=spread,dayCountConventionId=day,interestCalculationMethod='Compounded overnight in arrears',
            observationDescription='Confirmation section 4',resetFrequency='QUARTERLY',paymentFrequency='QUARTERLY')
    return dict(schemaVersion=1,swapKind='RATE_EXCHANGE',contractualNotional='26000000',notionalCurrencyId=gbp,
        quoteCurrencyId=gbp,quoteFactor='1',effectiveDate='2026-09-01',maturityDate='2027-09-01',
        sourceReference='Synthetic confirmation',principalExchange='NONE',
        legs=[leg('PAY',rate1,usd,'34700000',day1,'0'),leg('RECEIVE',rate2,gbp,'26000000',day2,'0.00135')])


def test_rate_terms_round_trip_and_partial_notional_are_exact():
    from security_master_schema.rate_swap_terms import RateSwapTerms
    from security_master_schema.swap_terms import parse_swap_terms
    from apps.reference_api.swap_creation_contracts import SwapProposalRequest
    p=payload();terms=RateSwapTerms.model_validate(p)
    assert parse_swap_terms(terms.model_dump(mode='json',by_alias=True))==terms
    assert SwapProposalRequest(canonicalName='Synthetic two-leg rate swap',terms=p).terms==terms
    assert terms.booked_reference_notional(D('13000000'))==D('13000000')
    assert terms.leg_notional(terms.legs[0],D('13000000'))==D('17350000')
    assert terms.quantity_unit=='NOMINAL' and len(terms.legs)==2


@pytest.mark.parametrize('case',['same_direction','one_leg','missing_spread','float_notional','missing_source','bad_date','nonfinite','custom_without_evidence','pretend_performance'])
def test_incomplete_or_ambiguous_rate_contract_is_rejected(case):
    from security_master_schema.rate_swap_terms import RateSwapTerms
    p=payload()
    if case=='same_direction':p['legs'][1]['direction']='PAY'
    elif case=='one_leg':p['legs'].pop()
    elif case=='missing_spread':p['legs'][0].pop('spread')
    elif case=='float_notional':p['legs'][0]['contractualNotional']=34700000.0
    elif case=='missing_source':p['sourceReference']=' '
    elif case=='bad_date':p['maturityDate']=p['effectiveDate']
    elif case=='nonfinite':p['legs'][1]['spread']='NaN'
    elif case=='custom_without_evidence':p['legs'][0]['resetFrequency']='CUSTOM'
    else:p['returnBasis']='TOTAL'
    with pytest.raises(ValueError):RateSwapTerms.model_validate(p)


def test_ordinary_performance_swap_keeps_its_original_json_contract():
    from security_master_schema.swap_terms import GenericSwapTerms,parse_swap_terms
    from tests.test_swap_creation_rules import payload as performance
    terms=GenericSwapTerms.model_validate(performance())
    assert parse_swap_terms(terms.model_dump(mode='json',by_alias=True))==terms
    assert 'swapKind' not in terms.model_dump(mode='json',by_alias=True)
