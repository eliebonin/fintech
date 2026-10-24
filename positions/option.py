"""Read old/new option bookings without replacing their retained premium terms."""
from itertools import product
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.option_valuation import frozen_option_conventions
from .contracts import PositionError


def normalize_booking(c,row,snapshot,event,*,currency_cache=None):
    parent=row['reference_instrument_node_id'];subject=row['trade_subject_reference_node_id']
    explicit=snapshot.get('valuationConventions');day=row['trade_datetime_utc'].date()
    currency=c.scalar(select(m.currency.c.currency_code).where(m.currency.c.currency_id==row['price_currency_id']))
    # The exact original fingerprint binds these IDs. Do not infer ID lineage
    # from clock ordering: DB recorded_at may be transaction-start time, while
    # the approval's application timestamp is later in that same transaction.
    definitions=select(m.instrument_definition_version).where(m.instrument_definition_version.c.instrument_node_id==parent,
        m.instrument_definition_version.c.status.in_(('APPROVED','SUPERSEDED')))
    listings=select(m.listing_definition_version).where(m.listing_definition_version.c.listing_node_id==subject,
        m.listing_definition_version.c.status.in_(('APPROVED','SUPERSEDED')))
    options=select(m.option_terms.c.option_terms_id).where(m.option_terms.c.instrument_node_id==parent)
    if explicit is not None:
        definitions=definitions.where(m.instrument_definition_version.c.instrument_definition_version_id==UUID(explicit['instrumentDefinitionId']))
        listings=listings.where(m.listing_definition_version.c.listing_definition_version_id==UUID(explicit['listingDefinitionId']))
        options=options.where(m.option_terms.c.option_terms_id==UUID(explicit['optionTermsId']))
    matches=[]
    for definition,listing,terms_id in product(c.execute(definitions).mappings().all(),c.execute(listings).mappings().all(),c.scalars(options).all()):
        if any(record['effective_from']>day or (record['effective_to'] is not None and record['effective_to']<day)
            for record in (definition,listing)):continue
        if (definition['base_currency_id']!=row['price_currency_id'] or listing['trading_currency_id']!=row['price_currency_id']
            or listing['market_venue_id']!=row['execution_venue_id'] or Decimal(snapshot['economics']['terms']['quoteFactor'])!=listing['quote_factor']):continue
        identities=dict(instrumentDefinitionId=str(definition['instrument_definition_version_id']),
            listingDefinitionId=str(listing['listing_definition_version_id']),optionTermsId=str(terms_id),marketVenueId=str(listing['market_venue_id']))
        try:matches.append(frozen_option_conventions(row,snapshot,identities,currency))
        except ValueError:continue
    if len(matches)!=1:raise PositionError('Unique original option definitions matching frozen BOOKED fingerprint required')
    return matches[0] | dict(kind='OPTION_PREMIUM_BOOKING',valuationRecognition=snapshot.get('valuationRecognition'))
