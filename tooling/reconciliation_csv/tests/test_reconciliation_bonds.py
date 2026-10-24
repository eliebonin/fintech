"""Reconciliation mapping tests use synthetic bonds, not customer exports."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
import pytest


def bond_bundle(maturity='2027-02-08', coupon='ZERO COUPON'):
    return SimpleNamespace(name='SAMPLE',digest='a'*64,bonds=[dict(instrument_id='40',
        id_isin='GB00EXAMPLE01',security_des='Example gilt',cpn_typ=coupon,cpn='3.75' if coupon=='FIXED' else '0',
        issue_dt='2026-08-10',maturity='2027-02-08',crncy='GBP',redemp_val='100.0',
        par_amt='0.01',cpn_freq='2',day_cnt_des='ACT/ACT',px_dirty_clean='CLEAN')],
        tables={'all_instruments':[dict(instrument_id='40',maturity_date=maturity,currency='GBP',
            instrument_type='BOND',isin='GB00EXAMPLE01')],
            'trades':[dict(instrument_id='40',trade_datetime_utc='2026-08-11 00:00:00')]})


def test_fraction_of_par_conversion_preserves_quantity_and_original_quote():
    from tooling.reconciliation_csv.reconciliation_bonds import percentage_price
    converted=percentage_price('0.99809')
    assert converted==dict(sourceValue='0.99809',value='99.809000000000',
        operation='MULTIPLY_BY_100',rounding='ROUND_HALF_EVEN_12DP',rounded=False)
    assert percentage_price('0.9967199999999999')['value']=='99.672000000000'
    assert percentage_price('0.9967199999999999')['rounded'] is True
    for value in ('NaN','Infinity','-1'):
        with pytest.raises(ValueError):percentage_price(value)


def test_conflicting_maturity_is_not_silently_selected():
    from tooling.reconciliation_csv.reconciliation_bonds import bond_requests
    row=bond_requests(bond_bundle('2027-04-06'),{'GBP':uuid4()},uuid4(),uuid4())[0]
    assert row['sourceId']=='40' and 'MATURITY_CONFLICT' in row['issues']
    assert row['request'].maturity_date is None


def test_fixed_coupon_is_fractional_and_unspecified_act_act_stays_pending():
    from tooling.reconciliation_csv.reconciliation_bonds import bond_requests
    row=bond_requests(bond_bundle(coupon='FIXED'),{'GBP':uuid4()},uuid4(),uuid4())[0]
    req=row['request']
    assert req.coupon_rate==Decimal('0.0375')
    assert req.coupon_frequency_per_year==2
    assert req.day_count_convention is None
    assert row['issues']==['DAY_COUNT_VARIANT_REQUIRED']
    assert req.par_amount is None  # 0.01 is not assumed to be a native bond unit.
    assert req.effective_from==date(2026,8,10)


def test_zero_coupon_request_retains_source_identity_without_inventing_issuer():
    from tooling.reconciliation_csv.reconciliation_bonds import bond_requests
    currency,source,payload=uuid4(),uuid4(),uuid4()
    row=bond_requests(bond_bundle(),{'GBP':currency},source,payload)[0]
    req=row['request']
    assert row['issues']==[] and req.coupon_type=='ZERO'
    assert req.base_currency_id==currency and req.maturity_date==date(2027,2,8)
    assert req.redemption_amount_per_par==Decimal('100')
    assert req.issuer_organisation_id is None
    assert req.source_system_id==source and req.source_payload_id==payload
    assert req.source_external_id=='40' and req.submission_mode=='AUTOMATED'


def test_conflicting_currency_and_nonbond_classification_cannot_be_approved():
    from tooling.reconciliation_csv.reconciliation_bonds import bond_requests
    bundle=bond_bundle();bundle.tables['all_instruments'][0]['currency']='USD'
    with pytest.raises(ValueError,match='currency'):bond_requests(bundle,{'GBP':uuid4()},uuid4(),uuid4())
    bundle=bond_bundle();bundle.tables['all_instruments'][0]['instrument_type']='FUND'
    with pytest.raises(ValueError,match='classification'):bond_requests(bundle,{'GBP':uuid4()},uuid4(),uuid4())


def test_zero_coupon_with_nonzero_rate_is_not_approved_as_zero():
    from tooling.reconciliation_csv.reconciliation_bonds import bond_requests
    bundle=bond_bundle();bundle.bonds[0]['cpn']='3.75'
    with pytest.raises(ValueError,match='Zero coupon'):bond_requests(bundle,{'GBP':uuid4()},uuid4(),uuid4())


def test_verified_gilt_review_is_bound_to_isin_and_preserves_original_proposal():
    from tooling.reconciliation_csv.reconciliation_bonds import reviewed_gilt_request
    from apps.reference_api.contracts import BondProposalRequest
    source=BondProposalRequest(canonicalName='Incorrect zero label',effectiveFrom='2024-01-11',
        couponType='FIXED',couponRate='0.0375',couponFrequencyPerYear=2,
        isin='GB00BPSNB460',sourceSystemId=uuid4(),sourcePayloadId=uuid4(),idempotencyKey='original')
    revised,evidence=reviewed_gilt_request(source)
    assert source.maturity_date is None and source.day_count_convention is None
    assert revised.maturity_date==date(2027,3,7)
    assert revised.day_count_convention=='ACT_ACT_ICMA'
    assert revised.canonical_name=='3.75% Treasury Gilt 2027'
    assert revised.source_payload_id==source.source_payload_id
    assert revised.idempotency_key!=source.idempotency_key
    assert evidence['reviewedOn']=='2026-10-23' and evidence['sources']
    assert evidence['dayCountMapping']=='INFERRED_FROM_DMO_QUASI_COUPON_FORMULA'
    bad=source.model_copy(update={'coupon_rate':Decimal('0.05')})
    with pytest.raises(ValueError,match='coupon'):reviewed_gilt_request(bad)
    bad=source.model_copy(update={'isin':'GB00EXAMPLE01'})
    with pytest.raises(ValueError,match='reviewed'):reviewed_gilt_request(bad)
