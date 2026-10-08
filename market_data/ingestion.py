"""Retain, normalize and publish a bounded daily delivery atomically; never fetch."""
from datetime import date, datetime
from hashlib import sha256
import json

from .contracts import DeliveryParser, ListingContext, ProviderSpec
from .rights import load_rights
from . import storage


def validate_normalized(parsed,provider,start,end,received_at):
    from decimal import Decimal,localcontext
    dimensions={}
    for point in parsed.points:
        if (point.series_type not in provider.series_types or not point.field or not point.value_basis
                or not parsed.timestamp_semantics or not start<=point.market_date<=end
                or point.observed_at.utcoffset() is None or point.observed_at>received_at
                or not isinstance(point.value,Decimal) or not point.value.is_finite()
                or not Decimal('0')<point.value<Decimal('1e18')):
            raise ValueError('Invalid normalized daily PRICE point or dimensions')
        with localcontext() as ctx:
            ctx.prec=40
            if point.value!=point.value.quantize(Decimal('0.000000000001')):
                raise ValueError('Normalized PRICE must match database precision')
        identity=(point.field,point.value_basis,parsed.timestamp_semantics)
        if point.series_type in dimensions and dimensions[point.series_type]!=identity:
            raise ValueError('Inconsistent normalized series dimensions')
        dimensions[point.series_type]=identity


def ingest_delivery(c, *, provider: ProviderSpec, parser: DeliveryParser,
                    dataset_id, namespace_id, symbol: str, raw_payload: str,
                    delivery_key: str, received_at: datetime, start: date, end: date) -> dict:
    """Caller owns commit/rollback; the injected parser owns provider semantics."""
    if (received_at.utcoffset() is None or not delivery_key or len(delivery_key) > 250
            or len(raw_payload.encode('utf-8')) > provider.max_payload_bytes
            or end < start or (end - start).days+1 > provider.max_window_days):
        raise ValueError('Invalid receipt, delivery identity or bounded payload/window')
    dataset, profile = storage.lock_dataset(c, dataset_id, namespace_id)
    evidence = []
    for activity in ('ACQUIRE', 'STORE'):
        decision = load_rights(c, dataset_id, activity, received_at.date())
        if not decision.allowed:
            raise PermissionError(f'{activity}: {decision.reason}')
        evidence.extend(decision.evidence)
    digest = sha256(raw_payload.encode('utf-8')).hexdigest()
    request = dict(namespaceId=str(namespace_id), symbol=symbol, start=start.isoformat(), end=end.isoformat())
    prior = storage.previous_delivery(c, dataset_id, delivery_key)
    if prior:
        if prior['content_sha256'] != digest or prior['report']['request'] != request:
            raise ValueError('Delivery key already exists with different content or parameters')
        return dict(prior['report'], runId=str(prior['run_id']), replayed=True)
    run_id, source_payload_id = storage.retain_payload(c, namespace_id=namespace_id,
        profile=profile, delivery_key=delivery_key, digest=digest, received_at=received_at)
    report = dict(accepted=0, duplicates=0, rejected=0, rejections=[], request=request)
    try:
        mapping, listing = storage.resolve_listing(c, namespace_id=namespace_id,
            symbol=symbol, received_at=received_at, permitted_tenant_id=profile['permitted_tenant_id'])
        storage.validate_series(c, listing=listing, dataset_id=dataset_id, provider=provider)
        parsed = parser(json.loads(raw_payload), symbol=symbol,
            listing=ListingContext(listing['currency_code'], listing['mic'], listing['timezone_name']),
            start=start, end=end, received_at=received_at)
        if any(point.series_type not in provider.series_types for point in parsed.points):
            raise ValueError('Adapter returned an undeclared series type')
        validate_normalized(parsed,provider,start,end,received_at)
        storage.validate_dimensions(c,listing['listing_node_id'],dataset_id,parsed)
        from .history import history_status
        report['historicalContinuity']=history_status(c,mapping['external_object_mapping_id'],start,end)
        if report['historicalContinuity']=='REJECTED':
            raise ValueError('Historical mapping review rejects this market-date interval')
        report['rejections'].extend(parsed.rejections)
    except (ValueError, TypeError) as exc:
        report['rejections'].append(dict(reason=str(exc)))
        parsed = None
    if parsed and parsed.points:
        storage.publish_points(c, parsed=parsed, provider=provider, dataset=dataset,
            listing=listing, mapping=mapping, symbol=symbol, delivery_key=delivery_key,
            digest=digest, source_payload_id=source_payload_id, received_at=received_at,
            evidence=evidence, report=report)
    storage.finish_delivery(c, run_id=run_id, dataset_id=dataset_id,
        source_payload_id=source_payload_id, delivery_key=delivery_key, digest=digest,
        raw_payload=raw_payload, received_at=received_at, evidence=evidence, report=report)
    return dict(report, replayed=False)
