"""Advisory cash readiness, sharing the authoritative writer's validation."""
from datetime import date, datetime, timezone
from .problem_details import current_api_version
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, exists, String, cast
from security_master_schema import models as m
from security_master_schema.tenant_workspace import TenantActionForbidden
from .booking_controls import authorize_booking
from .booking_errors import RepositoryNotFound
from .cash_booking_integrity import CASH_TYPES, CashBookingRefusal, load_cash_booking_listing
from .contracts import ApiMeta, CashBookingListingView, CashBookingListingResponse, CashBookingListingSearchResponse
from .tenant_context import TenantContext, get_tenant_context
from .problem_details import current_request_id
from .product_booking import visible_clause


def _utc_today():
    return datetime.now(timezone.utc).date()


def _candidates(tenant):
    node = m.financial_reference_node
    parent = node.alias('cash_parent')
    venue_mic = select(m.market_venue_identifier.c.identifier_value).where(
        m.market_venue_identifier.c.market_venue_id == m.market_venue.c.market_venue_id,
        m.market_venue_identifier.c.identifier_scheme == 'ISO_10383_MIC',
    ).order_by(m.market_venue_identifier.c.is_primary.desc(), m.market_venue_identifier.c.identifier_value).limit(1).correlate(m.market_venue).scalar_subquery()
    return select(m.listing, node.c.canonical_name, node.c.internal_code, node.c.status.label('node_status'),
        node.c.is_tradable, parent.c.status.label('parent_status'), m.instrument_type.c.type_code,
        m.currency.c.currency_code, m.market_venue.c.display_name.label('venue_name'), venue_mic.label('venue_mic')).select_from(
        m.listing.join(node, node.c.reference_node_id == m.listing.c.listing_node_id)
        .join(m.instrument, m.instrument.c.instrument_node_id == m.listing.c.instrument_node_id)
        .join(parent, parent.c.reference_node_id == m.instrument.c.instrument_node_id)
        .join(m.instrument_type, m.instrument_type.c.instrument_type_id == m.instrument.c.instrument_type_id)
        .join(m.currency, m.currency.c.currency_id == m.listing.c.trading_currency_id)
        .join(m.market_venue, m.market_venue.c.market_venue_id == m.listing.c.market_venue_id)
    ).where(m.instrument_type.c.type_code.in_(CASH_TYPES), visible_clause(node.c.reference_node_id, tenant),
            visible_clause(parent.c.reference_node_id, tenant))


def _view(connection, tenant, row, as_of):
    # Scope checks precede any dependency messages. Inactive visible references
    # are inspectable; foreign or revoked scopes never reach this boundary.
    status, reason = 'READY', None
    if row.node_status != 'ACTIVE' or row.parent_status != 'ACTIVE' or row.status != 'ACTIVE':
        status, reason = 'INACTIVE', 'The listing or its parent is inactive. Inspect the instrument before booking.'
    else:
        try:
            load_cash_booking_listing(connection, tenant, row.listing_node_id, as_of, lock=False)
        except CashBookingRefusal as error:
            status, reason = error.readiness_status, str(error)
        except RepositoryNotFound as error:
            # A concurrent scope change remains opaque, not an inspectable row.
            raise error
    return CashBookingListingView(referenceNodeId=row.listing_node_id, canonicalName=row.canonical_name,
        internalCode=row.internal_code, nodeType='LISTING', instrumentType=row.type_code,
        status=row.status, isTradable=row.is_tradable, parentReferenceNodeId=row.instrument_node_id,
        venueName=row.venue_name, marketVenueMic=row.venue_mic, tradingSymbol=row.trading_symbol, tradingCurrency=row.currency_code,
        bookingEligible=status == 'READY', readinessStatus=status, ineligibilityMessage=reason, asOfDate=as_of)


def get_cash_booking_listing(connection, tenant, listing_id, as_of):
    row = connection.execute(_candidates(tenant).where(m.listing.c.listing_node_id == listing_id)).mappings().first()
    if row is None:
        raise RepositoryNotFound('Visible cash listing was not found.')
    return _view(connection, tenant, row, as_of)


def search_cash_booking_listings(connection, tenant, query, limit, offset, as_of):
    statement = _candidates(tenant)
    if query.strip():
        escaped = query.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        term = f'%{escaped}%'
        ids = (m.listing.c.listing_node_id, m.listing.c.instrument_node_id)
        statement = statement.where(or_(m.financial_reference_node.c.canonical_name.ilike(term, escape='\\'),
            m.financial_reference_node.c.internal_code.ilike(term, escape='\\'), m.listing.c.trading_symbol.ilike(term, escape='\\'),
            m.market_venue.c.display_name.ilike(term, escape='\\'), cast(m.listing.c.listing_node_id, String) == query.strip(),
            exists(select(1).select_from(m.financial_reference_identifier).where(
                m.financial_reference_identifier.c.reference_node_id.in_(ids),
                m.financial_reference_identifier.c.identifier_value.ilike(term, escape='\\'))),
            exists(select(1).select_from(m.market_venue_identifier).where(
                m.market_venue_identifier.c.market_venue_id == m.listing.c.market_venue_id,
                m.market_venue_identifier.c.identifier_value.ilike(term, escape='\\')))))
    total = connection.scalar(select(func.count()).select_from(statement.subquery()))
    rows = connection.execute(statement.order_by(m.financial_reference_node.c.canonical_name, m.listing.c.listing_node_id)
                              .limit(limit).offset(offset)).mappings().all()
    data = []
    for row in rows:
        try:
            data.append(_view(connection, tenant, row, as_of))
        except RepositoryNotFound:
            continue
    return data, total


def cash_booking_readiness_router(connection_dependency, assert_membership):
    router = APIRouter()
    def authorized(connection, context):
        actor = assert_membership(connection, context)
        try:
            authorize_booking(connection, context.tenant_id, actor)
        except TenantActionForbidden as error:
            raise HTTPException(403, 'Trade booking is not permitted') from error
    def meta(context, **kwargs):
        return ApiMeta(tenantContext=str(context.tenant_id), source='live-reference-api', apiVersion=current_api_version(),
                       correlationId=current_request_id(), **kwargs)
    @router.get('/v1/trades/cash-listings', response_model=CashBookingListingSearchResponse)
    def search(q: str = Query(default='', max_length=250), asOfDate: date = Query(default_factory=_utc_today),
               limit: int = Query(default=25, ge=1, le=100), offset: int = Query(default=0, ge=0),
               context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency, scope='function')):
        authorized(connection, context)
        data, total = search_cash_booking_listings(connection, context.tenant_id, q, limit, offset, asOfDate)
        return CashBookingListingSearchResponse(data=data, meta=meta(context, limit=limit, offset=offset, total=total))
    @router.get('/v1/trades/cash-listings/{listing_id}', response_model=CashBookingListingResponse)
    def detail(listing_id: UUID, asOfDate: date = Query(default_factory=_utc_today),
               context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency, scope='function')):
        authorized(connection, context)
        try:
            return CashBookingListingResponse(data=get_cash_booking_listing(connection, context.tenant_id, listing_id, asOfDate), meta=meta(context))
        except RepositoryNotFound as error:
            raise HTTPException(404, str(error)) from error
    return router
