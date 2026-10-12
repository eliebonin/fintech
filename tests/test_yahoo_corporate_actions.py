"""Real adapter and SQL publication: source events are not normalization proof."""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID
import json
import pytest
from sqlalchemy import select, func
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from tests.test_yahoo_market_data import chart, parse
from tests.test_market_data_ingestion import setup_dataset, fixture_payload, ingest


def events_payload():
    payload=chart()
    payload['chart']['result'][0]['events']={
        'splits':{'1791207000':{'date':1791207000,'numerator':2,'denominator':1,'splitRatio':'2:1'}},
        'dividends':{'1791293400':{'date':1791293400,'amount':1.25}}}
    return payload


def test_parse_retains_split_and_dividend_ex_dates_without_inventing_payment_or_execution_times():
    parsed=parse(events_payload())
    split,dividend=parsed.corporate_actions
    assert split['event_type']=='STOCK_SPLIT' and split['ratio']==Decimal('2')
    assert split['date_value']==date(2026,10,5) and split['date_role']=='EX'
    assert dividend['event_type']=='CASH_DIVIDEND' and dividend['cash_amount']==Decimal('1.25')
    assert dividend['date_value']==date(2026,10,6)
    assert all('timestamp_value_utc' not in action for action in parsed.corporate_actions)
    assert parsed.adjustment_evidence['complete'] is False
    assert parsed.adjustment_evidence['anchorDate'] is None


@pytest.mark.parametrize('change', ['bad_ratio','contradictory_ratio','bad_amount','outside_window','key_mismatch'])
def test_invalid_corporate_action_does_not_publish_but_does_not_destroy_valid_prices(change):
    payload=events_payload();events=payload['chart']['result'][0]['events']
    if change=='bad_ratio': events['splits']['1791207000']['numerator']=True
    if change=='contradictory_ratio': events['splits']['1791207000']['splitRatio']='3:1'
    if change=='bad_amount': events['dividends']['1791293400']['amount']=-1
    if change=='outside_window': events['splits']={'1':{'date':1,'numerator':2,'denominator':1}}
    if change=='key_mismatch': events['splits']={'wrong':events['splits']['1791207000']}
    parsed=parse(payload)
    assert len(parsed.points)==4 and len(parsed.corporate_actions)==1
    assert len(parsed.adjustment_evidence['eventRejections'])==1
    assert parsed.adjustment_evidence['complete'] is False


def test_event_source_mismatch_cannot_publish_corporate_actions():
    payload=events_payload();payload['chart']['result'][0]['meta']['symbol']='MSFT'
    with pytest.raises(ValueError,match='identity'): parse(payload)


