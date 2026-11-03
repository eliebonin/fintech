"""Governed version creation and read-only input preview; not valuation."""
from dataclasses import asdict
from sqlalchemy import select, or_
from security_master_schema import models as m
from security_master_schema.market_data_resolver import ResolutionRequest,resolve_market_data_batch
from security_master_schema.market_data_visibility import catalogue_subject_clause as _market_data_visible_node_clause
from .valuation_policy_contracts import PolicyView,PolicyOptions,ResolutionPreview
from .contracts import MarketDataResolutionSnapshotItemView
from .resource_limits import governance_date
from security_master_schema.strategy_access import request_strategy_predicate
from market_data import pricing_policies
from market_data.pricing_policies import authority


def options(c,tenant,actor):
    can_manage=authority(c,tenant,actor)
    def picks(table,id_col,label_col,conditions):
        return [dict(id=r[0],label=r[1]) for r in c.execute(select(id_col,label_col).where(*conditions).order_by(label_col).limit(500))]
    ent=m.tenant_dataset_entitlement
    return PolicyOptions(canManage=can_manage,
        cuts=picks(m.valuation_cut,m.valuation_cut.c.valuation_cut_id,m.valuation_cut.c.display_name,[m.valuation_cut.c.status=='ACTIVE']),
        venues=picks(m.market_venue,m.market_venue.c.market_venue_id,m.market_venue.c.display_name,[m.market_venue.c.status=='ACTIVE']),
        instrumentTypes=picks(m.instrument_type,m.instrument_type.c.instrument_type_id,m.instrument_type.c.type_code,[]),
        calendars=picks(m.market_calendar,m.market_calendar.c.market_calendar_id,m.market_calendar.c.display_name,[m.market_calendar.c.status=='ACTIVE',or_(m.market_calendar.c.tenant_id.is_(None),m.market_calendar.c.tenant_id==tenant)]),
        strategies=picks(m.strategy,m.strategy.c.strategy_id,m.strategy.c.display_name,[m.strategy.c.tenant_id==tenant,m.strategy.c.status=='ACTIVE',request_strategy_predicate(c,tenant,'STRATEGY_READ',m.strategy.c.strategy_id)]),
        datasets=picks(m.dataset,m.dataset.c.dataset_id,m.dataset.c.display_name,[m.dataset.c.dataset_id.in_(select(ent.c.dataset_id).where(
            ent.c.tenant_id==tenant,ent.c.status=='ACTIVE',ent.c.valid_from<=governance_date(),or_(ent.c.valid_to.is_(None),ent.c.valid_to>=governance_date())))]))


def data_options(c,tenant,actor):
    from market_data.policy_compatibility import data_options as build
    from .market_data_sources import catalogue
    return build(c,tenant,catalogue(c,tenant,actor)['sources'])


def compatibility(c,tenant,actor,payload):
    from market_data.policy_compatibility import check_configuration
    from .market_data_sources import catalogue
    sources=catalogue(c,tenant,actor)['sources']
    for rule in payload.rules+payload.default_rules:
        if rule.dataset_id and rule.dataset_id not in {s['datasetId'] for s in sources}:
            raise ValueError('Dataset is not available to this tenant')
        if rule.market_calendar_id:
            from market_data.calendar_store import visible_calendar
            if not visible_calendar(c,tenant,rule.market_calendar_id):
                raise ValueError('Calendar is not available to this tenant')
        if rule.market_data_series_id and not c.scalar(select(m.market_data_series.c.market_data_series_id).where(
            m.market_data_series.c.market_data_series_id==rule.market_data_series_id,
            _market_data_visible_node_clause(m.market_data_series.c.reference_node_id,tenant))):
            raise ValueError('Series is not available to this tenant')
        if rule.subject_reference_node_id and not c.scalar(select(m.financial_reference_node.c.reference_node_id).where(
            m.financial_reference_node.c.reference_node_id==rule.subject_reference_node_id,
            _market_data_visible_node_clause(rule.subject_reference_node_id,tenant))):
            raise ValueError('Subject is not available to this tenant')
    return check_configuration(c,tenant,payload,sources)

def preview(c,tenant,actor,payload):
    authority(c,tenant,actor)
    request=ResolutionRequest(tenant_id=tenant,subject_reference_node_id=payload.subject_reference_node_ids[0],
        valuation_policy_id=payload.valuation_policy_id,valuation_date=payload.valuation_date,valuation_cut_id=payload.valuation_cut_id,
        market_data_as_of_utc=payload.market_data_as_of_utc,use_purpose=payload.use_purpose,strategy_id=payload.strategy_id)
    items=[MarketDataResolutionSnapshotItemView.model_validate(asdict(item)) for item in
        resolve_market_data_batch(c,request,tuple(payload.subject_reference_node_ids))]
    from market_data.display_access import assert_dataset_display
    selected=[item for item in items if item.selected_value is not None]
    assert_dataset_display(c,tenant,{item.dataset_id for item in selected},
        series_contexts=[(item.dataset_id,item.market_data_series_id) for item in selected])
    return ResolutionPreview(status='COMPLETED' if all(i.status=='SELECTED' for i in items) else 'PARTIAL',items=items)

def _policy_view(definition):
    """Translate the business projection into the unchanged HTTP response."""
    return PolicyView(valuationPolicyId=definition.policy_id,policyCode=definition.policy_code,
        displayName=definition.display_name,valuationCutId=definition.valuation_cut_id,
        strategyId=definition.strategy_id,versionNo=definition.version_no,status=definition.status,
        validFrom=definition.valid_from,validTo=definition.valid_to,
        createdByUserAccountId=definition.created_by,createdAtUtc=definition.created_at,
        selectionMode=definition.selection_mode,rules=definition.rules,defaultRules=definition.default_rules)


def policy_view(c,tenant,policy_id):
    return _policy_view(pricing_policies.policy_definition(c,tenant,policy_id))


def create_policy(c,tenant,actor,payload,key):
    return _policy_view(pricing_policies.create_policy(c,tenant,actor,payload,key))
