"""Three-query catalogue projection; full evidence remains on detail endpoints."""
from datetime import date
from sqlalchemy import and_, func, or_, select
from security_master_schema import models as m
from .contracts import ApiMeta, InstrumentCatalogueItem, InstrumentCatalogueResponse
from .repository import _base_instrument_select, _search_predicate


def search_instrument_catalogue(connection, tenant_id, query, limit, offset, api_version,
                                correlation_id, instrument_type=None, asset_class=None, status=None):
    rn, inst, typ, _, columns, stmt = _base_instrument_select(tenant_id)
    stmt = stmt.with_only_columns(*(columns[i] for i in (0, 1, 2, 3, 4, 6)))
    predicate = _search_predicate(tenant_id, query, rn, inst, typ)
    if predicate is not None:
        stmt = stmt.where(predicate)
    if instrument_type:
        stmt = stmt.where(typ.c.type_code == instrument_type.upper())
    if asset_class:
        stmt = stmt.where(m.instrument_definition_version.c.asset_class == asset_class.upper())
    if status:
        stmt = stmt.where(rn.c.status == status.upper())
    total = int(connection.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())))
    # Stable tie ordering prevents duplicates/omissions when names are equal.
    rows = connection.execute(stmt.order_by(rn.c.canonical_name, rn.c.reference_node_id)
                              .limit(limit).offset(offset)).mappings().all()
    counts = {}
    if rows:
        listing, version = m.listing, m.listing_definition_version
        scope = m.reference_node_scope.alias('catalogue_listing_scope')
        as_of = date.today()
        counts = dict(connection.execute(select(listing.c.instrument_node_id, func.count())
            .select_from(listing.join(version, and_(
                version.c.listing_node_id == listing.c.listing_node_id,
                version.c.status == 'APPROVED', version.c.is_current.is_(True),
                version.c.effective_from <= as_of,
                or_(version.c.effective_to.is_(None), version.c.effective_to >= as_of)))
                .join(m.market_venue, version.c.market_venue_id == m.market_venue.c.market_venue_id)
                .join(m.currency, version.c.trading_currency_id == m.currency.c.currency_id)
                .outerjoin(scope, scope.c.reference_node_id == listing.c.listing_node_id))
            .where(listing.c.instrument_node_id.in_([row.instrument_id for row in rows]))
            .where(or_(scope.c.reference_node_id.is_(None), and_(scope.c.status == 'ACTIVE', or_(
                scope.c.scope_type == 'SHARED_CANONICAL',
                and_(scope.c.scope_type == 'TENANT_PRIVATE', scope.c.owner_tenant_id == tenant_id)))))
            .group_by(listing.c.instrument_node_id)).all())
    return InstrumentCatalogueResponse(data=[InstrumentCatalogueItem(
        instrumentId=row.instrument_id, canonicalName=row.canonical_name,
        instrumentType=row.instrument_type, assetClass=row.asset_class,
        status=row.node_status, baseCurrency=row.base_currency,
        listingCount=counts.get(row.instrument_id, 0)) for row in rows],
        meta=ApiMeta(tenantContext=str(tenant_id), source='live-reference-api',
                     apiVersion=api_version, correlationId=correlation_id,
                     limit=limit, offset=offset, total=total))
