"""Evidence-supported historical availability for the curated public universe.

Operator-only, reference-only and transaction-owned by the caller. Yahoo's
firstTradeDate is a conservative provider-history estimate, NOT a certified IPO
date or proof that today's ISIN/ticker/venue existed throughout that history.
Original immutable approvals and current economic definitions are preserved.
"""
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select, func
from security_master_schema import models as m
from security_master_schema.index_universe_seed import load_manifest, VENUES, _insert, _same
from market_data.providers.yahoo.onboarding import DATASET_CODE, yahoo_symbol
from market_data.providers.yahoo.adapter import EXCHANGES

SNAPSHOT = date(2026, 10, 6)
BOUNDS_FILE = Path(m.__file__).parent/'data/index_regular_way_bounds_2026_10_08.json'
LIFECYCLE_BOUNDS = json.loads(BOUNDS_FILE.read_text(encoding='utf-8'))
REGULAR_WAY = {
    'CEG': ('2022-02-02', 'https://www.constellationenergy.com/news/2022/constellation-launches-as-largest-u-s--clean-energy-company-afte.html'),
    'GEHC': ('2023-01-04', 'https://www.sec.gov/Archives/edgar/data/1932393/000193239323000025/gehc-20221231.htm'),
    'GEV': ('2024-04-02', 'https://www.gevernova.com/investors/stock'),
    'SOLV': ('2024-04-01', 'https://www.solventum.com/en-au/home/our-company/newsroom/press-releases/2024-03-08-3m-board-of-directors-approves-spin-off-of-solventum/'),
    'SNDK': ('2025-02-24', 'https://beta.nasdaqtrader.com/TraderNews.aspx?id=ECA2025-38'),
    'Q': ('2025-11-03', 'https://www.sec.gov/Archives/edgar/data/2058873/000205887326000015/R8.htm'),
    'FDXF': ('2026-06-01', 'https://ir.fedexfreight.com/financial-information/sec-filings/content/0001628280-26-053359/0001628280-26-053359.pdf'),
    'HONA': ('2026-06-29', 'https://www.honeywellaerospace.com/us/en/company/newsroom/2026/06/honeywell-aerospace-spin-off-begins-trading-nasdaq'),
    'VYLR': ('2026-10-01', 'https://www.sec.gov/Archives/edgar/data/2128626/000119312526409909/d115079d8k.htm'),
}


def booking_start(entry):
    """A later primary lifecycle boundary can only restrict provider coverage."""
    estimate = date.fromisoformat(entry['effectiveFrom'])
    bound = LIFECYCLE_BOUNDS.get(entry['symbol'])
    return max(estimate, date.fromisoformat(bound['start'])) if bound else estimate


def _apply_lifecycle_bounds(c, source, entries):
    digest = sha256(BOUNDS_FILE.read_bytes()).hexdigest()
    payload = c.execute(select(m.source_payload).where(
        m.source_payload.c.integration_source_system_id == source,
        m.source_payload.c.external_message_reference == 'index-regular-way-bounds-2026-10-08')).mappings().one_or_none()
    if payload:
        _same(payload.payload_sha256, digest, 'regular-way lifecycle evidence')
        payload_id = payload.source_payload_id
    else:
        payload_id = _insert(c, m.source_payload, 'source_payload_id', integration_source_system_id=source,
            payload_format='JSON', external_message_reference='index-regular-way-bounds-2026-10-08',
            payload_locator=str(BOUNDS_FILE.resolve()), payload_sha256=digest, processing_status='VALIDATED')
    adjusted = 0
    for entry in entries:
        if entry['symbol'] not in LIFECYCLE_BOUNDS:
            continue
        start = date.fromisoformat(entry['effectiveFrom'])
        boundary = booking_start(entry)
        if not start <= boundary < SNAPSHOT:
            raise ValueError('Regular-way lifecycle restriction is outside approved historical coverage.')
        for table, key, code in (
            (m.instrument, 'instrument_node_id', 'PUBLIC_EQ_'+entry['isin']),
            (m.listing, 'listing_node_id', 'PUBLIC_LIST_'+entry['isin']+'_'+entry['mic']),
        ):
            node = c.scalar(select(m.financial_reference_node.c.reference_node_id).where(m.financial_reference_node.c.internal_code == code))
            existing = c.scalar(select(table.c.effective_from).where(table.c[key] == node).with_for_update())
            if existing not in (start, boundary):
                raise ValueError('Unexpected lifecycle restriction; refusing overwrite.')
            if existing != boundary:
                c.execute(table.update().where(table.c[key] == node).values(effective_from=boundary))
                adjusted += 1
    return adjusted, str(payload_id)


