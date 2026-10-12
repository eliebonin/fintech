"""Daily equity chart adapter. No repairs, implicit adjustments or access bypass."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from email.utils import parsedate_to_datetime
import time
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx

from market_data.contracts import DailyPoint, ListingContext, ParsedDelivery, ProviderSpec


EXCHANGES = {'XNAS': {'NMS', 'NGM', 'NCM'}, 'XNYS': {'NYQ'},
             'BATS': {'BATS', 'BTS'}, 'XPAR': {'PAR'}, 'XAMS': {'AMS'}}
MAX_BYTES = 4 * 1024 * 1024


ParsedChart = ParsedDelivery
YAHOO_DAILY_EQUITY = ProviderSpec('YAHOO_FINANCE_PERSONAL', ('CLOSE', 'ADJUSTED_CLOSE'), MAX_BYTES, 366)
YAHOO_EQUITY_HISTORY = ProviderSpec('YAHOO_FINANCE_PERSONAL', ('CLOSE', 'ADJUSTED_CLOSE'), MAX_BYTES, 1830)


def parse_delivery(payload: dict, *, symbol: str, listing: ListingContext,
                   start: date, end: date, received_at: datetime) -> ParsedDelivery:
    return parse_chart(payload, symbol=symbol, currency=listing.currency, mic=listing.mic,
                       timezone_name=listing.timezone_name, start=start, end=end, received_at=received_at)


def fetch_chart(client: httpx.Client, symbol: str, start: date, end: date, *,
                sleep=time.sleep, now=lambda: datetime.now(timezone.utc), on_retry=None,
                max_window_days: int = 366, interval: str = '1d') -> str:
    """Serial GET with three bounded 429 retries; never retry an access denial."""
    if (not isinstance(max_window_days, int) or isinstance(max_window_days, bool)
            or not 1 <= max_window_days <= 1830 or not symbol or len(symbol) > 100
            or end < start or (end - start).days + 1 > max_window_days
            or interval not in {'1d','5m','1h'} or (interval=='5m' and (end-start).days+1>60)
            or (interval=='1h' and (end-start).days+1>730)):
        raise ValueError('A symbol and a bounded daily/history window of at most 1830 days are required')
    params = dict(period1=int(datetime.combine(start, datetime.min.time(), timezone.utc).timestamp()),
                  period2=int(datetime.combine(end + timedelta(days=1), datetime.min.time(), timezone.utc).timestamp()),
                  interval=interval, events='div,splits', includePrePost='false')
    for attempt in range(4):
        with client.stream('GET', f'https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol, safe="")}',
                           params=params, headers={'User-Agent': 'PersonalPriceResearch/1.0',
                                                   'Accept': 'application/json'},
                           timeout=30, follow_redirects=False) as response:
            if response.status_code == 429 and attempt < 3:
                delay = 30 * 2 ** attempt
                header = response.headers.get('Retry-After', '').strip()
                if header.isascii() and header.isdecimal() and len(header.lstrip('0')) > 3:
                    response.raise_for_status()
                try:
                    if header.isascii() and header.isdecimal():
                        server_delay = int(header.lstrip('0') or '0')
                    else:
                        server_time = parsedate_to_datetime(header)
                        if server_time.utcoffset() is None:
                            raise ValueError('Retry-After date must include timezone')
                        server_delay = max(0, (server_time - now()).total_seconds())
                    delay = max(delay, server_delay)
                except (ValueError, TypeError, OverflowError):
                    pass  # Malformed header: retain the conservative exponential delay.
                if delay > 600:
                    response.raise_for_status()  # Stop rather than retry earlier than requested.
            else:
                response.raise_for_status()
                chunks, total = [], 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise ValueError('Source response exceeds the 4 MiB limit')
                    chunks.append(chunk)
                return b''.join(chunks).decode('utf-8')
        # Release the response/connection before waiting. No database transaction is held.
        if on_retry is not None:
            on_retry(attempt + 1, delay)
        sleep(delay)
    raise AssertionError('Unreachable retry state')


def parse_chart(payload: dict, *, symbol: str, currency: str, mic: str,
                timezone_name: str, start: date, end: date,
                received_at: datetime | None = None) -> ParsedChart:
    if end < start:
        raise ValueError('Invalid date range')
    if received_at is not None and received_at.utcoffset() is None:
        raise ValueError('Receipt time must have a timezone')
    try:
        chart = payload['chart']
        if chart.get('error') or len(chart['result']) != 1:
            raise ValueError('Source did not return one chart')
        result = chart['result'][0]
        meta = result['meta']
        if (meta['symbol'] != symbol or meta['currency'] != currency or currency not in {'USD', 'EUR'}
                or meta['exchangeName'] not in EXCHANGES.get(mic, set())
                or meta['exchangeTimezoneName'] != timezone_name or meta['instrumentType'] != 'EQUITY'):
            raise ValueError('Source identity does not match symbol, venue, currency, timezone or equity type')
        tz = ZoneInfo(timezone_name)
        timestamps = result.get('timestamp', [])
        indicators = result.get('indicators', {})
        closes = indicators['quote'][0]['close']
        adjusted = indicators.get('adjclose', [{}])[0].get('adjclose')
        fields = [('CLOSE', closes, 'SPLIT_ADJUSTED')]
        if adjusted is not None:
            fields.append(('ADJ_CLOSE', adjusted, 'VENDOR_ADJUSTED'))
        if any(len(values) != len(timestamps) for _, values, _ in fields):
            raise ValueError('Source column length mismatch')
        points, rejections, seen = [], [], set()
        receipt_day = received_at.astimezone(tz).date() if received_at else None
        for i, timestamp in enumerate(timestamps):
            if isinstance(timestamp, bool) or not isinstance(timestamp, int):
                raise ValueError('Invalid source timestamp')
            observed = datetime.fromtimestamp(timestamp, timezone.utc)
            market_date = observed.astimezone(tz).date()
            if market_date in seen:
                raise ValueError('Source has duplicate market dates')
            seen.add(market_date)
            for field, values, basis in fields:
                reason = None
                try:
                    raw = values[i]
                    value = Decimal(str(raw)) if not isinstance(raw, bool) else Decimal('NaN')
                    if not value.is_finite() or value <= 0 or value >= Decimal('1e18'):
                        reason = 'Invalid nonpositive, nonfinite or oversized equity price'
                    else:
                        # Match Numeric(30, 12) before duplicate comparison; preserve original text in the delivery.
                        value = value.quantize(Decimal('0.000000000001'), rounding=ROUND_HALF_EVEN)
                        if value <= 0:
                            reason = 'Equity price is below storage precision'
                except (InvalidOperation, ValueError, TypeError):
                    reason = 'Missing or malformed equity price'
                if market_date < start or market_date > end:
                    reason = 'Outside requested market date window'
                if receipt_day is not None and market_date >= receipt_day:
                    # Conservative: avoid admitting the still-moving daily bar without authoritative session close.
                    reason = 'Current or future session is not certified complete; retry the next day'
                if reason:
                    rejections.append(dict(field=field, marketDate=market_date.isoformat(), reason=reason))
                else:
                    points.append(DailyPoint(field, market_date, observed, value, basis,
                                             'CLOSE' if field == 'CLOSE' else 'ADJUSTED_CLOSE'))
        from .corporate_actions import parse_events
        actions,splits,dividends,event_rejections=parse_events(result,symbol=symbol,timezone_name=timezone_name,start=start,end=end)
        # The chart endpoint returns events for a bounded query window, not a
        # certified timeline through the price adjustment anchor. Retain facts
        # for assessment without manufacturing usable normalization proof.
        adjustment = dict(method='YAHOO_CHART_SPLIT_EVENTS',splits=splits,dividends=dividends,eventRejections=event_rejections,
            queryStart=start.isoformat(),queryEnd=end.isoformat(),anchorDate=None,complete=False,
            blockingReason='PROVIDER_ADJUSTMENT_ANCHOR_NOT_CERTIFIED')
        return ParsedChart(tuple(points), tuple(rejections),
                           'VENDOR_ADJUSTED', 'PROVIDER_DAILY_BAR_TIMESTAMP', adjustment,actions)
    except (KeyError, IndexError, TypeError, OverflowError) as exc:
        raise ValueError('Malformed Yahoo chart payload') from exc
