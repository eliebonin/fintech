"""Synthetic bundle rules; never read production exports in automated tests."""
import csv
from datetime import date
from io import StringIO
import pytest


def sample(tmp_path):
    tables = {
        'strategy_info': [{'strategy_id':'2','strategy_currency_id':'2','strategy_name':'SAMPLE','active':'True'}],
        'currencies': [{'currency_id':'2','currency':'GBP'},{'currency_id':'9','currency':'SGD'}],
        'trades': [
            dict(trade_id='open',instrument_id='10',strategy_id='2',trade_type='Investment',trade_datetime_utc='2026-10-19 00:00:00',settlement_date='2026-10-21',quantity='1234567890123456.123456789012',price='100',trade_currency='GBP',counterparty_id='21'),
            dict(trade_id='reset',instrument_id='20',strategy_id='2',trade_type='RESET',trade_datetime_utc='2026-10-20 00:00:00',quantity='-10.25',price='1',trade_currency='GBP',counterparty_id='21'),
            dict(trade_id='exclude',instrument_id='30',strategy_id='2',trade_type='FWD HEDGING',trade_datetime_utc='2026-10-20 00:00:00',quantity='1',price='1',trade_currency='GBP',counterparty_id='21')],
        'all_instruments': [dict(instrument_id='10',instrument_type='FUND',currency='GBP'),dict(instrument_id='20',instrument_type='CURRENCY',currency='GBP'),dict(instrument_id='30',instrument_type='FXFWD',currency='GBP')],
        'bonds': [dict(instrument_id='10')],
        'swaps': [],
        'prices': [dict(instrument_id='10',date='2026-10-20',price='100.123456789012')],
        'fx_rates': [dict(date='2026-10-20',base_currency='GBP',quote_currency='SGD',rate='1.7')],
        'cash_balances': [dict(trade_id='cash',instrument_id='99',trade_datetime_utc='2026-10-20',trade_currency='SGD',counterparty_id='21',quantity='5')],
        'accrued_interests': [],
    }
    for name, rows in tables.items():
        fields=list(rows[0]) if rows else ['instrument_id']
        out=StringIO(newline='');writer=csv.DictWriter(out,fieldnames=fields);writer.writeheader();writer.writerows(rows)
        (tmp_path/f'SAMPLE-2026-10-20-{name}.csv').write_bytes(out.getvalue().encode('utf-8'))
    return tmp_path


def load(path):
    from tooling.reconciliation_csv.reconciliation import load_bundle
    return load_bundle(path,'SAMPLE',date(2026,10,20),excluded_trade_ids={'exclude'},amc_ids={'10'})


def test_exclusion_reset_and_amc_are_separate_from_positions(tmp_path):
    bundle=load(sample(tmp_path))
    assert [r['trade_id'] for r in bundle.positions]==['open']
    assert [r['trade_id'] for r in bundle.flows]==['reset']
    assert bundle.positions[0]['quantity']=='1234567890123456.123456789012'
    assert bundle.flows[0]['quantity']=='-10.25'
    assert bundle.bonds==[]
    assert bundle.manifest['amcSourceIds']==['10']
    assert bundle.manifest['excludedTradeIds']==['exclude']
    assert bundle.manifest['requiredCurrencies']==['GBP','SGD']
    assert bundle.manifest['unmappedOrganisationIds']==['21']


def test_normalization_does_not_mutate_source_files_and_receipt_is_stable(tmp_path):
    from tooling.reconciliation_csv.reconciliation import retain_files
    source=sample(tmp_path);before={p.name:p.read_bytes() for p in source.glob('*.csv')}
    first=load(source);second=load(source)
    assert first.digest==second.digest
    retained=retain_files(first,tmp_path/'retained')
    assert retain_files(first,tmp_path/'retained')==retained
    assert {p.name:p.read_bytes() for p in source.glob('*.csv')}==before
    assert all(path.read_bytes()==first.files[kind] for kind,path in retained.items() if kind!='manifest')
    retained['prices'].write_bytes(b'changed')
    with pytest.raises(ValueError,match='Retained file differs'):retain_files(first,tmp_path/'retained')


