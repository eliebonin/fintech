"""Scoped discovery candidates and batched native history; no financial writes."""
from collections import defaultdict
from uuid import UUID
from sqlalchemy import select,func,or_,case
from security_master_schema import models as m
from security_master_schema.strategy_access import strategy_predicate
from security_master_schema.reference_visibility import visible_clause
from .entitlements import current_selections
from security_master_schema.governance_clock import governance_date


def candidate_pairs(c,tenant,actor,query,now,*,coupon_visibility=False):
    t,s,i,l,d,n=m.trade,m.strategy,m.instrument,m.listing,m.instrument_dates,m.financial_reference_node
    choice=current_selections(c,tenant).subquery()
    event_type=case((m.instrument_type.c.type_code=='BOND','BOND_MATURITY'),(m.instrument_type.c.type_code=='FX_FORWARD','FX_FORWARD_MATURITY'))
    parent=func.coalesce(l.c.instrument_node_id,t.c.reference_instrument_node_id,t.c.trade_subject_reference_node_id)
    statement=select(s.c.strategy_id,s.c.display_name.label('strategy_name'),i.c.instrument_node_id.label('instrument_id'),n.c.canonical_name.label('instrument_name'),n.c.status.label('reference_status'),d.c.maturity_date,choice.c.selected_tier,choice.c.revision.label('assistance_revision'),choice.c.event_type,m.instrument_type.c.type_code.label('instrument_type')).select_from(t.join(s,s.c.strategy_id==t.c.strategy_id).outerjoin(l,l.c.listing_node_id==t.c.trade_subject_reference_node_id).join(i,i.c.instrument_node_id==parent).join(m.instrument_type,m.instrument_type.c.instrument_type_id==i.c.instrument_type_id).join(n,n.c.reference_node_id==i.c.instrument_node_id).outerjoin(d,d.c.instrument_node_id==i.c.instrument_node_id).join(choice,(choice.c.strategy_id==s.c.strategy_id)&(choice.c.event_type==event_type))).where(s.c.tenant_id==tenant,choice.c.selected_tier>=1,m.instrument_type.c.type_code.in_(['BOND','FX_FORWARD']),t.c.price_basis.is_distinct_from('CASH_AMOUNT'),t.c.trade_datetime_utc<=now,t.c.created_at_utc<=now,strategy_predicate(c,tenant,actor,'LIFECYCLE_READ',s.c.strategy_id),visible_clause(i.c.instrument_node_id,tenant),visible_clause(t.c.trade_subject_reference_node_id,tenant))
    if query.eventType!='ALL':statement=statement.where(choice.c.event_type==query.eventType)
    date_match=(d.c.maturity_date>=query.fromDate)&(d.c.maturity_date<=query.toDate)
    if query.includeEarlierOverdue:date_match=or_(date_match,(d.c.maturity_date<query.fromDate)&(d.c.maturity_date<now.date()))
    # A missing reference date is an actionable data-quality event, not an
    # invented maturity or a silent disappearance from the operational book.
    if not coupon_visibility:statement=statement.where(or_(date_match,d.c.maturity_date.is_(None)))
    if query.strategyId:statement=statement.where(s.c.strategy_id==query.strategyId)
    if query.instrumentId:statement=statement.where(i.c.instrument_node_id==query.instrumentId)
    if text:=query.q.strip():
        # Keep search inside the authorised candidate query, before any source
        # reconstruction, full-population counts or pagination. Literal input
        # is escaped; listing identifiers never widen reference visibility.
        identifier=m.financial_reference_identifier
        listed=select(l.c.listing_node_id).where(l.c.instrument_node_id==i.c.instrument_node_id,visible_clause(l.c.listing_node_id,tenant)).correlate(i)
        identifiers=select(identifier.c.financial_reference_identifier_id).where(
            or_(identifier.c.reference_node_id==i.c.instrument_node_id,identifier.c.reference_node_id.in_(listed)),
            identifier.c.identifier_value.icontains(text,autoescape=True),
            or_(identifier.c.valid_from.is_(None),identifier.c.valid_from<=governance_date()),
            or_(identifier.c.valid_to.is_(None),identifier.c.valid_to>=governance_date())).correlate(i).exists()
        match=or_(n.c.canonical_name.icontains(text,autoescape=True),identifiers)
        try:identity=UUID(text)
        except ValueError:pass
        else:match=or_(match,i.c.instrument_node_id==identity)
        statement=statement.where(match)
    return [dict(row) for row in c.execute(statement.distinct().order_by(d.c.maturity_date.asc().nulls_first(),s.c.strategy_id,i.c.instrument_node_id)).mappings()]


