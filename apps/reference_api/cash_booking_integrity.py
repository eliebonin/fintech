"""Locked authoritative eligibility for listing-backed cash executions."""
from decimal import Decimal
from sqlalchemy import select
from security_master_schema import models as m
from .trade_properties import TradeFieldError

CASH_TYPES = frozenset({'EQUITY', 'ETF', 'ETC', 'ETN', 'ETV', 'ETI', 'DIGITAL_ASSET',
    'FUND', 'FUND_SHARE_CLASS', 'EXCHANGE_TRADED_VEHICLE', 'EXCHANGE_TRADED_CERTIFICATE'})


def _locked(connection, table, key, value, *, lock=True):
    statement = select(table).where(table.c[key] == value).order_by(*table.primary_key.columns)
    return connection.execute(statement.with_for_update() if lock else statement).mappings().all()


class CashBookingRefusal(TradeFieldError):
    def __init__(self, message, readiness_status):
        super().__init__('listingId', message)
        self.readiness_status = readiness_status


def _invalid(message, readiness_status='NOT_READY'):
    raise CashBookingRefusal(message, readiness_status)


def _definition(connection, table, key, value, execution_date, *, lock=True):
    rows = _locked(connection, table, key, value, lock=lock)
    approved = [row for row in rows if row.status == 'APPROVED' and row.is_current]
    if len(approved) != 1:
        _invalid('Exactly one current approved definition is required for the listing and its instrument.', 'MISSING_CONFIGURATION')
    eligible = [row for row in rows if row.status == 'APPROVED'
                and row.effective_from <= execution_date
                and (row.effective_to is None or execution_date <= row.effective_to)]
    if not eligible:
        _invalid('Execution date is outside the approved reference definition.')
    if len(eligible) != 1:
        _invalid('Ambiguous approved reference definitions cover the execution date.', 'MISSING_CONFIGURATION')
    return eligible[0]


def _within_lifecycle(projection, execution_date):
    # Overall reference availability and a particular version's business-valid
    # interval are distinct. Both must cover execution; approval time is not
    # backdated when a steward adds evidence-supported historical coverage.
    if ((projection.effective_from and projection.effective_from > execution_date)
            or (projection.effective_to and projection.effective_to < execution_date)):
        _invalid('Execution date is outside the reference lifecycle.')


def _consistent(projection, definition, fields):
    for field in fields:
        if projection[field] != definition[field]:
            _invalid('The listing or instrument differs from its approved definition. Reselect an approved reference.')


