"""Synthetic source variants; no private portfolio rows in tests."""
from datetime import date
import pytest
from .test_reconciliation_bundle import sample, load


def test_identifier_fx_variant_retains_bytes_and_resolves_codes(tmp_path):
    from tooling.reconciliation_csv.reconciliation import load_bundle, retain_files
    root=sample(tmp_path)
    (root/'SAMPLE-2026-10-20-fx_rates.csv').unlink()
    raw=b'id,date,base_currency_id,quote_currency_id,rate\n7,2026-10-20,2.0,9,1.7\n'
    (root/'SAMPLE-2026-10-20-fx.csv').write_bytes(raw)
    schedule=b'instrument_id,payment_date,coupon_amount,principal_amount,coupon_pct,principal_pct\n10,2027-01-01,5,100,0.05,1\n'
    (root/'SAMPLE-2026-10-20-bond_schedules.csv').write_bytes(schedule)
    b=load_bundle(root,'SAMPLE',date(2026,10,20),excluded_trade_ids={'exclude'},amc_ids={'10'},include_details=True)
    assert b.tables['fx_rates'][0]['base_currency']=='GBP'
    assert b.tables['fx_rates'][0]['quote_currency']=='SGD'
    assert b.files['fx_rates']==raw
    assert b.files['bond_schedules']==schedule
    assert b.manifest['sourceSchemaVariants']['fx_rates']=='CURRENCY_IDS_FX_FILE'
    retained=retain_files(b,root/'evidence')
    assert retained['fx_rates'].read_bytes()==raw
    assert b.digest==load_bundle(root,'SAMPLE',date(2026,10,20),excluded_trade_ids={'exclude'},amc_ids={'10'},include_details=True).digest


def test_unknown_fx_id_is_rejected(tmp_path):
    root=sample(tmp_path)
    (root/'SAMPLE-2026-10-20-fx_rates.csv').unlink()
    (root/'SAMPLE-2026-10-20-fx.csv').write_text('date,base_currency_id,quote_currency_id,rate\n2026-10-20,999,2,1\n')
    with pytest.raises(ValueError,match='Unknown FX currency'):load(root)


def test_original_variant_manifest_has_no_new_identity_fields(tmp_path):
    b=load(sample(tmp_path))
    assert 'sourceSchemaVariants' not in b.manifest
    assert set(b.files)=={'strategy_info','currencies','trades','all_instruments','bonds','swaps','prices','fx_rates','cash_balances','accrued_interests'}