def source_maps(c,tenant,pairs,*,event_type='BOND_MATURITY'):
    proposal_table,posting_table=(m.fx_maturity_proposal,m.fx_maturity_posting) if event_type=='FX_FORWARD_MATURITY' else (m.bond_redemption_proposal,m.bond_redemption_posting)
    ids={r['instrument_id'] for r in pairs};strategies={r['strategy_id'] for r in pairs}
    subjects={identity:identity for identity in ids}
    for row in c.execute(select(m.listing.c.listing_node_id,m.listing.c.instrument_node_id).where(m.listing.c.instrument_node_id.in_(ids))):subjects[row.listing_node_id]=row.instrument_node_id
    terms=defaultdict(list)
    if event_type=='BOND_MATURITY':
        for row in c.execute(select(m.bond_terms).where(m.bond_terms.c.instrument_node_id.in_(ids),m.bond_terms.c.is_current)):terms[row.instrument_node_id].append(dict(row._mapping))
    identifiers=defaultdict(list)
    for row in c.execute(select(m.financial_reference_identifier.c.reference_node_id,m.financial_reference_identifier.c.identifier_value,m.identifier_scheme.c.scheme_code).join(m.identifier_scheme).where(m.financial_reference_identifier.c.reference_node_id.in_(ids),or_(m.financial_reference_identifier.c.valid_from.is_(None),m.financial_reference_identifier.c.valid_from<=governance_date()),or_(m.financial_reference_identifier.c.valid_to.is_(None),m.financial_reference_identifier.c.valid_to>=governance_date())).order_by(m.financial_reference_identifier.c.is_primary.desc(),m.financial_reference_identifier.c.identifier_value)):
        if row.scheme_code=='ISIN':identifiers[row.reference_node_id].append(row.identifier_value)
    proposals=defaultdict(list);postings=defaultdict(list)
    for row in c.execute(select(proposal_table).where(proposal_table.c.tenant_id==tenant,proposal_table.c.strategy_id.in_(strategies),proposal_table.c.instrument_id.in_(ids)).order_by(proposal_table.c.recorded_at.desc(),proposal_table.c.proposal_id.desc())).mappings():proposals[(row['strategy_id'],row['instrument_id'])].append(dict(row))
    for row in c.execute(select(posting_table).where(posting_table.c.tenant_id==tenant,posting_table.c.strategy_id.in_(strategies)).order_by(posting_table.c.recorded_at.desc(),posting_table.c.posting_id.desc())).mappings():
        identity=row['evidence'].get('instrumentId')
        if identity:postings[(row['strategy_id'],identity)].append(dict(row))
    # Native cancellation/correction retains the original posting. Completion
    # requires its generated trade links to remain active, not history alone.
    linked={UUID(value) for history in postings.values() for row in history for value in row['trade_ids']}
    states={str(row.trade_id):row.lifecycle_status for row in c.execute(select(m.trade.c.trade_id,m.trade.c.lifecycle_status).where(m.trade.c.trade_id.in_(linked),m.trade.c.strategy_id.in_(strategies)))}
    for history in postings.values():
        for row in history:row['_postingActive']=bool(row['trade_ids']) and all(states.get(str(value))=='BOOKED' for value in row['trade_ids'])
    return subjects,terms,identifiers,proposals,postings
