"""Synthetic test terms exercise existing contracts, never relaxed validators."""
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4
from decimal import Decimal
import pytest


def fixture():
    bundle=SimpleNamespace(name='SAMPLE',digest='b'*64,positions=[dict(instrument_id='10',quantity='123.4567')])
    instrument=dict(instrument_id='10',short_name='Example swap',price_type='unitlev',currency='USD',
        effective_date='2026-01-02',maturity_date='2027-01-04')
    source=dict(instrument_id='10',funded_instrument_id='11',funding_instrument_id='',notional='',
        leverage='2.8',floating_spread_bps='25',swap_payment_per_year='12',return_type='TR',funded_return_type='',funding_return_type='')
    ids={'11':uuid4(),'1396':uuid4(),'1048':uuid4()};currencies={'USD':uuid4()}
    counts={'ACT_360':uuid4(),'ACT_365F':uuid4()}
    return bundle,instrument,source,ids,currencies,uuid4(),counts


def test_missing_contract_terms_become_explicit_mockup_values_not_model_changes():
    from tooling.reconciliation_csv.reconciliation_products import swap_plan
    args=fixture();before=deepcopy(args[2]);plan=swap_plan(*args)
    terms=plan['request'].terms
    assert terms.quantity_unit=='UNITS' and terms.leverage==Decimal('2.8')
    assert terms.contractual_units==Decimal('123.4567')
    assert terms.notional_per_unit==100 and terms.contractual_notional==Decimal('12345.67')
    assert terms.funding_spread==Decimal('0.0025')
    assert terms.funding_reference_id==args[3]['1396']
    assert terms.funding_reset_frequency=='MONTHLY' and terms.funding_payment_frequency=='MONTHLY'
    assert terms.performance_reset_frequency=='MONTHLY'
    assert 'contractualNotional' in plan['assumptions'] and 'fundingReferenceId' in plan['assumptions']
    assert 'MOCKUP' in terms.source_reference and args[2]==before


def test_supplied_notional_and_funding_identity_survive_mockup_completion():
    from tooling.reconciliation_csv.reconciliation_products import swap_plan
    args=fixture();args[2].update(notional='2795656.78',funding_instrument_id='1048.0')
    plan=swap_plan(*args);terms=plan['request'].terms
    assert terms.contractual_notional==Decimal('2795656.78')
    assert terms.contractual_units*terms.notional_per_unit==terms.contractual_notional
    assert terms.funding_reference_id==args[3]['1048']
    assert 'contractualNotional' not in plan['assumptions'] and 'fundingReferenceId' not in plan['assumptions']
    assert terms.day_count_convention_id==args[6]['ACT_365F']


def test_nominal_swaps_keep_nominal_units_and_do_not_gain_unit_terms():
    from tooling.reconciliation_csv.reconciliation_products import swap_plan
    args=fixture();args[1]['price_type']='notional';args[2].update(notional='2600000',floating_spread_bps='0')
    terms=swap_plan(*args)['request'].terms
    assert terms.quantity_unit=='NOMINAL' and terms.contractual_notional==2600000
    assert terms.contractual_units is None and terms.notional_per_unit is None
    assert terms.financing_treatment=='NONE' and terms.funding_reference_id is None


def test_missing_reference_or_invalid_frequency_fails_instead_of_becoming_zero():
    from tooling.reconciliation_csv.reconciliation_products import swap_plan
    args=fixture();args[2]['swap_payment_per_year']='7'
    with pytest.raises(ValueError,match='frequency'):swap_plan(*args)
    args=fixture();args[3].pop('11')
    with pytest.raises((KeyError,ValueError)):swap_plan(*args)


