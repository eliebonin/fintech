"""Shared reference visibility, with a retained joined-query compatibility predicate."""
from sqlalchemy import select, exists, and_, or_
from . import models as m
from .errors import RepositoryNotFound

def visible_clause(reference_id, tenant):
    scope = m.reference_node_scope.alias()
    return ~exists(select(1).select_from(scope).where(
        scope.c.reference_node_id == reference_id,
        ~and_(scope.c.status == 'ACTIVE', or_(scope.c.scope_type == 'SHARED_CANONICAL',
             and_(scope.c.scope_type == 'TENANT_PRIVATE', scope.c.owner_tenant_id == tenant)))))


def require_visible(connection, tenant, node_id):
    node = connection.execute(select(m.financial_reference_node).where(
        m.financial_reference_node.c.reference_node_id == node_id,
        m.financial_reference_node.c.status == 'ACTIVE', visible_clause(node_id, tenant))).mappings().first()
    if node is None: raise RepositoryNotFound('Active visible reference was not found.')
    return node



def joined_scope_clause(tenant_id):
    scope = m.reference_node_scope
    return or_(
        scope.c.reference_node_id.is_(None),
        and_(scope.c.status == "ACTIVE", or_(
            scope.c.scope_type == "SHARED_CANONICAL",
            and_(scope.c.scope_type == "TENANT_PRIVATE", scope.c.owner_tenant_id == tenant_id),
        )),
    )
