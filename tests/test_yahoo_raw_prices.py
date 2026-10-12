"""Catch reversed factors, split-day double adjustment and incomplete coverage."""
from datetime import date, datetime, timezone
from decimal import Decimal
import json
import pytest
from sqlalchemy import select, func
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from tests.test_market_data_ingestion import setup_dataset, fixture_payload, ingest


def delivery(start='2022-06-03', end='2022-06-06', *, split=True, anchor='2022-06-06'):
    stamp=int(datetime.fromisoformat(anchor+'T20:00:00+00:00').timestamp())
    event_stamp=int(datetime(2022,6,6,13,30,tzinfo=timezone.utc).timestamp())
    payload={'chart':{'result':[{'meta':{'symbol':'AMZN','currency':'USD','exchangeName':'NMS',
        'exchangeTimezoneName':'America/New_York','instrumentType':'EQUITY','regularMarketTime':stamp},
        'timestamp':[], 'indicators':{'quote':[{'close':[]}]},
        'events':{'splits':{str(event_stamp):{'date':event_stamp,'numerator':20,'denominator':1}} if split else {}}}], 'error':None}}
    return dict(run_id='sample',source_payload_id='payload',raw_payload=json.dumps(payload),
        received_at_utc=datetime(2022,6,7,8,tzinfo=timezone.utc),
        report={'request':dict(symbol='AMZN',start=start,end=end)})


def assess(run, windows=None):
    from market_data.providers.yahoo.raw_prices import assess_basis
    from market_data.contracts import ListingContext
    return assess_basis(run, windows or [run], ListingContext('USD','XNAS','America/New_York'))


def test_amzn_before_split_is_multiplied_twenty_but_split_day_is_not():
    from market_data.price_basis import normalise_as_traded
    evidence=assess(delivery())
    before=normalise_as_traded(Decimal('122.35'),'SPLIT_ADJUSTED',
        dict(evidence,marketDate='2022-06-03'),allow_split_conversion=True)
    on_day=normalise_as_traded(Decimal('124.79'),'SPLIT_ADJUSTED',
        dict(evidence,marketDate='2022-06-06'),allow_split_conversion=True)
    assert before.valuation_value==Decimal('2447')
    assert on_day.valuation_value==Decimal('124.79')


def test_history_window_before_current_anchor_requires_missing_suffix():
    with pytest.raises(ValueError,match='SPLIT_COVERAGE_GAP'):
        assess(delivery(end='2022-06-03',split=False))
    original=delivery(end='2022-06-03',split=False)
    suffix=delivery(start='2022-06-04')
    assert assess(original,[original,suffix])['splits']==[
        dict(date='2022-06-06',numerator='20',denominator='1')]


def test_complete_no_split_window_proves_factor_one():
    from market_data.price_basis import normalise_as_traded
    evidence=assess(delivery(split=False))
    result=normalise_as_traded(Decimal('100'),'SPLIT_ADJUSTED',dict(evidence,marketDate='2022-06-03'),allow_split_conversion=True)
    assert result.valuation_value==Decimal('100') and result.evidence['factor']=='1'


def test_multiple_splits_including_reverse_split_use_cumulative_ratio():
    from market_data.price_basis import normalise_as_traded
    run=delivery(start='2022-06-01');payload=json.loads(run['raw_payload'])
    stamp=int(datetime(2022,6,2,13,30,tzinfo=timezone.utc).timestamp())
    payload['chart']['result'][0]['events']['splits'][str(stamp)]={'date':stamp,'numerator':1,'denominator':10}
    run['raw_payload']=json.dumps(payload)
    proof=dict(assess(run),marketDate='2022-06-01')
    assert normalise_as_traded(Decimal('100'),'SPLIT_ADJUSTED',proof,allow_split_conversion=True).valuation_value==Decimal('200')


def test_derived_raw_keeps_normalization_evidence_without_adjusting_twice():
    from market_data.price_basis import normalise_as_traded
    proof=dict(method='DERIVED_SPLIT_ONLY',sourceValue='122.35',valuationValue='2447',factor='0.05')
    result=normalise_as_traded(Decimal('2447'),'RAW',proof,allow_split_conversion=True)
    assert result.valuation_value==Decimal('2447')
    assert result.evidence['derivation']['sourceValue']=='122.35'


