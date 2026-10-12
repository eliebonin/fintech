"""FX direction, closed-bar cutoffs, DST and immutable source lineage."""
from datetime import date,datetime,timezone
from decimal import Decimal
import pytest

def chart(times,values,interval='5m'):
    return {'chart':{'error':None,'result':[{'meta':{'symbol':'EURGBP=X','currency':'GBP','exchangeName':'CCY','instrumentType':'CURRENCY','exchangeTimezoneName':'Europe/London','dataGranularity':interval},'timestamp':[int(datetime.fromisoformat(t).timestamp()) for t in times],'indicators':{'quote':[{'close':values}]}}]}}

def parser():
    from market_data.providers.yahoo.fx_adapter import parse_fx
    return parse_fx

def test_cutoff_uses_closed_bar_and_not_the_bar_starting_at_cutoff():
    data=chart(['2026-10-07T14:55:00+00:00','2026-10-07T15:00:00+00:00','2026-10-07T19:55:00+00:00'],[.85,.99,.86])
    points,rejected=parser()(data,symbol='EURGBP=X',start=date(2026,10,7),end=date(2026,10,7),received_at=datetime(2026,10,8,tzinfo=timezone.utc),interval='5m')
    assert not rejected
    assert [(p.label,p.value,p.observed_at.isoformat()) for p in points]==[('UK',Decimal('0.850000000000'),'2026-10-07T15:00:00+00:00'),('US',Decimal('0.860000000000'),'2026-10-07T20:00:00+00:00')]
    assert points[0].source_at.isoformat()=='2026-10-07T14:55:00+00:00'

def test_missing_exact_cutoff_bar_is_not_carried_forward():
    data=chart(['2026-10-07T14:50:00+00:00'],[.85])
    points,rejected=parser()(data,symbol='EURGBP=X',start=date(2026,10,7),end=date(2026,10,7),received_at=datetime(2026,10,8,tzinfo=timezone.utc),interval='5m')
    assert points==[] and {r['cutoff'] for r in rejected}=={'UK','US'}

def test_cutoff_uses_zone_rules_during_uk_us_dst_mismatch():
    data=chart(['2026-10-28T15:55:00+00:00','2026-10-28T19:55:00+00:00'],[.85,.86])
    points,_=parser()(data,symbol='EURGBP=X',start=date(2026,10,28),end=date(2026,10,28),received_at=datetime(2026,10,29,tzinfo=timezone.utc),interval='5m')
    assert [p.observed_at.hour for p in points]==[16,20]

def test_hourly_history_uses_hour_ending_at_cut_not_the_following_hour():
    data=chart(['2026-10-07T14:00:00+00:00','2026-10-07T15:00:00+00:00','2026-10-07T19:00:00+00:00'],[.85,.99,.86],interval='1h')
    points,rejected=parser()(data,symbol='EURGBP=X',start=date(2026,10,7),end=date(2026,10,7),received_at=datetime(2026,10,8,tzinfo=timezone.utc),interval='1h')
    assert not rejected
    assert [p.value for p in points]==[Decimal('0.850000000000'),Decimal('0.860000000000')]
    assert (points[0].observed_at-points[0].source_at).total_seconds()==3600

def test_daily_fx_is_unadjusted_and_has_no_claimed_named_cutoff():
    data=chart(['2026-10-06T23:00:00+00:00'],[.84819],interval='1d')
    points,rejected=parser()(data,symbol='EURGBP=X',start=date(2026,10,7),end=date(2026,10,7),received_at=datetime(2026,10,8,tzinfo=timezone.utc),interval='1d')
    assert not rejected and points[0].label=='EOD' and points[0].market_date==date(2026,10,7)
    assert points[0].value==Decimal('0.848190000000')

def test_usd_daily_canonical_yahoo_alias_requires_verified_direction():
    data=chart(['2026-10-06T23:00:00+00:00'],[.75],interval='1d')
    data['chart']['result'][0]['meta'].update(symbol='GBP=X',longName='USD/GBP')
    points,_=parser()(data,symbol='USDGBP=X',start=date(2026,10,7),end=date(2026,10,7),received_at=datetime(2026,10,8,tzinfo=timezone.utc),interval='1d')
    assert points[0].value==Decimal('0.750000000000')
    data['chart']['result'][0]['meta']['longName']='GBP/USD'
    with pytest.raises(ValueError,match='identity'):
        parser()(data,symbol='USDGBP=X',start=date(2026,10,7),end=date(2026,10,7),received_at=datetime(2026,10,8,tzinfo=timezone.utc),interval='1d')

