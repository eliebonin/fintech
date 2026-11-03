"""Trusted ingestion boundary for atomic source-price/accrual packages."""
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.evidence import evidence_hash
from .bond_quotes import component_payload,clean_quote,per_100_quote


def record_quote_accruals(c,components,recorded_at):
    """Caller owns source acquisition rights and transaction; no tenant write API.

    Each entry is observation UUID -> BondQuoteAccrual. Dataset/licence, source
    currency, instrument, quote date and correction identity cannot be overridden.
    """
    if not components:return
    if recorded_at.utcoffset() is None:raise ValueError('Quote evidence timestamp needs timezone')
    observation=m.market_data_observation;series=m.market_data_series
    rows=c.execute(select(observation,series.c.reference_node_id,series.c.currency_id,series.c.value_type,
        m.instrument_type.c.type_code).select_from(observation.join(series).outerjoin(m.listing,m.listing.c.listing_node_id==series.c.reference_node_id)
        .join(m.instrument,m.instrument.c.instrument_node_id==func.coalesce(m.listing.c.instrument_node_id,series.c.reference_node_id))
        .join(m.instrument_type)).where(observation.c.market_data_observation_id.in_(components))
        .order_by(observation.c.market_data_observation_id).with_for_update(of=observation)).mappings().all()
    sources={row['market_data_observation_id']:row for row in rows}
    if set(sources)!=set(components):raise ValueError('Every quote component requires its exact source price observation')
    dimensions={}
    for sid,code,value in c.execute(select(m.market_data_series_dimension.c.market_data_series_id,m.market_data_series_dimension.c.dimension_code,
        m.market_data_series_dimension.c.dimension_value).where(m.market_data_series_dimension.c.market_data_series_id.in_({r['market_data_series_id'] for r in rows}))):
        dimensions.setdefault(sid,{}).setdefault(code,set()).add(value)
    existing={row['observation_id']:row for row in c.execute(select(m.market_data_bond_quote_accrual).where(m.market_data_bond_quote_accrual.c.observation_id.in_(components))).mappings()}
    pending=[]
    for identifier,component in components.items():
        source=sources[identifier];payload=component_payload(component);dims=dimensions.get(source['market_data_series_id'],{})
        if (source['type_code']!='BOND' or source['value_type']!='PRICE' or source['value_basis']!='RAW' or source['quality_status']!='ACCEPTED'
            or not source['market_date'] or not source['currency_id'] or recorded_at<source['received_at_utc']
            or component.quote_settlement_date<source['market_date'] or dims.get('BOND_PRICE_TYPE')!={'DIRTY'} or not per_100_quote(dims.get('QUOTE_FACTOR',set()))):
            raise ValueError('Matching native RAW DIRTY bond quote, per-100 divisor, dates and currency required')
        clean_quote(source['value'],component.accrued_per_100)
        digest=evidence_hash(payload)
        if identifier in existing:
            if existing[identifier]['component_hash']!=digest:raise ValueError('Correct the price observation to revise its immutable accrued component')
            continue
        pending.append(dict(observation_id=identifier,accrued_interest_per_100=component.accrued_per_100,
            quote_settlement_date=component.quote_settlement_date,source_reference=payload['sourceReference'],recorded_at_utc=recorded_at,component_hash=digest))
    if pending:c.execute(m.market_data_bond_quote_accrual.insert(),pending)


def load_quote_accruals(c,observation_ids,information_cutoff=None):
    if not observation_ids:return {}
    table=m.market_data_bond_quote_accrual
    query=select(table).where(table.c.observation_id.in_(observation_ids))
    if information_cutoff is not None:query=query.where(table.c.recorded_at_utc<=information_cutoff)
    return {row['observation_id']:dict(row) for row in c.execute(query).mappings()}
