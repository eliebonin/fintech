"""Provider history is an estimate, not an assertion of IPO/ISIN continuity."""
from datetime import date
from copy import deepcopy
import pytest


def meta(symbol='AAPL'):
    return dict(symbol=symbol, firstTradeDate=345479400,
                exchangeTimezoneName='America/New_York', currency='USD',
                exchangeName='NMS', instrumentType='EQUITY')


def test_date_assessment_uses_provider_day_and_marks_estimate():
    from apps.market_data_ingestor.index_trading_history import assess_start
    row = assess_start(meta(), 'AAPL', 'XNAS', 'USD')
    assert row['effectiveFrom'] == '1980-12-12'
    assert row['basis'] == 'PROVIDER_HISTORY_ESTIMATE'


def test_negative_epoch_supported_on_windows():
    from apps.market_data_ingestor.index_trading_history import assess_start
    item = meta()
    item['firstTradeDate'] = -252322200
    assert date.fromisoformat(assess_start(item, 'AAPL', 'XNAS', 'USD')['effectiveFrom']).year == 1962


def test_when_issued_date_does_not_enable_regular_way_listing():
    from apps.market_data_ingestor.index_trading_history import assess_start
    item = meta('GEHC')
    item['firstTradeDate'] = 1671114600
    row = assess_start(item, 'GEHC', 'XNAS', 'USD')
    assert row['effectiveFrom'] == '2023-01-04'
    assert row['basis'] == 'PRIMARY_REGULAR_WAY'
    assert row['sources']


@pytest.mark.parametrize('symbol,provider_date,expected', [
    ('GOOG','2004-08-19','2014-04-03'), ('DELL','2016-08-17','2018-12-28'),
    ('CARR','2020-03-19','2020-04-03'), ('OTIS','2020-03-19','2020-04-03'),
    ('DOW','2019-03-20','2019-04-02'), ('NWS','2013-06-19','2013-07-01'),
    ('NWSA','2013-06-19','2013-07-01'), ('FOX','2019-03-13','2019-03-19'),
    ('FOXA','2019-03-12','2019-03-19')])
def test_listing_lifecycle_excludes_known_predecessor_and_when_issued_history(symbol, provider_date, expected):
    from apps.market_data_ingestor.index_trading_history import booking_start
    assert booking_start(dict(symbol=symbol, effectiveFrom=provider_date)).isoformat() == expected


@pytest.mark.parametrize('field,value', [('symbol','WRONG'),('currency','EUR'),
    ('exchangeTimezoneName','Europe/Paris'),('exchangeName','PAR'),
    ('instrumentType','ETF'),('firstTradeDate',None),('firstTradeDate',True),
    ('firstTradeDate',999999999999)])
def test_untrusted_or_future_metadata_refused(field, value):
    from apps.market_data_ingestor.index_trading_history import assess_start
    item = deepcopy(meta()); item[field] = value
    with pytest.raises(ValueError):
        assess_start(item, 'AAPL', 'XNAS', 'USD')