def assess_start(meta, symbol, mic, currency):
    tz = VENUES[mic][3]
    if (meta.get('symbol') != symbol or meta.get('currency') != currency
            or meta.get('exchangeName') not in EXCHANGES[mic]
            or meta.get('exchangeTimezoneName') != tz
            or meta.get('instrumentType') != 'EQUITY'):
        raise ValueError('Provider identity, venue, currency or type mismatch.')
    stamp = meta.get('firstTradeDate')
    if not isinstance(stamp, int) or isinstance(stamp, bool):
        raise ValueError('Provider trading-start timestamp is missing or invalid.')
    try:
        # Windows fromtimestamp rejects some negative epoch values.
        start = (datetime(1970, 1, 1, tzinfo=timezone.utc)
                 + timedelta(seconds=stamp)).astimezone(ZoneInfo(tz)).date()
    except (OverflowError, ValueError) as exc:
        raise ValueError('Provider trading-start timestamp is out of range.') from exc
    if not date(1800, 1, 1) <= start < SNAPSHOT:
        raise ValueError('Provider trading-start date is outside the historical seed window.')
    result = dict(providerFirstTradeDate=start.isoformat(), effectiveFrom=start.isoformat(),
                  basis='PROVIDER_HISTORY_ESTIMATE', sources=[])
    if symbol in REGULAR_WAY:
        regular, url = REGULAR_WAY[symbol]
        result.update(effectiveFrom=regular, basis='PRIMARY_REGULAR_WAY', sources=[url])
    return result


def export_evidence(c):
    """Reuse retained acquisition evidence; do not issue another 543 HTTP calls."""
    dataset = c.scalar(select(m.dataset.c.dataset_id).where(m.dataset.c.dataset_code == DATASET_CODE))
    if dataset is None:
        raise ValueError('The personal Yahoo dataset must already exist.')
    namespace = c.scalar(select(m.dataset_access_profile.c.external_id_namespace_id).where(
        m.dataset_access_profile.c.dataset_id == dataset))
    deliveries = c.execute(select(m.market_data_ingestion_run).where(
        m.market_data_ingestion_run.c.dataset_id == dataset,
        m.market_data_ingestion_run.c.report['request']['start'].as_string() == '2021-10-07'
    ).order_by(m.market_data_ingestion_run.c.received_at_utc)).mappings().all()
    by_symbol = {}
    for delivery in deliveries:
        if delivery.report.get('request', {}).get('namespaceId') != str(namespace):
            continue
        if sha256(delivery.raw_payload.encode('utf-8')).hexdigest() != delivery.content_sha256:
            raise ValueError('Retained provider payload checksum mismatch.')
        result = json.loads(delivery.raw_payload)['chart'].get('result')
        if result and delivery.report.get('accepted', 0):
            by_symbol.setdefault(result[0]['meta']['symbol'], delivery)
    securities = []
    for row in load_manifest()['securities']:
        symbol = yahoo_symbol(row['symbol'], row['mic'])
        if symbol not in by_symbol:
            raise ValueError(f'Missing retained trading-start evidence for {symbol}.')
        delivery = by_symbol[symbol]
        meta = json.loads(delivery.raw_payload)['chart']['result'][0]['meta']
        securities.append(dict(isin=row['isin'], mic=row['mic'], symbol=symbol,
            **assess_start(meta, symbol, row['mic'], row['currency']),
            providerMetadata=meta, sourcePayloadId=str(delivery.source_payload_id),
            sourceSha256=delivery.content_sha256))
    return dict(schemaVersion=1, asOf='2026-10-08', seedAsOf=SNAPSHOT.isoformat(),
        caveat='Provider history estimates do not certify IPO, historical ticker, ISIN or venue continuity. Primary regular-way overrides exclude when-issued trading.',
        securities=securities)


