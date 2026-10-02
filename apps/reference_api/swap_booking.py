"""Read-only authoritative terms for the OTC autocall-reference swap slice."""
from sqlalchemy import select
from security_master_schema import models as m
from .product_booking_contracts import SwapDetailsView


def load_swap_context(connection, tenant_id, instrument_id, as_of, *, lock=False):
    """Return immutable source details; shared booking code supplies convention/identity."""
    from .product_booking import require_visible, instrument_row

    generic = select(m.swap_definition_version.c.instrument_definition_version_id).join(
        m.instrument_definition_version, m.instrument_definition_version.c.instrument_definition_version_id ==
        m.swap_definition_version.c.instrument_definition_version_id).where(
        m.instrument_definition_version.c.instrument_node_id == instrument_id,
        m.instrument_definition_version.c.is_current, m.instrument_definition_version.c.status == 'APPROVED')
    if connection.scalar(generic):
        from .generic_swap_booking import load_generic_swap_context
        return load_generic_swap_context(connection, tenant_id, instrument_id, as_of, lock=lock)

    def rows(table, predicate):
        statement=select(table).where(predicate).order_by(*table.primary_key.columns)
        return [dict(row) for row in connection.execute(statement.with_for_update() if lock else statement).mappings()]

    def visible(node_id):
        if lock:
            for table in (m.financial_reference_node,m.reference_node_scope):
                rows(table,table.c.reference_node_id==node_id)
        return require_visible(connection,tenant_id,node_id)

    terms=rows(m.swap_terms,m.swap_terms.c.instrument_node_id==instrument_id)
    legs=rows(m.swap_leg,m.swap_leg.c.swap_instrument_node_id==instrument_id)
    if len(terms)!=1 or terms[0]['swap_type']!='TOTAL_RETURN' or len(legs)!=2 or {leg['leg_role'] for leg in legs}!={'PERFORMANCE','FUNDING'}:
        raise ValueError('Only a two-leg autocall-reference total-return swap is supported.')
    performance=next(leg for leg in legs if leg['leg_role']=='PERFORMANCE')
    funding=next(leg for leg in legs if leg['leg_role']=='FUNDING')
    base=connection.scalar(select(m.instrument.c.base_currency_id).where(m.instrument.c.instrument_node_id==instrument_id))
    if any(leg['currency_id']!=base or not leg['schedule_id'] for leg in legs) or performance['pay_receive']==funding['pay_receive'] or funding['spread'] is None:
        raise ValueError('Explicit matching leg currencies, opposing directions, schedules and funding spread are required.')
    ref=visible(performance['reference_node_id']);rate=visible(funding['reference_node_id'])
    if connection.scalar(select(m.reference_node_type.c.type_code).where(m.reference_node_type.c.reference_node_type_id==rate.reference_node_type_id))!='RATE_INDEX':
        raise ValueError('The funding reference must be an active rate index.')
    if lock:
        rows(m.instrument,m.instrument.c.instrument_node_id==ref.reference_node_id)
    _,underlying=instrument_row(connection,tenant_id,ref.reference_node_id)
    if not underlying.is_current or underlying.type_status!='ACTIVE':
        raise ValueError('A current active underlying instrument is required.')
    definitions=rows(m.instrument_definition_version,(m.instrument_definition_version.c.instrument_node_id==ref.reference_node_id)&m.instrument_definition_version.c.is_current&(m.instrument_definition_version.c.status=='APPROVED'))
    if underlying.type_code!='STRUCTURED_PRODUCT' or len(definitions)!=1:
        raise ValueError('An approved structured-product autocall reference is required.')
    definition=definitions[0]
    if any(definition[key]!=underlying[key] for key in ('base_currency_id','instrument_type_id','effective_from','effective_to','issuer_organisation_id')) or definition['effective_from']>as_of or (definition['effective_to'] and definition['effective_to']<as_of):
        raise ValueError('Underlying differs from its effective approved definition.')
    dates=rows(m.instrument_dates,m.instrument_dates.c.instrument_node_id==instrument_id)
    if len(dates)!=1 or not dates[0]['effective_date'] or not dates[0]['maturity_date'] or not dates[0]['effective_date']<=as_of<dates[0]['maturity_date']:
        raise ValueError('Execution must be within explicit swap effective and maturity dates.')
    profiles=rows(m.return_profile,m.return_profile.c.return_profile_id==performance['return_profile_id'])
    if len(profiles)!=1 or profiles[0]['status']!='ACTIVE' or profiles[0]['base_return_basis']!='TOTAL' or profiles[0]['requires_financing_reference']:
        raise ValueError('An explicit active supported total-return profile is required.')
    graph=rows(m.structured_product_terms,(m.structured_product_terms.c.instrument_node_id==ref.reference_node_id)&m.structured_product_terms.c.is_current)
    if len(graph)!=1 or graph[0]['status'] not in {'ACTIVE','VALIDATED'} or graph[0]['effective_from']>as_of or (graph[0]['effective_to'] and graph[0]['effective_to']<as_of):
        raise ValueError('An effective validated autocall payoff definition is required.')
    facts=dict(swapTerms=terms,legs=legs,dates=dates,returnProfiles=profiles,underlyingDefinitions=definitions,
        underlyingDates=rows(m.instrument_dates,m.instrument_dates.c.instrument_node_id==ref.reference_node_id),structuredTerms=graph)
    terms_id=graph[0]['structured_product_terms_id']
    for table in (m.structured_product_initial_fixing,m.structured_product_condition_group,m.structured_product_coupon_programme,
                  m.structured_product_range_accrual_terms,m.structured_product_supertracker_terms):
        facts[table.name]=rows(table,table.c.structured_product_terms_id==terms_id)
    composition=rows(m.instrument_composition,m.instrument_composition.c.parent_instrument_node_id==ref.reference_node_id)
    facts['composition']=composition
    ids=[item['instrument_composition_id'] for item in composition]
    facts['componentTerms']=rows(m.structured_product_component_terms,m.structured_product_component_terms.c.instrument_composition_id.in_(ids))
    groups=facts['structured_product_condition_group'];group_ids=[item['condition_group_id'] for item in groups]
    facts['barriers']=rows(m.barrier_rule,m.barrier_rule.c.condition_group_id.in_(group_ids))
    facts['actions']=rows(m.condition_group_action,m.condition_group_action.c.condition_group_id.in_(group_ids))
    active_groups={item['condition_group_id'] for item in groups if item['status'] in {'ACTIVE','VALIDATED'}}
    if not any(item['action_type']=='REDEEM_PARENT' and item['payment_timing']=='ON_AUTOCALL'
               and item['status'] in {'ACTIVE','VALIDATED'} and item['condition_group_id'] in active_groups
               and item['target_scope']=='PARENT' and item['target_reference_node_id']==ref.reference_node_id
               for item in facts['actions']):
        raise ValueError('The referenced payoff must contain an explicit autocall redemption action.')
    programmes=facts['structured_product_coupon_programme']
    facts['couponPeriods']=rows(m.structured_product_coupon_period,m.structured_product_coupon_period.c.coupon_programme_id.in_([p['coupon_programme_id'] for p in programmes]))
    schedules={leg['schedule_id'] for leg in legs}
    schedules.update(connection.scalars(select(m.schedule.c.schedule_id).where(m.schedule.c.owner_reference_node_id.in_([instrument_id,ref.reference_node_id]))))
    for entries in facts.values():
        for item in entries:
            schedules.update(value for key,value in item.items() if key in {'schedule_id','payment_schedule_id','observation_schedule_id'} and value)
    event_ids={value for entries in facts.values() for item in entries for key,value in item.items()
               if key in {'schedule_event_id','observation_event_id'} and value}
    schedules.update(connection.scalars(select(m.schedule_event.c.schedule_id).where(m.schedule_event.c.schedule_event_id.in_(event_ids))))
    facts['schedules']=rows(m.schedule,m.schedule.c.schedule_id.in_(sorted(schedules,key=str)))
    if any(item['status']!='ACTIVE' or item['owner_reference_node_id'] not in {instrument_id,ref.reference_node_id,*[c['component_reference_node_id'] for c in composition]} for item in facts['schedules']):
        raise ValueError('Active schedules owned by the swap/payoff are required.')
    facts['scheduleEvents']=rows(m.schedule_event,m.schedule_event.c.schedule_id.in_(sorted(schedules,key=str)))
    if any(not any(event['schedule_id']==leg['schedule_id'] and event['status'] in {'SCHEDULED','CONFIRMED'} for event in facts['scheduleEvents']) for leg in legs):
        raise ValueError('Each swap leg requires explicit scheduled events.')
    # Source facts contain reference IDs, not raw source payloads. Validate every
    # referenced economic node before exposing even the typed display fields.
    references={ref.reference_node_id,rate.reference_node_id}
    for entries in facts.values():
        for item in entries:
            references.update(value for key,value in item.items() if value and key in {
                'component_reference_node_id','underlying_reference_node_id','target_reference_node_id','owner_reference_node_id'})
    facts['referenceNodes']=[dict(visible(node_id)) for node_id in sorted(references,key=str)]
    return SwapDetailsView(performanceReferenceId=ref.reference_node_id,performanceReferenceName=ref.canonical_name,
        performanceDirection=performance['pay_receive'],returnProfileCode=profiles[0]['profile_code'],
        fundingReferenceId=rate.reference_node_id,fundingReferenceName=rate.canonical_name,fundingDirection=funding['pay_receive'],
        fundingSpread=funding['spread'],effectiveDate=dates[0]['effective_date'],sourceFacts=facts),dates[0]['maturity_date']
