"""Recover the uniquely fingerprint-bound historical futures version IDs."""
from itertools import product
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.booking_conventions import FutureConvention
from security_master_schema.future_valuation import frozen_future_conventions
from .contracts import PositionError


def normalize_booking(c,row,snapshot,*,identity_cache,sources=None):
    context=snapshot['economics']['terms'];fingerprint=context.get('termsFingerprint')
    cache_key=(row['reference_instrument_node_id'],row['trade_subject_reference_node_id'],fingerprint)
    identities=identity_cache.get(cache_key)
    if identities is None:
        parent=row['reference_instrument_node_id'];subject=row['trade_subject_reference_node_id'];day=row['trade_datetime_utc'].date()
        cv=FutureConvention.model_validate(context['convention'])
        definitions=sources.definitions(c,row) if sources is not None else c.execute(select(m.instrument_definition_version).where(
            m.instrument_definition_version.c.instrument_node_id==parent,
            m.instrument_definition_version.c.status.in_(('APPROVED','SUPERSEDED')))).mappings().all()
        listings=sources.listings(c,row) if sources is not None else c.execute(select(m.listing_definition_version).where(m.listing_definition_version.c.listing_node_id==subject,
            m.listing_definition_version.c.status.in_(('APPROVED','SUPERSEDED')))).mappings().all()
        conventions=[]
        for record in (sources.conventions(c,row) if sources is not None else c.execute(select(m.instrument_booking_convention).where(m.instrument_booking_convention.c.instrument_node_id==parent)).mappings()):
            if FutureConvention.model_validate_json(record['convention_payload'])==cv:conventions.append(record)
        family=sources.family(c,row) if sources is not None else c.scalar(select(m.future_terms.c.future_family_id).where(m.future_terms.c.instrument_node_id==parent))
        matches=[]
        for definition,listing,convention in product(definitions,listings,conventions):
            if any(record['effective_from']>day or record['effective_to'] is not None and record['effective_to']<day for record in (definition,listing)):continue
            if (definition['base_currency_id']!=cv.price_currency_id or listing['trading_currency_id']!=cv.price_currency_id
                or listing['market_venue_id']!=row['execution_venue_id'] or listing['quote_factor']!=cv.quote_factor):continue
            ids=dict(conventionId=str(convention['instrument_booking_convention_id']),definitionId=str(definition['instrument_definition_version_id']),
                listingDefinitionId=str(listing['listing_definition_version_id']),venueId=str(listing['market_venue_id']),
                familyId=str(family),underlyingId=context['underlyingId'])
            try:frozen_future_conventions(row,snapshot,ids)
            except ValueError:continue
            matches.append(ids)
        if len(matches)!=1:raise PositionError('Unique original futures definitions matching frozen BOOKED fingerprint required')
        identities=matches[0];identity_cache[cache_key]=identities
    return frozen_future_conventions(row,snapshot,identities)|dict(valuationRecognition=snapshot.get('valuationRecognition'))