def load_cash_booking_listing(connection, tenant_id, listing_id, execution_date, *, lock=True):
    from .repository import RepositoryNotFound
    from .product_booking import require_visible
    listing = connection.execute(select(m.listing).where(m.listing.c.listing_node_id == listing_id)).mappings().first()
    if listing is None:
        raise RepositoryNotFound('Visible active listing does not exist')
    parent_id = listing.instrument_node_id
    instrument = connection.execute(select(m.instrument).where(m.instrument.c.instrument_node_id == parent_id)).mappings().first()
    if instrument is None:
        raise RepositoryNotFound('Visible active parent instrument does not exist')
    currencies = {}
    currency_ids = {listing.trading_currency_id, instrument.base_currency_id} - {None}
    for currency_id in sorted(currency_ids, key=str):
        rows = _locked(connection, m.currency, 'currency_id', currency_id, lock=lock)
        if len(rows) != 1 or rows[0].status != 'ACTIVE':
            _invalid('Listing and instrument currencies must be active.', 'INACTIVE')
        currencies[currency_id] = rows[0]
    for node_id in sorted({listing_id, parent_id}, key=str):
        _locked(connection, m.financial_reference_node, 'reference_node_id', node_id, lock=lock)
        _locked(connection, m.reference_node_scope, 'reference_node_id', node_id, lock=lock)
    listing_node = require_visible(connection, tenant_id, listing_id)
    parent_node = require_visible(connection, tenant_id, parent_id)
    locked_listing = _locked(connection, m.listing, 'listing_node_id', listing_id, lock=lock)
    locked_instrument = _locked(connection, m.instrument, 'instrument_node_id', parent_id, lock=lock)
    if len(locked_listing) != 1 or len(locked_instrument) != 1:
        raise RepositoryNotFound('Visible active listing or instrument does not exist')
    current_listing, current_instrument = locked_listing[0], locked_instrument[0]
    if (current_listing.instrument_node_id != parent_id or current_listing.trading_currency_id != listing.trading_currency_id
            or current_instrument.base_currency_id != instrument.base_currency_id):
        _invalid('Reference identities or currencies changed during booking. Reselect the listing.')
    listing, instrument = current_listing, current_instrument
    # Economic parents need not be directly tradable: the listing is this
    # execution's tradable subject (the existing canonical equity uses False).
    if listing.status != 'ACTIVE' or not listing_node.is_tradable or not instrument.is_current:
        _invalid('An active tradable listing and current approved instrument are required.')
    definition = _definition(connection, m.instrument_definition_version, 'instrument_node_id', parent_id, execution_date, lock=lock)
    listing_definition = _definition(connection, m.listing_definition_version, 'listing_node_id', listing_id, execution_date, lock=lock)
    _within_lifecycle(instrument, execution_date)
    _within_lifecycle(listing, execution_date)
    # Historical cash booking is deliberately limited to unchanged economics:
    # do not substitute today's currency, venue or factors for different terms.
    _consistent(instrument, definition, ('instrument_type_id', 'asset_class', 'issuer_organisation_id', 'base_currency_id'))
    if definition.is_current:
        _consistent(instrument, definition, ('sequence_no',))
    _consistent(listing, listing_definition, ('market_venue_id', 'trading_currency_id', 'trading_symbol', 'quote_factor', 'unit_multiplier'))
    for node, expected in sorted(((listing_node, 'LISTING'), (parent_node, 'INSTRUMENT')),
                                 key=lambda item: str(item[0].reference_node_type_id)):
        rows = _locked(connection, m.reference_node_type, 'reference_node_type_id', node.reference_node_type_id, lock=lock)
        if len(rows) != 1 or rows[0].status != 'ACTIVE' or rows[0].type_code != expected:
            _invalid('Active listing and instrument reference types are required.')
    types = _locked(connection, m.instrument_type, 'instrument_type_id', instrument.instrument_type_id, lock=lock)
    if len(types) != 1 or types[0].status != 'ACTIVE' or types[0].type_code not in CASH_TYPES:
        _invalid('This product requires a supported product-specific booking ticket; cash-share semantics are not permitted.')
    venues = _locked(connection, m.market_venue, 'market_venue_id', listing.market_venue_id, lock=lock)
    if len(venues) != 1 or venues[0].status != 'ACTIVE':
        _invalid('Execution venue must be active.', 'INACTIVE')
    if instrument.issuer_organisation_id:
        issuers = _locked(connection, m.organisation, 'organisation_id', instrument.issuer_organisation_id, lock=lock)
        if len(issuers) != 1 or issuers[0].status != 'ACTIVE':
            _invalid('Selected instrument issuer must be active.', 'INACTIVE')
    if listing.quote_factor <= 0 or listing.unit_multiplier <= 0:
        _invalid('Approved quote factor and unit multiplier must be positive.')
    return dict(listing) | {'currency_code':currencies[listing.trading_currency_id].currency_code,
        'booking_snapshot':dict(schemaVersion=1, kind='CASH_BOOKING', instrumentDefinitionId=str(definition.instrument_definition_version_id),
            listingDefinitionId=str(listing_definition.listing_definition_version_id), instrumentId=str(parent_id),
            quoteFactor=str(Decimal(listing.quote_factor)), unitMultiplier=str(Decimal(listing.unit_multiplier)),
            priceCurrencyId=str(listing.trading_currency_id))}
