"""Yahoo source semantics and failures without making live network requests."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import json

import httpx
import pytest


def chart():
    return {'chart': {'error': None, 'result': [{'meta': {
        'symbol': 'AAPL', 'currency': 'USD', 'exchangeName': 'NMS',
        'instrumentType': 'EQUITY', 'exchangeTimezoneName': 'America/New_York'},
        'timestamp': [1791207000, 1791293400],
        'indicators': {'quote': [{'close': [250.25, 252]}],
                       'adjclose': [{'adjclose': [249.75, 252]}]}}]}}


def parse(payload=None, **kwargs):
    from market_data.providers.yahoo.adapter import parse_chart
    return parse_chart(payload or chart(), symbol='AAPL', currency='USD', mic='XNAS',
                       timezone_name='America/New_York', start=date(2026, 10, 5),
                       end=date(2026, 10, 6), **kwargs)


def test_separate_close_and_adjusted_close_with_source_bar_times():
    result = parse()
    assert len(result.points) == 4
    close = next(p for p in result.points if p.market_date == date(2026, 10, 5) and p.field == 'CLOSE')
    adjusted = next(p for p in result.points if p.market_date == close.market_date and p.field == 'ADJ_CLOSE')
    assert close.value == Decimal('250.25') and close.value_basis == 'SPLIT_ADJUSTED'
    assert adjusted.value == Decimal('249.75') and adjusted.value_basis == 'VENDOR_ADJUSTED'
    assert close.observed_at.isoformat() == '2026-10-05T13:30:00+00:00'
    assert not result.rejections


@pytest.mark.parametrize('field,value', [('symbol', 'MSFT'), ('currency', 'EUR'), ('exchangeName', 'NYQ'),
    ('exchangeTimezoneName', 'Europe/Paris'), ('instrumentType', 'ETF')])
def test_mismatched_identity_is_not_silently_mapped(field, value):
    payload = chart()
    payload['chart']['result'][0]['meta'][field] = value
    with pytest.raises(ValueError, match='identity'):
        parse(payload)


@pytest.mark.parametrize('bad', [None, True, -1, 0, 'NaN', 'Infinity', 'oops'])
def test_invalid_prices_are_reported_not_forward_filled(bad):
    payload = chart()
    payload['chart']['result'][0]['indicators']['quote'][0]['close'][0] = bad
    result = parse(payload)
    assert len(result.points) == 3
    assert len(result.rejections) == 1
    assert result.rejections[0]['field'] == 'CLOSE'


def test_malformed_column_lengths_and_duplicate_dates_fail_closed():
    payload = chart()
    payload['chart']['result'][0]['indicators']['quote'][0]['close'].pop()
    with pytest.raises(ValueError, match='length'):
        parse(payload)
    payload = chart()
    payload['chart']['result'][0]['timestamp'][1] = payload['chart']['result'][0]['timestamp'][0]
    with pytest.raises(ValueError, match='duplicate'):
        parse(payload)


def test_rate_limit_exhaustion_is_bounded_and_symbol_is_encoded():
    from market_data.providers.yahoo.adapter import fetch_chart
    requests = []
    waits = []
    def handler(request):
        requests.append(request)
        return httpx.Response(429)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            fetch_chart(client, 'BRK-B', date(2026, 10, 5), date(2026, 10, 6), sleep=waits.append)
    assert len(requests) == 4
    assert waits == [30, 60, 120]
    assert requests[0].url.host == 'query1.finance.yahoo.com'
    assert requests[0].url.params['interval'] == '1d'


def test_fetch_identifies_personal_research_and_requests_json():
    from market_data.providers.yahoo.adapter import fetch_chart
    def handler(request):
        if (request.headers['User-Agent'] != 'PersonalPriceResearch/1.0'
                or request.headers['Accept'] != 'application/json'):
            return httpx.Response(403)
        return httpx.Response(200, json=chart())
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        raw = fetch_chart(client, 'AAPL', date(2026, 10, 5), date(2026, 10, 6))
    assert len(parse(json.loads(raw)).points) == 4


def test_explicit_five_year_fetch_is_bounded_and_daily_default_is_unchanged():
    from market_data.providers.yahoo.adapter import fetch_chart
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, text='history'))) as client:
        with pytest.raises(ValueError):
            fetch_chart(client, 'AAPL', date(2021, 10, 7), date(2026, 10, 6))
        assert fetch_chart(client, 'AAPL', date(2021, 10, 7), date(2026, 10, 6), max_window_days=1830) == 'history'
        with pytest.raises(ValueError):
            fetch_chart(client, 'AAPL', date(2020, 10, 7), date(2026, 10, 6), max_window_days=1830)
        with pytest.raises(ValueError):
            fetch_chart(client, 'AAPL', date(2021, 10, 7), date(2026, 10, 6), max_window_days=100000)


@pytest.mark.parametrize('retry_after,expected', [('90', 90), ('bad', 30), ('-1', 30),
    ('Wed, 07 Oct 2026 12:01:30 GMT', 90)])
def test_rate_limit_recovers_and_respects_retry_after(retry_after, expected):
    from datetime import datetime, timezone
    from market_data.providers.yahoo.adapter import fetch_chart
    requests, waits = [], []
    def handler(request):
        requests.append(request)
        return (httpx.Response(429, headers={'Retry-After': retry_after}) if len(requests) == 1
                else httpx.Response(200, text='chart body'))
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = fetch_chart(client, 'AAPL', date(2026, 10, 5), date(2026, 10, 6),
            sleep=waits.append, now=lambda: datetime(2026, 10, 7, 12, tzinfo=timezone.utc))
    assert result == 'chart body'
    assert len(requests) == 2
    assert waits == [expected]


@pytest.mark.parametrize('status,headers', [(401, {}), (403, {}), (500, {}),
    (429, {'Retry-After': '601'}), (429, {'Retry-After': '9' * 5000}),
    (429, {'Retry-After': '0' * 5000 + '601'})])
def test_denial_or_excessive_server_delay_stops_without_retry(status, headers):
    from market_data.providers.yahoo.adapter import fetch_chart
    requests, waits = [], []
    def handler(request):
        requests.append(request)
        return httpx.Response(status, headers=headers)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            fetch_chart(client, 'AAPL', date(2026, 10, 5), date(2026, 10, 6), sleep=waits.append)
    assert len(requests) == 1
    assert waits == []


def test_requested_window_and_incomplete_today_bar_are_rejected():
    payload = chart()
    from datetime import datetime, timezone
    result = parse(payload, received_at=datetime(2026, 10, 5, 14, tzinfo=timezone.utc))
    assert not result.points
    assert len(result.rejections) == 4