def test_future_accruals_are_rejected_not_silently_loaded(tmp_path):
    source=sample(tmp_path)
    (source/'SAMPLE-2026-10-20-accrued_interests.csv').write_text('trade_id,instrument_id,value_date,trade_daily_accrual_amount\nopen,10,2026-10-21,1\n')
    with pytest.raises(ValueError,match='after bundle cutoff'):load(source)


def test_wrong_strategy_and_duplicate_trade_ids_fail_before_writes(tmp_path):
    source=sample(tmp_path);path=source/'SAMPLE-2026-10-20-trades.csv'
    text=path.read_text();path.write_text(text.replace('open,10,2,','open,10,99,'))
    with pytest.raises(ValueError,match='strategy'):load(source)
    path.write_text(text+text.splitlines()[1]+'\n')
    with pytest.raises(ValueError,match='Duplicate trade'):load(source)


def test_unknown_trade_instrument_is_not_guessed(tmp_path):
    source=sample(tmp_path);path=source/'SAMPLE-2026-10-20-trades.csv'
    path.write_text(path.read_text().replace('open,10,2,','open,404,2,'))
    with pytest.raises(ValueError,match='Missing instrument'):load(source)


def with_activity(source, *, flag='False'):
    path=source/'SAMPLE-2026-10-20-trades.csv'
    rows=list(csv.DictReader(StringIO(path.read_text(encoding='utf-8'))))
    for row in rows:row['active']='True'
    rows.extend([dict(rows[0],trade_id='inactive-investment',active=flag),
                 dict(rows[1],trade_id='inactive-reset',active=flag)])
    out=StringIO(newline='');writer=csv.DictWriter(out,fieldnames=list(rows[0]))
    writer.writeheader();writer.writerows(rows)
    path.write_text(out.getvalue(),encoding='utf-8')
    return path


def test_inactive_positions_and_flows_are_evidence_only(tmp_path):
    source=sample(tmp_path);path=with_activity(source);original=path.read_bytes()
    bundle=load(source)
    assert [r['trade_id'] for r in bundle.positions]==['open']
    assert [r['trade_id'] for r in bundle.flows]==['reset']
    assert bundle.manifest['inactiveTradeIds']==['inactive-investment','inactive-reset']
    assert len(bundle.tables['trades'])==5
    assert bundle.files['trades']==original==path.read_bytes()


@pytest.mark.parametrize('flag',['','unknown','0','1'])
def test_unknown_activity_is_rejected_when_column_is_present(tmp_path,flag):
    source=sample(tmp_path);with_activity(source,flag=flag)
    with pytest.raises(ValueError,match='activity'):load(source)


def test_inactive_accruals_are_retained_but_not_aggregated(tmp_path):
    from tooling.reconciliation_csv.reconciliation_accruals import aggregate_accruals
    source=sample(tmp_path);with_activity(source,flag=' false ')
    path=source/'SAMPLE-2026-10-20-accrued_interests.csv'
    path.write_text('trade_id,instrument_id,value_date,trade_daily_accrual_amount\n'
        'open,10,2026-10-20,2.12\ninactive-investment,10,2026-10-20,99\n',encoding='utf-8')
    bundle=load(source);result=aggregate_accruals(bundle)
    assert len(bundle.tables['accrued_interests'])==2
    assert len(result)==1 and result[0]['normalization']['value']=='2.120000000000'
    assert [r['trade_id'] for r in result[0]['originalRows']]==['open']
    path.write_text(path.read_text(encoding='utf-8')+'unknown,10,2026-10-20,99\n',encoding='utf-8')
    with pytest.raises(ValueError,match='unavailable position'):load(source)