def test_event_only_suffix_is_retained_without_publishing_an_intraday_price():
    from market_data.providers.yahoo.raw_prices import retain_event_coverage
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            dataset,namespace,_=setup_dataset(c)
            payload=fixture_payload()
            report=retain_event_coverage(c,dataset_id=dataset,namespace_id=namespace,symbol='AAPL',
                raw_payload=payload,start=date(2026,10,5),end=date(2026,10,6),
                received_at=datetime(2026,10,7,8,tzinfo=timezone.utc))
            assert report['eventCoverageOnly'] is True
            assert c.scalar(select(func.count()).select_from(m.market_data_observation).where(m.market_data_observation.c.dataset_id==dataset))==0
            assert c.scalar(select(m.source_payload.c.processing_status).where(m.source_payload.c.source_payload_id==report['sourcePayloadId']))=='VALIDATED'
        finally: tx.rollback()


@pytest.mark.parametrize('mutation',['missing_anchor','future_anchor','bad_split','wrong_symbol'])
def test_invalid_identity_anchor_or_split_cannot_certify_raw(mutation):
    run=delivery();payload=json.loads(run['raw_payload']);result=payload['chart']['result'][0]
    if mutation=='missing_anchor': result['meta'].pop('regularMarketTime')
    if mutation=='future_anchor': result['meta']['regularMarketTime']=int(datetime(2022,6,9,tzinfo=timezone.utc).timestamp())
    if mutation=='bad_split': next(iter(result['events']['splits'].values()))['numerator']=0
    if mutation=='wrong_symbol': result['meta']['symbol']='OTHER'
    run['raw_payload']=json.dumps(payload)
    with pytest.raises(ValueError): assess(run)


def test_raw_publication_preserves_source_and_is_replay_safe_for_later_ingestion():
    from market_data.providers.yahoo.raw_prices import normalize_dataset
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            dataset,namespace,listing=setup_dataset(c)
            payload=json.loads(fixture_payload())
            payload['chart']['result'][0]['meta']['regularMarketTime']=1791316800
            raw=json.dumps(payload)
            first=ingest(c,dataset,namespace,'raw-source-1',raw)
            report=normalize_dataset(c,dataset,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'],symbols=['AAPL'])
            assert report['rawCreated']==2 and report['blocked']==0
            rows=c.execute(select(m.market_data_observation).where(m.market_data_observation.c.dataset_id==dataset)).mappings().all()
            assert len(rows)==6
            raw_rows=[r for r in rows if r['value_basis']=='RAW']
            assert {r['value'] for r in raw_rows}=={Decimal('250.25'),Decimal('252')}
            source_payload=c.scalar(select(m.market_data_ingestion_run.c.source_payload_id).where(m.market_data_ingestion_run.c.run_id==first['runId']))
            assert all(r['source_payload_id']==source_payload for r in raw_rows)
            assert normalize_dataset(c,dataset,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'],symbols=['AAPL'])['rawCreated']==0
            # Derived CLOSE must not cause the source publisher to overwrite RAW,
            # select an ambiguous CLOSE, or reject normal split-adjusted ingestion.
            assert ingest(c,dataset,namespace,'raw-source-2',raw)['duplicates']==4
            # A later source correction produces an append-only RAW correction;
            # reprocessing the old retained run cannot put the old price back.
            payload['chart']['result'][0]['indicators']['quote'][0]['close'][0]=251
            ingest(c,dataset,namespace,'raw-source-3',json.dumps(payload))
            assert normalize_dataset(c,dataset,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'],symbols=['AAPL'])['rawCreated']==1
            changed=c.execute(select(m.market_data_observation).where(m.market_data_observation.c.dataset_id==dataset,
                m.market_data_observation.c.value_basis=='RAW',m.market_data_observation.c.supersedes_observation_id.is_not(None))).mappings().one()
            assert changed['value']==Decimal('251')
            assert normalize_dataset(c,dataset,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'],symbols=['AAPL'])['rawCreated']==0
        finally: tx.rollback()


def test_no_store_right_cannot_create_raw_or_proofs():
    from market_data.providers.yahoo.raw_prices import normalize_dataset
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            dataset,namespace,_=setup_dataset(c)
            ingest(c,dataset,namespace)
            c.execute(m.licence_activity_grant.delete().where(m.licence_activity_grant.c.activity=='STORE'))
            with pytest.raises(PermissionError,match='STORE'):
                normalize_dataset(c,dataset,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'])
            assert c.scalar(select(func.count()).select_from(m.market_data_observation).where(
                m.market_data_observation.c.dataset_id==dataset,m.market_data_observation.c.value_basis=='RAW'))==0
        finally: tx.rollback()