@pytest.mark.parametrize('field,value',[('symbol','GBPEUR=X'),('instrumentType','EQUITY'),('currency','EUR')])
def test_wrong_direction_and_instrument_type_are_rejected(field,value):
    data=chart(['2026-10-07T14:55:00+00:00'],[.85])
    data['chart']['result'][0]['meta'][field]=value
    with pytest.raises(ValueError,match='identity'):
        parser()(data,symbol='EURGBP=X',start=date(2026,10,7),end=date(2026,10,7),received_at=datetime(2026,10,8,tzinfo=timezone.utc),interval='5m')

def test_fx_publication_is_repeatable_and_does_not_expand_permissions():
    from sqlalchemy import select,func
    from apps.reference_api.db import get_engine
    from security_master_schema import models as m
    from security_master_schema.demo_data import DEMO_IDS as ids
    from security_master_schema.index_universe_seed import seed
    from market_data.providers.yahoo.onboarding import enable_personal_research
    from market_data.providers.yahoo.fx_storage import configure_fx,ingest_fx
    from market_data.rights import load_rights
    import json
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            seed(c,ids['demo_user_account'])
            enable_personal_research(c,ids['tenant'],ids['demo_user_account'],'Owner authorized local research')
            config=configure_fx(c,ids['tenant'],ids['demo_user_account'])
            assert configure_fx(c,ids['tenant'],ids['demo_user_account'])==config
            assert load_rights(c,config['datasetId'],'ACQUIRE',date.today()).allowed
            assert not load_rights(c,config['datasetId'],'NON_DISPLAY',date.today()).allowed
            assert not load_rights(c,config['datasetId'],'REDISTRIBUTE',date.today()).allowed
            assert not c.scalar(select(func.count()).select_from(m.tenant_dataset_entitlement).where(m.tenant_dataset_entitlement.c.dataset_id==config['datasetId'],m.tenant_dataset_entitlement.c.use_purpose=='VALUATION'))
            data=chart(['2026-10-07T14:55:00+00:00','2026-10-07T19:55:00+00:00'],[.85,.86])
            now=datetime.now(timezone.utc)
            report=ingest_fx(c,config=config,symbol='EURGBP=X',raw_payload=json.dumps(data),start=date(2026,10,7),end=date(2026,10,7),received_at=now,interval='5m')
            assert report['accepted']==2
            replay=ingest_fx(c,config=config,symbol='EURGBP=X',raw_payload=json.dumps(data),start=date(2026,10,7),end=date(2026,10,7),received_at=now,interval='5m')
            assert replay['replayed']
            rows=c.execute(select(m.market_data_observation,m.market_data_series.c.is_official,m.market_data_series.c.value_type).join(m.market_data_series).where(m.market_data_observation.c.dataset_id==config['datasetId'])).mappings().all()
            assert len(rows)==2 and all(r['value_type']=='RATE' and not r['is_official'] for r in rows)
            assert all(r['source_timestamp_utc']<r['observed_at_utc'] and r['source_payload_id'] for r in rows)
            data['chart']['result'][0]['indicators']['quote'][0]['close'][0]=.851
            corrected=ingest_fx(c,config=config,symbol='EURGBP=X',raw_payload=json.dumps(data),start=date(2026,10,7),end=date(2026,10,7),received_at=now,interval='5m')
            assert corrected['accepted']==1 and corrected['duplicates']==1
            assert c.scalar(select(func.count()).select_from(m.market_data_observation).where(m.market_data_observation.c.dataset_id==config['datasetId'],m.market_data_observation.c.supersedes_observation_id.is_not(None)))==1
            assert c.scalar(select(m.market_data_observation.c.value).where(m.market_data_observation.c.market_data_observation_id==rows[0]['market_data_observation_id']))==rows[0]['value']
            hourly=chart(['2026-10-07T14:00:00+00:00','2026-10-07T19:00:00+00:00'],[.852,.863],interval='1h')
            result=ingest_fx(c,config=config,symbol='EURGBP=X',raw_payload=json.dumps(hourly),start=date(2026,10,7),end=date(2026,10,7),received_at=now,interval='1h')
            assert result['accepted']==2
            assert c.scalar(select(func.count()).select_from(m.market_data_series).where(m.market_data_series.c.default_dataset_id==config['datasetId']))==4
            assert c.scalar(select(m.market_data_observation.c.value).where(m.market_data_observation.c.market_data_observation_id==rows[1]['market_data_observation_id']))==rows[1]['value']
        finally:tx.rollback()
