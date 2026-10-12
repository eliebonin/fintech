from datetime import datetime, timezone
from tests.test_yahoo_market_data import chart, parse


def test_yahoo_split_events_retained_but_window_is_not_certified_complete():
    payload=chart()
    stamp=int(datetime(2026,10,6,tzinfo=timezone.utc).timestamp())
    payload['chart']['result'][0]['events']={'splits':{str(stamp):{
        'date':stamp,'numerator':2,'denominator':1}}}
    result=parse(payload)
    assert result.adjustment_evidence['splits']==[dict(date='2026-10-05',numerator='2',denominator='1')]
    assert result.adjustment_evidence['complete'] is False
    assert result.adjustment_evidence['blockingReason']=='PROVIDER_ADJUSTMENT_ANCHOR_NOT_CERTIFIED'


def test_yahoo_empty_events_do_not_prove_factor_one():
    result=parse(chart())
    assert result.adjustment_evidence['complete'] is False
    assert result.adjustment_evidence['anchorDate'] is None
