"""Search aliases sourced from approved terms, without duplicating identifiers."""
from sqlalchemy import exists, select
from security_master_schema import models as m


def swap_tenant_identifier_matches(node_id, query):
    definition = m.instrument_definition_version.alias('search_swap_definition')
    terms = m.swap_definition_version.alias('search_swap_terms')
    escaped = query.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    return exists(select(1).select_from(terms.join(definition,
        definition.c.instrument_definition_version_id == terms.c.instrument_definition_version_id)).where(
        definition.c.instrument_node_id == node_id,
        definition.c.status == 'APPROVED', definition.c.is_current,
        terms.c.economics_payload['tenantIdentifier'].astext.ilike(f'%{escaped}%', escape='\\')))