def test_new_ingestion_publishes_versioned_source_events_and_replays_without_duplicates():
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            dataset,namespace,listing=setup_dataset(c)
            payload=events_payload();payload['chart']['result'][0]['meta']['exchangeName']='NYQ'
            first=ingest(c,dataset,namespace,'actions-1',json.dumps(payload))
            assert first['corporateActions']['inserted']==2
            parent=c.scalar(select(m.listing.c.instrument_node_id).where(m.listing.c.listing_node_id==listing))
            actions=c.execute(select(m.corporate_action).where(m.corporate_action.c.affected_instrument_node_id==parent,
                m.corporate_action.c.external_event_reference.like('YAHOO_FINANCE_PERSONAL:AAPL:%'))).mappings().all()
            assert len(actions)==2 and all(a['status']=='ANNOUNCED' for a in actions)
            assert all(a['source_payload_id'] and a['recorded_at_utc'] for a in actions)
            assert all(a['announced_at_utc'] is None for a in actions)
            dividend=next(a for a in actions if a['event_type']=='CASH_DIVIDEND')
            cash=c.execute(select(m.corporate_action_effect).where(m.corporate_action_effect.c.corporate_action_id==dividend['corporate_action_id'])).mappings().one()
            assert cash['cash_amount']==Decimal('1.25') and cash['currency_id']==DEMO_IDS['usd_currency']
            dates=c.execute(select(m.corporate_action_date).where(m.corporate_action_date.c.corporate_action_id.in_([a['corporate_action_id'] for a in actions]))).mappings().all()
            assert all(d['date_role']=='EX' and d['timestamp_value_utc'] is None for d in dates)
            assert ingest(c,dataset,namespace,'actions-1',json.dumps(payload))['replayed']
            second=ingest(c,dataset,namespace,'actions-2',json.dumps(payload))
            assert second['corporateActions']['duplicates']==2 and second['corporateActions']['inserted']==0
            payload['chart']['result'][0]['events']['dividends']['1791293400']['amount']=1.5
            corrected=ingest(c,dataset,namespace,'actions-3',json.dumps(payload))
            assert corrected['corporateActions']['inserted']==1 and corrected['corporateActions']['revised']==1
            assert c.scalar(select(m.corporate_action_effect.c.cash_amount).where(m.corporate_action_effect.c.corporate_action_id==dividend['corporate_action_id']))==Decimal('1.25')
            versions=c.execute(select(m.corporate_action.c.sequence_no).where(m.corporate_action.c.external_event_reference==dividend['external_event_reference']).order_by(m.corporate_action.c.sequence_no)).scalars().all()
            assert versions==[1,2]
            from market_data.providers.yahoo.corporate_actions import backfill_retained_actions
            reassessed=backfill_retained_actions(c,dataset,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'])
            assert reassessed['inserted']==0  # Older deliveries cannot revert a correction on replay.
            assert c.scalar(select(func.count()).select_from(m.market_data_price_basis_proof))==0
        finally: tx.rollback()


def test_cancelled_source_event_is_not_revived_by_changed_provider_payload():
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            dataset,namespace,_=setup_dataset(c)
            payload=events_payload();payload['chart']['result'][0]['meta']['exchangeName']='NYQ'
            ingest(c,dataset,namespace,'cancelled-1',json.dumps(payload))
            event=c.scalar(select(m.corporate_action.c.corporate_action_id).where(
                m.corporate_action.c.external_event_reference=='YAHOO_FINANCE_PERSONAL:AAPL:dividends:1791293400'))
            c.execute(m.corporate_action.update().where(m.corporate_action.c.corporate_action_id==event).values(status='CANCELLED'))
            payload['chart']['result'][0]['events']['dividends']['1791293400']['amount']=1.5
            report=ingest(c,dataset,namespace,'cancelled-2',json.dumps(payload))
            assert report['corporateActions']['reviewRequired']==1 and report['corporateActions']['inserted']==0
            assert c.scalar(select(m.corporate_action.c.status).where(m.corporate_action.c.corporate_action_id==event))=='CANCELLED'
        finally: tx.rollback()


def test_backfill_does_not_hide_an_earlier_event_rejection_behind_a_later_empty_delivery():
    from market_data.providers.yahoo.corporate_actions import backfill_retained_actions
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            dataset,namespace,_=setup_dataset(c)
            payload=events_payload();payload['chart']['result'][0]['meta']['exchangeName']='NYQ'
            payload['chart']['result'][0]['events']['dividends']['1791293400']['amount']=-1
            ingest(c,dataset,namespace,'partial-actions',json.dumps(payload))
            ingest(c,dataset,namespace,'later-empty-events',fixture_payload())
            report=backfill_retained_actions(c,dataset,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'])
            assert report['rejectedEvents']==1 and report['status']=='PARTIAL'
        finally: tx.rollback()


def test_retained_backfill_is_scoped_idempotent_and_persists_assessment_without_new_prices():
    from dataclasses import replace
    from market_data.ingestion import ingest_delivery
    from market_data.providers.yahoo.adapter import parse_delivery,YAHOO_DAILY_EQUITY
    from market_data.providers.yahoo.corporate_actions import backfill_retained_actions
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            dataset,namespace,_=setup_dataset(c)
            payload=events_payload();payload['chart']['result'][0]['meta']['exchangeName']='NYQ'
            # Simulate the old real parser retaining events without canonical publication.
            def old_parser(*args,**kwargs): return replace(parse_delivery(*args,**kwargs),corporate_actions=())
            report=ingest_delivery(c,provider=YAHOO_DAILY_EQUITY,parser=old_parser,dataset_id=dataset,namespace_id=namespace,symbol='AAPL',
                raw_payload=json.dumps(payload),delivery_key='legacy-actions',received_at=datetime(2026,10,7,8,tzinfo=timezone.utc),start=date(2026,10,5),end=date(2026,10,6))
            before=c.scalar(select(func.count()).select_from(m.market_data_observation))
            result=backfill_retained_actions(c,dataset,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'])
            assert result['status']=='COMPLETE'
            assert result['inserted']==2 and result['normalizationProofsCreated']==0
            assert result['assessments'][0]['priceBasisReady'] is False
            assert backfill_retained_actions(c,dataset,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'])['inserted']==0
            assert c.scalar(select(func.count()).select_from(m.market_data_observation))==before
            assert c.scalar(select(m.market_data_ingestion_attempt.c.report).where(m.market_data_ingestion_attempt.c.job_id==UUID(result['jobId'])))['sourceRunId']==report['runId']
            with pytest.raises(PermissionError): backfill_retained_actions(c,dataset,DEMO_IDS['second_tenant'],DEMO_IDS['demo_user_account'])
        finally: tx.rollback()
