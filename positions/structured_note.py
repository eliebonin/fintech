"""Resolve historical note version identities against the original booking hash.

The captured context predates flat valuation conventions. Matching its hash
recovers identities without substituting today's quotation or modifying trades.
"""
from itertools import product
import json
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.structured_note_valuation import frozen_note_conventions
from .contracts import PositionError


def normalize_booking(c,row,snapshot,*,identity_cache,sources=None):
    context=snapshot['economics']['terms'];parent=row['reference_instrument_node_id'];subject=row['trade_subject_reference_node_id']
    key=(parent,subject,context.get('termsFingerprint'));identities=identity_cache.get(key)
    if identities is None:
        cv=context['convention']
        definitions=sources.definitions(c,row) if sources is not None else c.execute(select(m.instrument_definition_version).where(
            m.instrument_definition_version.c.instrument_node_id==parent,
            m.instrument_definition_version.c.status.in_(('APPROVED','SUPERSEDED')))).mappings().all()
        conventions=[record for record in (sources.conventions(c,row) if sources is not None else c.execute(select(m.instrument_booking_convention).where(
            m.instrument_booking_convention.c.instrument_node_id==parent)).mappings())
            if json.loads(record['convention_payload'])==cv]
        terms=sources.note_terms(c,row) if sources is not None else c.execute(select(m.structured_product_terms.c.structured_product_terms_id).where(
            m.structured_product_terms.c.instrument_node_id==parent)).scalars().all()
        listings=(sources.listings(c,row) if sources is not None else c.execute(select(m.listing_definition_version).where(m.listing_definition_version.c.listing_node_id==subject,
            m.listing_definition_version.c.status.in_(('APPROVED','SUPERSEDED')))).mappings().all()) if context.get('listingId') else [None]
        matches=[];day=row['trade_datetime_utc'].date()
        for definition,convention,term,listing in product(definitions,conventions,terms,listings):
            if any(record['effective_from']>day or record['effective_to'] is not None and record['effective_to']<day
                    for record in (definition,listing) if record):continue
            if str(definition['base_currency_id'])!=cv['priceCurrencyId']:continue
            ids=dict(conventionId=str(convention['instrument_booking_convention_id']),
                definitionId=str(definition['instrument_definition_version_id']),structuredTermsId=str(term))
            if listing:ids.update(listingDefinitionId=str(listing['listing_definition_version_id']),venueId=str(listing['market_venue_id']))
            try:frozen_note_conventions(row,snapshot,ids)
            except ValueError:continue
            matches.append(ids)
        if len(matches)!=1:raise PositionError('Unique original structured-note definitions matching frozen BOOKED fingerprint required')
        identities=matches[0];identity_cache[key]=identities
    return frozen_note_conventions(row,snapshot,identities)|dict(valuationRecognition=snapshot.get('valuationRecognition'))
