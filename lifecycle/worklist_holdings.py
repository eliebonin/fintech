"""Scoped notification candidates and deadline states, never financial authority."""
from uuid import UUID
from sqlalchemy import select,func,or_
from security_master_schema import models as m
from security_master_schema.reference_visibility import visible_clause
from security_master_schema.strategy_access import strategy_predicate
from security_master_schema.governance_clock import governance_date
from .entitlements import current_selections


def milestone_state(milestone,now):
    stamp=milestone.get('atUtc')
    if stamp is not None:return ('UPCOMING','INFORMATION') if now<stamp else ('DUE','ACTIONABLE') if now==stamp else ('OVERDUE','ACTIONABLE')
    day=milestone['date']
    return ('UPCOMING','INFORMATION') if day>now.date() else ('DUE','ACTIONABLE') if day==now.date() else ('OVERDUE','ACTIONABLE')


def held_candidates(c,tenant,actor,query,now,*,instrument_type,event_type):
    """Only authorised held candidates; economic state comes from ledger below."""
    if {'FUTURE':'FUTURE_EXPIRY','OPTION':'OPTION_EXPIRY','STRUCTURED_PRODUCT':'STRUCTURED_OBSERVATION','SWAP':'STRUCTURED_OBSERVATION'}.get(instrument_type)!=event_type:raise ValueError('Unsupported notification product/event.')
    t,s,i,l,n=m.trade,m.strategy,m.instrument,m.listing,m.financial_reference_node
    choice=current_selections(c,tenant).subquery()
    parent=func.coalesce(l.c.instrument_node_id,t.c.reference_instrument_node_id,t.c.trade_subject_reference_node_id)
    statement=select(s.c.strategy_id,s.c.display_name.label('strategy_name'),i.c.instrument_node_id.label('instrument_id'),n.c.canonical_name.label('instrument_name'),n.c.status.label('reference_status'),choice.c.selected_tier,choice.c.revision.label('assistance_revision'),m.instrument_type.c.type_code.label('instrument_type')).select_from(
        t.join(s,s.c.strategy_id==t.c.strategy_id).outerjoin(l,l.c.listing_node_id==t.c.trade_subject_reference_node_id).join(i,i.c.instrument_node_id==parent).join(m.instrument_type,m.instrument_type.c.instrument_type_id==i.c.instrument_type_id).join(n,n.c.reference_node_id==i.c.instrument_node_id).join(choice,(choice.c.strategy_id==s.c.strategy_id)&(choice.c.event_type==event_type))).where(
        s.c.tenant_id==tenant,choice.c.selected_tier>=1,m.instrument_type.c.type_code==instrument_type,t.c.price_basis.is_distinct_from('CASH_AMOUNT'),t.c.trade_datetime_utc<=now,t.c.created_at_utc<=now,
        strategy_predicate(c,tenant,actor,'LIFECYCLE_READ',s.c.strategy_id),visible_clause(i.c.instrument_node_id,tenant),visible_clause(t.c.trade_subject_reference_node_id,tenant))
    if query.strategyId:statement=statement.where(s.c.strategy_id==query.strategyId)
    if query.instrumentId:statement=statement.where(i.c.instrument_node_id==query.instrumentId)
    if text:=query.q.strip():
        identifier=m.financial_reference_identifier
        listed=select(l.c.listing_node_id).where(l.c.instrument_node_id==i.c.instrument_node_id,visible_clause(l.c.listing_node_id,tenant)).correlate(i)
        match=select(identifier.c.financial_reference_identifier_id).where(or_(identifier.c.reference_node_id==i.c.instrument_node_id,identifier.c.reference_node_id.in_(listed)),identifier.c.identifier_value.icontains(text,autoescape=True),or_(identifier.c.valid_from.is_(None),identifier.c.valid_from<=governance_date()),or_(identifier.c.valid_to.is_(None),identifier.c.valid_to>=governance_date())).correlate(i).exists()
        filters=[n.c.canonical_name.icontains(text,autoescape=True),match]
        try:filters.append(i.c.instrument_node_id==UUID(text))
        except ValueError:pass
        statement=statement.where(or_(*filters))
    return [dict(row) for row in c.execute(statement.distinct().order_by(s.c.strategy_id,i.c.instrument_node_id)).mappings()]
