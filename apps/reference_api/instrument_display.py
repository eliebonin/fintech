"""Bounded tenant-visible display reads; no writes, financial terms or public label endpoint."""
from collections import defaultdict
from collections.abc import Iterable
from uuid import UUID
from sqlalchemy import select,func,or_
from sqlalchemy.engine import Connection
from security_master_schema import models as m
from security_master_schema.governance_clock import governance_date
from security_master_schema.instrument_display import make_instrument_display
from .instrument_display_contracts import InstrumentDisplayView


def _chunks(values):
    values=list(values)
    for start in range(0,len(values),500):yield values[start:start+500]


def load_instrument_displays(c:Connection,tenant_id:UUID,reference_ids:Iterable[UUID|str|None])->dict[str,InstrumentDisplayView]:
    """Resolve exact nodes/canonical listing parents, never derivative underlyings."""
    from .repository import _market_data_visible_node_clause
    ids=set()
    for value in reference_ids:
        try:ids.add(UUID(str(value)))
        except (ValueError,TypeError):continue
    if not ids:return {}
    node=m.financial_reference_node;parent=node.alias('display_canonical_parent');listing=m.listing
    quote=m.currency.alias('display_quote_currency');denomination=m.currency.alias('display_denomination_currency')
    rows=[]
    for chunk in _chunks(ids):
        query=select(node.c.reference_node_id,node.c.canonical_name,node.c.internal_code,
            parent.c.reference_node_id.label('parent_id'),parent.c.canonical_name.label('parent_name'),
            m.instrument_type.c.type_code,m.instrument_type.c.display_name.label('type_label'),listing.c.trading_symbol,listing.c.market_venue_id,
            m.market_venue.c.display_name.label('venue'),quote.c.currency_code.label('quote_currency'),
            denomination.c.currency_code.label('denomination_currency')).select_from(
                node.outerjoin(listing,listing.c.listing_node_id==node.c.reference_node_id)
                .outerjoin(m.instrument,m.instrument.c.instrument_node_id==func.coalesce(listing.c.instrument_node_id,node.c.reference_node_id))
                .outerjoin(parent,parent.c.reference_node_id==m.instrument.c.instrument_node_id)
                .outerjoin(m.instrument_type,m.instrument_type.c.instrument_type_id==m.instrument.c.instrument_type_id)
                .outerjoin(m.market_venue,m.market_venue.c.market_venue_id==listing.c.market_venue_id)
                .outerjoin(quote,quote.c.currency_id==listing.c.trading_currency_id)
                .outerjoin(denomination,denomination.c.currency_id==m.instrument.c.base_currency_id)).where(
                    node.c.reference_node_id.in_(chunk),_market_data_visible_node_clause(node.c.reference_node_id,tenant_id))
        rows.extend(c.execute(query).mappings())
    # Only IDs derived from visible rows may reach these supporting reads.
    visible_ids={value for row in rows for value in (row['reference_node_id'],row['parent_id']) if value}
    identifiers=defaultdict(list);assignment=m.financial_reference_identifier;as_of=governance_date()
    for chunk in _chunks(visible_ids):
        query=select(assignment,m.identifier_scheme.c.scheme_code).join(m.identifier_scheme).where(
            assignment.c.reference_node_id.in_(chunk),
            or_(assignment.c.valid_from.is_(None),assignment.c.valid_from<=as_of),
            or_(assignment.c.valid_to.is_(None),assignment.c.valid_to>=as_of)).order_by(
                assignment.c.is_primary.desc(),assignment.c.valid_from.desc().nulls_last(),assignment.c.identifier_value)
        for value in c.execute(query).mappings():identifiers[value['reference_node_id']].append(value)
    swap_ids={row['parent_id'] or row['reference_node_id'] for row in rows if row['type_code']=='SWAP'}
    tenant_codes=defaultdict(set)
    for chunk in _chunks(swap_ids):
        definition=m.instrument_definition_version;swap=m.swap_definition_version
        query=select(definition.c.instrument_node_id,swap.c.economics_payload['tenantIdentifier'].astext.label('tenant_identifier')).join(
            swap,swap.c.instrument_definition_version_id==definition.c.instrument_definition_version_id).where(
                definition.c.instrument_node_id.in_(chunk),definition.c.status=='APPROVED',definition.c.is_current.is_(True))
        for value in c.execute(query):
            if value.tenant_identifier:tenant_codes[value.instrument_node_id].add(value.tenant_identifier)
    result={}
    for row in rows:
        subject=row['reference_node_id'];canonical=row['parent_id'] or subject
        candidates=identifiers[subject]+(identifiers[canonical] if canonical!=subject else [])
        candidates=[dict(scheme=value['scheme_code'],value=value['identifier_value']) for value in candidates
            if value['context_market_venue_id'] is None or value['context_market_venue_id']==row['market_venue_id']]
        codes=tenant_codes[canonical]
        result[str(subject)]=InstrumentDisplayView(instrumentId=str(canonical) if row['type_code'] else None,**make_instrument_display(
            name=row['parent_name'] or row['canonical_name'],kind=row['type_code'],type_label=row['type_label'],identifiers=candidates,
            symbol=row['trading_symbol'],venue=row['venue'],
            currency=row['quote_currency'] or row['denomination_currency'],
            currency_role='quote' if row['quote_currency'] else 'denomination',
            tenant_identifier=next(iter(codes)) if len(codes)==1 else None,
            search_aliases=[row['canonical_name'],row['internal_code']] ))
    return result


def decorate_response(c,tenant_id,response,reference_ids):
    displays=load_instrument_displays(c,tenant_id,reference_ids)
    return response.model_copy(update={'meta':response.meta.model_copy(update={'instrument_displays':displays})})