def apply_history(c, actor, path):
    """Append closed historical approvals; never mutate any approval or trade."""
    bundle = json.loads(path.read_text(encoding='utf-8'))
    reviewed = {(r['isin'], r['mic']): r for r in load_manifest()['securities']}
    entries = bundle.get('securities', [])
    if (bundle.get('schemaVersion') != 1 or bundle.get('seedAsOf') != SNAPSHOT.isoformat()
            or len(entries) != len(reviewed)
            or {(r['isin'], r['mic']) for r in entries} != set(reviewed)):
        raise ValueError('An exact, complete public-universe evidence bundle is required.')
    if c.scalar(select(m.user_account.c.status).where(m.user_account.c.user_account_id == actor)) != 'ACTIVE':
        raise ValueError('An active recorded seed operator account is required.')
    c.execute(select(func.pg_advisory_xact_lock(2026100650040)))
    source = c.scalar(select(m.integration_source_system.c.integration_source_system_id).where(
        m.integration_source_system.c.system_code == 'PUBLIC_INDEX_UNIVERSE_SEED',
        m.integration_source_system.c.tenant_id.is_(None), m.integration_source_system.c.status == 'ACTIVE'))
    if source is None:
        raise ValueError('Seed the curated reference universe first.')
    digest = sha256(path.read_bytes()).hexdigest()
    payload = c.execute(select(m.source_payload).where(
        m.source_payload.c.integration_source_system_id == source,
        m.source_payload.c.external_message_reference == 'index-trading-starts-2026-10-08')).mappings().one_or_none()
    if payload:
        _same(payload.payload_sha256, digest, 'trading-start evidence hash')
        payload_id = payload.source_payload_id
    else:
        payload_id = _insert(c, m.source_payload, 'source_payload_id', integration_source_system_id=source,
            payload_format='JSON', external_message_reference='index-trading-starts-2026-10-08',
            payload_locator=str(path.resolve()), payload_sha256=digest, processing_status='VALIDATED')
    count = 0
    for entry in entries:
        row = reviewed[entry['isin'], entry['mic']]
        expected_symbol = yahoo_symbol(row['symbol'], row['mic'])
        _same(entry['symbol'], expected_symbol, 'provider symbol')
        assessment = assess_start(entry['providerMetadata'], expected_symbol, row['mic'], row['currency'])
        _same({k:entry[k] for k in assessment}, assessment, 'trading-start assessment')
        # Retained source lineage is checked where available. A fresh seeded
        # database may consume the reviewed offline bundle without copying MD.
        retained = c.execute(select(m.market_data_ingestion_run).where(
            m.market_data_ingestion_run.c.source_payload_id == entry['sourcePayloadId'])).mappings().one_or_none()
        if retained:
            _same(retained.content_sha256, entry['sourceSha256'], 'retained evidence')
            _same(json.loads(retained.raw_payload)['chart']['result'][0]['meta'], entry['providerMetadata'], 'provider metadata')
        start = date.fromisoformat(entry['effectiveFrom'])
        for table, versions, key, code, fields in (
            (m.instrument, m.instrument_definition_version, 'instrument_node_id', 'PUBLIC_EQ_'+row['isin'],
             ('instrument_type_id','asset_class','issuer_organisation_id','base_currency_id')),
            (m.listing, m.listing_definition_version, 'listing_node_id', 'PUBLIC_LIST_'+row['isin']+'_'+row['mic'],
             ('market_venue_id','trading_currency_id','trading_symbol','quote_factor','unit_multiplier')),
        ):
            node = c.scalar(select(m.financial_reference_node.c.reference_node_id).where(
                m.financial_reference_node.c.internal_code == code, m.financial_reference_node.c.status == 'ACTIVE'))
            scope = c.execute(select(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id == node)).mappings().one()
            _same((scope.scope_type, scope.owner_tenant_id, scope.status), ('SHARED_CANONICAL', None, 'ACTIVE'), 'seed scope')
            projection = c.execute(select(table).where(table.c[key] == node).with_for_update()).mappings().one()
            definitions = c.execute(select(versions).where(versions.c[key] == node).with_for_update()).mappings().all()
            current = [v for v in definitions if v.is_current and v.status == 'APPROVED']
            if len(current) != 1:
                raise ValueError('Exactly one current approved seeded definition is required.')
            original = current[0]
            _same((original.effective_from, original.effective_to, original.sequence_no), (SNAPSHOT, None, 1), 'original approval')
            _same(tuple(projection[f] for f in fields), tuple(original[f] for f in fields), 'unchanged seeded economics')
            _same(projection.effective_to, None, 'active lifecycle')
            if table is m.instrument:
                _same((projection.is_current, projection.sequence_no), (True, 1), 'instrument lifecycle')
            else:
                _same((projection.status, projection.instrument_node_id, projection.trading_symbol),
                      ('ACTIVE', c.scalar(select(m.financial_reference_node.c.reference_node_id).where(
                          m.financial_reference_node.c.internal_code == 'PUBLIC_EQ_'+row['isin'])), row['symbol']), 'listing identity')
            history = [v for v in definitions if v is not original]
            if history:
                if len(history) != 1:
                    raise ValueError('Unexpected existing historical definitions; refusing overwrite.')
                old = history[0]
                _same((old.status, old.is_current, old.effective_from, old.effective_to, old.source_payload_id),
                      ('APPROVED', False, start, SNAPSHOT-timedelta(days=1), payload_id), 'historical approval')
                _same(tuple(old[f] for f in fields), tuple(original[f] for f in fields), 'historical economics')
                if projection.effective_from not in (start, booking_start(entry)):
                    raise ValueError('Historical lifecycle differs; refusing overwrite.')
            else:
                _same(projection.effective_from, SNAPSHOT, 'original lifecycle')
                values = {f:original[f] for f in fields}
                c.execute(versions.insert().values(**values, **{key:node}, sequence_no=2,
                    is_current=False, status='APPROVED', effective_from=start, effective_to=SNAPSHOT-timedelta(days=1),
                    source_payload_id=payload_id, approved_by_user_account_id=actor, approved_at_utc=datetime.now(timezone.utc)))
                c.execute(table.update().where(table.c[key] == node).values(effective_from=start))
                count += 1
    adjusted, bounds_payload = _apply_lifecycle_bounds(c, source, entries)
    primary = sum(r['basis']=='PRIMARY_REGULAR_WAY' or r['symbol'] in LIFECYCLE_BOUNDS for r in entries)
    return dict(listings=len(entries), appendedDefinitions=count, sourcePayloadId=str(payload_id),
        primaryRegularWay=primary, providerHistoryEstimates=len(entries)-primary,
        lifecycleBoundsAdjusted=adjusted, lifecycleBoundsSourcePayloadId=bounds_payload)
