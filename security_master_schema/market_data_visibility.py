"""Shared subject visibility, including a listing's parent economic instrument."""
from sqlalchemy import select,exists,and_,or_
from . import models as m


def visible_subject_clause(reference_node_id,tenant_id):
    def direct(node_id,suffix):
        scope=m.reference_node_scope.alias('market_data_scope_'+suffix)
        node=m.financial_reference_node.alias('market_data_node_'+suffix)
        return and_(exists(select(1).select_from(node).where(node.c.reference_node_id==node_id,node.c.status=='ACTIVE')),
            or_(~exists(select(1).select_from(scope).where(scope.c.reference_node_id==node_id)),
                exists(select(1).select_from(scope).where(scope.c.reference_node_id==node_id,scope.c.status=='ACTIVE',
                    or_(scope.c.scope_type=='SHARED_CANONICAL',and_(scope.c.scope_type=='TENANT_PRIVATE',scope.c.owner_tenant_id==tenant_id))))))
    listing=m.listing.alias('market_data_parent_listing')
    return and_(direct(reference_node_id,'subject'),~exists(select(1).select_from(listing).where(
        listing.c.listing_node_id==reference_node_id,~direct(listing.c.instrument_node_id,'parent'))))


def catalogue_subject_clause(reference_node_id, tenant_id):
    # Policy validation supplies literal UUIDs; catalogue reads supply columns.
    # Preserve both contracts while building the same parameterized predicate.
    if not hasattr(reference_node_id,'in_'):
        from sqlalchemy import literal
        reference_node_id=literal(reference_node_id,type_=m.financial_reference_node.c.reference_node_id.type)
    def direct(node_id, suffix):
        scope = m.reference_node_scope.alias('market_data_scope_' + suffix)
        node = m.financial_reference_node.alias('market_data_node_' + suffix)
        # An uncorrelated ACTIVE-ID set avoids a master-table rescan for every
        # series. Tenant scopes and the separate listing-parent check below are
        # unchanged. Equivalence is checked across subject/parent scope variants.
        active=select(node.c.reference_node_id).where(node.c.status=='ACTIVE').cte().prefix_with('MATERIALIZED')
        return and_(node_id.in_(select(active.c.reference_node_id)),
            or_(~exists(select(1).select_from(scope).where(scope.c.reference_node_id == node_id)),
                exists(select(1).select_from(scope).where(scope.c.reference_node_id == node_id,
                    scope.c.status == 'ACTIVE', or_(scope.c.scope_type == 'SHARED_CANONICAL',
                        and_(scope.c.scope_type == 'TENANT_PRIVATE', scope.c.owner_tenant_id == tenant_id))))))
    listing = m.listing.alias('market_data_parent_listing')
    return and_(direct(reference_node_id, 'subject'),
        ~exists(select(1).select_from(listing).where(listing.c.listing_node_id == reference_node_id,
            ~direct(listing.c.instrument_node_id, 'parent'))))
