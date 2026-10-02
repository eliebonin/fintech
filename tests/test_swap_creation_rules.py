from decimal import Decimal
from uuid import uuid4
import pytest
from pydantic import ValidationError

def payload(**changes):
    currency=str(uuid4())
    return dict(performanceReferenceId=str(uuid4()),contractualNotional='1000000',notionalCurrencyId=currency,
        effectiveDate='2026-10-01',maturityDate='2029-10-01',performanceDirection='RECEIVE',returnBasis='TOTAL',
        returnProfileId=str(uuid4()),quoteCurrencyId=currency,quoteFactor='100',sourceReference='Confirmation section 3',
        performanceResetFrequency='AT_MATURITY',redemptionRule='TERMINATE',financingTreatment='NONE')|changes

def terms(**changes):
    from apps.reference_api.swap_creation_contracts import GenericSwapTerms
    return GenericSwapTerms.model_validate(payload(**changes))

def funding(**changes):
    return dict(fundingReferenceId=str(uuid4()),fundingSpread='0.015',fundingNotionalBasis='BOOKED_NOMINAL',
        dayCountConventionId=str(uuid4()),interestCalculationMethod='Compounded daily in arrears',
        fundingObservationDescription='Five business day observation lag',fundingResetFrequency='MONTHLY',
        fundingPaymentFrequency='QUARTERLY',financingTreatment='SEPARATE')|changes

def test_no_funding_and_round_trip():
    from apps.reference_api.swap_creation_contracts import GenericSwapTerms,SwapProposalRequest
    value=terms()
    assert value.leverage==Decimal('1') and value.funding_reference_id is None
    assert value.model_dump(mode='json',by_alias=True)['contractualNotional']=='1000000'
    assert GenericSwapTerms.model_validate_json(value.model_dump_json()).quote_factor==Decimal('100')
    assert SwapProposalRequest(canonicalName='Swap',terms=value).terms==value

@pytest.mark.parametrize('field',['contractualNotional','leverage','quoteFactor'])
@pytest.mark.parametrize('bad',['0','-1','NaN','Infinity','-Infinity',1.1])
def test_unsafe_decimals(field,bad):
    with pytest.raises(ValidationError): terms(**{field:bad})

@pytest.mark.parametrize('changes',[dict(maturityDate='2026-10-01'),dict(maturityDate='2025-01-01'),
    dict(quoteCurrencyId=str(uuid4())),dict(sourceReference=' '),dict(unexpected='x')])
def test_invalid_core(changes):
    with pytest.raises(ValidationError): terms(**changes)

@pytest.mark.parametrize('field',['fundingSpread','fundingNotionalBasis','dayCountConventionId',
    'interestCalculationMethod','fundingObservationDescription','fundingResetFrequency','fundingPaymentFrequency'])
def test_no_or_incomplete_funding(field):
    with pytest.raises(ValidationError): terms(**{field:funding()[field]})
    if field!='fundingObservationDescription':
        values=funding();values.pop(field)
        with pytest.raises(ValidationError): terms(**values)

def test_spread_units_and_precision():
    from apps.reference_api.swap_creation_contracts import spread_from_basis_points
    assert spread_from_basis_points('150')==Decimal('0.015')
    assert terms(**funding()).funding_spread==Decimal('0.015')
    assert terms(**funding(fundingSpread='-0.0025')).funding_spread==Decimal('-0.0025')
    for bad in ['NaN','Infinity','0.000000001',0.015]:
        with pytest.raises(ValidationError): terms(**funding(fundingSpread=bad))

def test_double_funding_evidence():
    for extra in [{},dict(additionalFundingAcknowledged=True),dict(additionalFundingEvidence='Source 4')]:
        with pytest.raises(ValidationError):
            terms(returnBasis='EXCESS',**funding(financingTreatment='EMBEDDED_AND_SEPARATE'),**extra)
    assert terms(returnBasis='EXCESS',**funding(financingTreatment='EMBEDDED_AND_SEPARATE'),
        additionalFundingAcknowledged=True,additionalFundingEvidence='Source 4').additional_funding_acknowledged
    assert terms(returnBasis='EXCESS',financingTreatment='EMBEDDED').funding_reference_id is None

@pytest.mark.parametrize('changes',[dict(returnBasis='EXCESS'),dict(financingTreatment='SEPARATE'),
    dict(additionalFundingAcknowledged=True),dict(continuationDescription='Reinvest'),
    dict(performanceResetFrequency='CUSTOM'),dict(redemptionRule='CONTINUE')])
def test_inconsistent_or_unsourced_rules(changes):
    with pytest.raises(ValidationError): terms(**changes)

def test_sourced_custom_rules():
    assert terms(performanceResetFrequency='CUSTOM',performanceScheduleDescription='Source 5 dates',
        redemptionRule='CONTINUE',continuationDescription='Source 6 cash proceeds').redemption_rule=='CONTINUE'
    with pytest.raises(ValidationError): terms(**funding(fundingResetFrequency='CUSTOM'))
    assert terms(**funding(fundingResetFrequency='CUSTOM',fundingResetScheduleDescription='Source 7 dates')).funding_reset_frequency=='CUSTOM'