def product_bundle(tmp_path):
    import csv
    from datetime import date
    from tooling.reconciliation_csv.tests.test_reconciliation_bundle import sample
    from tooling.reconciliation_csv.reconciliation import load_bundle
    source=sample(tmp_path)
    tables={
        'all_instruments':[
            dict(instrument_id='10',instrument_type='DIVER OTC',short_name='Example swap',currency='GBP',price_type='unit',effective_date='2026-01-02',maturity_date='2027-01-04'),
            dict(instrument_id='11',instrument_type='INDEX',short_name='Example performance',currency='GBP',price_type='notional',effective_date='',maturity_date=''),
            dict(instrument_id='1048',instrument_type='INDEX',short_name='SONIA',currency='GBP',price_type='notional',effective_date='',maturity_date=''),
            dict(instrument_id='1396',instrument_type='INDEX',short_name='SOFR',currency='USD',price_type='notional',effective_date='',maturity_date=''),
            dict(instrument_id='20',instrument_type='CURRENCY',short_name='GBP',currency='GBP',price_type='unit',effective_date='',maturity_date=''),
        ],
        'currencies':[dict(currency_id='2',currency='GBP'),dict(currency_id='9',currency='SGD'),dict(currency_id='1',currency='USD')],
        'swaps':[dict(instrument_id='10',funded_instrument_id='11',funding_instrument_id='1048.0',
            notional='1000000',leverage='2',floating_spread_bps='10',swap_payment_per_year='4',return_type='TR',funded_return_type='TR',funding_return_type='')],
    }
    for kind,rows in tables.items():
        with (source/f'SAMPLE-2026-10-20-{kind}.csv').open('w',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    return load_bundle(source,'SAMPLE',date(2026,10,20),excluded_trade_ids={'exclude'})


def test_amc_maps_to_certificate_not_bond_or_fund():
    from tooling.reconciliation_csv.reconciliation_products import amc_seed_record
    b=SimpleNamespace(digest='c'*64,positions=[dict(instrument_id='1857',trade_datetime_utc='2024-09-16 12:30:00')])
    item=dict(instrument_id='1857',short_name='Example AMC',isin='XS0000000001',currency='USD')
    record=amc_seed_record(b,item)
    assert record['instrumentType']=='ACTIVELY_MANAGED_CERTIFICATE'
    assert record['displayName']=='Example AMC [AMC]'
    assert record['effectiveFrom']=='2024-09-16'
    assert record['isin']=='XS0000000001'
    assert 'etpKind' not in record and 'redemptionModel' not in record


def test_option_uses_first_observed_trade_not_erroneous_expiry_as_effective_start():
    from tooling.reconciliation_csv.reconciliation_products import normalized_option_request
    b=SimpleNamespace(digest='d'*64,positions=[dict(instrument_id='20265',trade_datetime_utc='2026-08-13 11:00:00',unit_multiplier='1.0')])
    item=dict(instrument_id='20265',short_name='SPX.202612.P.05800000',long_name='Put SPX Index @ 5800.0 - 2026-12-18',
        currency='USD',effective_date='2026-12-18',maturity_date='2026-12-18')
    req=normalized_option_request(b,item,uuid4(),uuid4())
    assert req.effective_from.isoformat()=='2026-08-13' and req.expiry_date.isoformat()=='2026-12-18'
    assert req.strike==5800 and req.premium_multiplier==1 and req.deliverable_units==1
    assert req.exercise_style=='EUROPEAN' and req.settlement_method=='CASH'
    assert 'mockup' in req.canonical_name


def additional_bundle(tmp_path):
    import csv
    from datetime import date
    from tooling.reconciliation_csv.reconciliation import load_bundle
    product_bundle(tmp_path)
    path=tmp_path/'SAMPLE-2026-10-20-all_instruments.csv'
    rows=list(csv.DictReader(path.read_text().splitlines()))
    fields=list(rows[0])+['isin','long_name','issuer']
    rows.extend([
        dict(instrument_id='1857',instrument_type='FUND',short_name='Example AMC',currency='USD',price_type='unit',isin='XS0000000001',issuer='Example issuer from source'),
        dict(instrument_id='20265',instrument_type='VANILLA',short_name='SPX.202612.P.05800000',currency='USD',price_type='unit',
            effective_date='2026-12-18',maturity_date='2026-12-18',long_name='Put SPX Index @ 5800.0 - 2026-12-18')])
    with path.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    path=tmp_path/'SAMPLE-2026-10-20-trades.csv'
    trades=list(csv.DictReader(path.read_text().splitlines()))
    fields=list(trades[0])+['unit_multiplier']
    for identifier,day in (('1857','2024-09-16'),('20265','2026-08-13')):
        trades.append(dict(trade_id='open-'+identifier,instrument_id=identifier,strategy_id='2',trade_type='Investment',
            trade_datetime_utc=day+' 12:00:00',quantity='2000',price='23.8',trade_currency='USD',counterparty_id='21',unit_multiplier='1'))
    with path.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(trades)
    return load_bundle(tmp_path,'SAMPLE',date(2026,10,20),excluded_trade_ids={'exclude'},amc_ids={'1857'})
