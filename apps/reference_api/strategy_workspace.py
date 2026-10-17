"""Read-only strategy holdings and calendar inspection, not portfolio valuation."""
from datetime import datetime,time,timezone,date,timedelta
from uuid import UUID
from typing import Literal
from fastapi import Depends,Query
from .request_audit import AuditRouter as APIRouter
from sqlalchemy import select,or_,func
from security_master_schema import models as m
from security_master_schema.strategy_access import require_strategy_action
from positions.contracts import ProjectionRequest,PositionError
from positions.holdings import project_holdings
from positions.holdings_repository import load_holdings_facts
from positions.reconstruction import canonical,key_identity
from market_data.split_replay import load_reviewed_splits
from .tenant_context import TenantContext,get_tenant_context
from .problem_details import ApiProblem


def snapshot(c,tenant,strategy,day,basis,information):
    now=c.scalar(select(func.clock_timestamp()))
    information=information or now
    if information.tzinfo is None or information.utcoffset() is None or information>now:
        raise ValueError('Information cutoff must be a past or current timestamp with timezone')
    information=information.astimezone(timezone.utc)
    request=ProjectionRequest(tenant,strategy,datetime.combine(day,time.max,timezone.utc),information)
    facts,descriptions=load_holdings_facts(c,request)
    subjects={f.booking.subject_id for f in facts if f.booking}
    splits=load_reviewed_splits(c,subjects,information,tenant_id=tenant)
    projection=project_holdings(facts,request,basis=basis,splits=splits)
    # Reuse unit/identity safety only. No financial calculation or marks are read.
    from valuation.corporate_actions import assert_projection_actions
    assert_projection_actions(c,projection,PositionError,reviewed_events=splits)
    return projection,descriptions,information


def position_rows(projection,descriptions):
    result=[]
    for bucket in projection.buckets:
        key=bucket.key; desc=descriptions[bucket.trade_ids[0]]; quantity=bucket.closing_quantity
        # Display the booked product classification, not an inference from units
        # (a bond and a swap can both be booked in NOMINAL or UNITS).
        instrument_type={'OPTION_BOOKING':'OPTION','ETF':'ETP'}.get(key.product_basis,key.product_basis)
        labels={'EQUITY':'Equities','BOND':'Bonds','ETP':'Exchange-traded products','FUND':'Funds',
            'FUTURE':'Futures','OPTION':'Options','SWAP':'Swaps','FX_FORWARD':'FX forwards',
            'STRUCTURED_PRODUCT':'Structured products'}
        label=labels.get(instrument_type,'Other instruments')
        # Alerts explain dated retained terms against this view's UTC date.
        # They are not settlement evidence, a notification queue or an unwind.
        dated_types={'BOND','FX_FORWARD','FUTURE','OPTION','SWAP','STRUCTURED_PRODUCT'}
        evidence={(descriptions[t].get('contractDate'),descriptions[t].get('contractDateLabel')) for t in bucket.trade_ids}
        known={item for item in evidence if item[0]}
        contract_date,date_label=next(iter(known)) if len(known)==1 else (None,None)
        attention,message=None,None
        if quantity!=0:
            if len(known)>1:
                attention,message='CONTRACT_DATE_CONFLICT','Conflicting booked contract dates — review terms'
            elif len(known)!=len(evidence) or not known:
                if instrument_type in dated_types or known:
                    contract_date,date_label=None,None
                    attention,message='CONTRACT_DATE_MISSING','Contract date not recorded in all booking evidence'
            if contract_date and attention is None:
                day=date.fromisoformat(contract_date);as_of=projection.request.closing_cutoff.date()
                if day<as_of:
                    attention,message='PAST_CONTRACT_DATE',f'Past {date_label.lower()} — position still open'
                elif day==as_of:
                    attention='CONTRACT_DATE_TODAY'
                    message={'Maturity':'Matures today','Expiry':'Expires today','Last trading':'Last trading today'}[date_label]
        result.append(dict(positionId=key_identity(key),subjectId=str(key.subject_id),instrumentId=desc['instrumentId'],
            instrumentType=instrument_type,instrumentTypeLabel=label,
            contractDate=contract_date,contractDateLabel=date_label,attentionCode=attention,attentionMessage=message,
            name=desc['name'],currency=desc['currency'],quantity=canonical(quantity),quantityUnit=key.quantity_unit,
            direction='LONG' if quantity>0 else 'SHORT' if quantity<0 else 'FLAT',tradeCount=len(bucket.trade_ids),
            unitMultiplier=str(key.unit_multiplier),quoteFactor=str(key.quote_factor)))
    # Group and alphabetize the complete filtered result before route pagination.
    return sorted(result,key=lambda row:(row['instrumentTypeLabel'].casefold(),row['name'].casefold(),row['subjectId'],row['positionId']))


def measure_position_rows(c,request,projection,descriptions):
    """Flat base quantity alone does not prove a forward's two legs closed."""
    from valuation.forward_measures import contractual_legs,load_contract_bookings
    buckets={key_identity(b.key):b for b in projection.buckets}
    population=load_contract_bookings(c,request,[b for b in projection.buckets
        if b.key.product_basis=='FX_FORWARD' and b.closing_quantity==0])
    rows=[]
    for row in position_rows(projection,descriptions):
        if row['direction']!='FLAT':rows.append(row)
        elif row['direction']=='FLAT' and row['instrumentType']=='FX_FORWARD':
            try:
                legs=contractual_legs(c,request,buckets[row['positionId']],population=population)
                if legs['baseAmount'] or legs['quoteAmount']:rows.append(row)
            except (ValueError,KeyError,TypeError,ArithmeticError):
                rows.append(row|dict(attentionCode='CONTRACT_EVIDENCE_CONFLICT',
                    attentionMessage='Flat base amount does not establish closure of both forward obligations'))
    return rows


def movement_rows(projection,descriptions,identity):
    bucket=next((b for b in projection.buckets if key_identity(b.key)==identity),None)
    if bucket is None:raise LookupError('Position not found at these cutoffs')
    items=[]
    for movement in projection.executions:
        if movement.key!=bucket.key:continue
        booking=movement.booking;desc=descriptions[booking.trade_id]
        items.append(dict(movementId=str(movement.event_id),tradeId=str(booking.trade_id),kind=desc['tradeType'],
            effectiveAt=movement.effective_at,quantity=canonical(booking.quantity),executionPrice=desc['executionPrice'],
            executionDate=desc['executionDate'],settlementDate=desc['settlementDate'],source='BOOKED_TRADE'))
    for adjustment in projection.split_adjustments:
        if adjustment.key!=bucket.key:continue
        items.append(dict(movementId=str(adjustment.event.action_id),tradeId=None,kind='SHARE_RATIO',
            effectiveAt=adjustment.event.effective_at,quantity=canonical(adjustment.quantity_after-adjustment.quantity_before),
            executionPrice=None,source='REVIEWED_CORPORATE_ACTION',ratio=str(adjustment.event.ratio)))
    items.sort(key=lambda r:(r['effectiveAt'],r['movementId']))
    from decimal import Decimal,localcontext
    with localcontext() as context:
        context.prec=512
        running=Decimal(0)
        for item in items:
            running+=Decimal(item['quantity']);item['runningQuantity']=canonical(running)
    if running!=bucket.closing_quantity:raise PositionError('Movement history does not reconcile with position')
    return items,bucket.closing_quantity


def calendar_register(c,tenant,strategy,day):
    from .calendar_service import calendar_view,assignment_view
    from market_data.calendar_store import visible_calendar,calendar_days
    from market_data.calendar_decisions import decision_for_target
    assignments=[];indirect=[];decisions={};now=c.scalar(select(func.clock_timestamp()))
    def detail(calendar_id):
        row=visible_calendar(c,tenant,calendar_id)
        if not row:raise ValueError('Assigned calendar is not currently available')
        value=calendar_view(c,tenant,calendar_id,False).model_dump(mode='json')
        definition=row['definition_json'] or {}
        value['configuration']=definition.get('configuration')
        value['sourceEvidence']={key:val for key,val in definition.items() if key not in {'configuration','days'}}
        value['components']=[]
        for component_id in (value['configuration'] or {}).get('baseCalendarIds',[]):
            component=visible_calendar(c,tenant,UUID(str(component_id)))
            if component:value['components'].append(dict(calendarId=str(component['market_calendar_id']),displayName=component['display_name']))
        return value
    for row in c.execute(select(m.calendar_assignment).where(m.calendar_assignment.c.tenant_id==tenant,
        m.calendar_assignment.c.target_kind=='STRATEGY',m.calendar_assignment.c.target_id==strategy)
        .order_by(m.calendar_assignment.c.valid_from.desc(),m.calendar_assignment.c.created_at_utc.desc(),m.calendar_assignment.c.calendar_assignment_id.desc())).mappings():
        calendar=detail(row['market_calendar_id'])
        if row['purpose'] not in decisions:
            decisions[row['purpose']]=decision_for_target(c,tenant,'STRATEGY',strategy,row['purpose'],day,now)
        decision=decisions[row['purpose']]
        within=row['valid_from']<=day<=row['valid_to']
        active=bool(decision and decision['assignmentId']==str(row['calendar_assignment_id']))
        calendar_row=visible_calendar(c,tenant,row['market_calendar_id'])
        days=calendar_days(c,calendar_row,day,day+timedelta(days=30))
        assignments.append(dict(assignment=assignment_view(row).model_dump(mode='json'),calendar=calendar,activeOnDate=active,superseded=within and not active,
            statusOnDate=days[0]['status'],days=[d for d in days if d['status']!='OPEN']))
    policies=c.execute(select(m.valuation_policy).where(m.valuation_policy.c.tenant_id==tenant,m.valuation_policy.c.status=='ACTIVE',
        m.valuation_policy.c.valid_from<=day,or_(m.valuation_policy.c.valid_to.is_(None),m.valuation_policy.c.valid_to>=day),
        or_(m.valuation_policy.c.strategy_id.is_(None),m.valuation_policy.c.strategy_id==strategy))).mappings().all()
    seen=set()
    def add(calendar_id,origin,label):
        if not calendar_id or (calendar_id,origin,label) in seen:return
        seen.add((calendar_id,origin,label)); row=visible_calendar(c,tenant,calendar_id)
        if not row:return
        days=calendar_days(c,row,day,day)
        indirect.append(dict(calendar=detail(calendar_id),origin=origin,
            context=label,statusOnDate=days[0]['status']))
    for policy in policies:
        label=f"{policy['policy_code']} v{policy['version_no']} (available policy, not selected)"
        cut=c.execute(select(m.valuation_cut).where(m.valuation_cut.c.valuation_cut_id==policy['valuation_cut_id'])).mappings().one()
        add(cut['market_calendar_id'],'POLICY_CUT',label)
        for rule in c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_id==policy['valuation_policy_id'],m.valuation_policy_rule.c.status=='ACTIVE')).mappings():
            add(rule['market_calendar_id'],'POLICY_RULE',label+f" / rule {rule['rule_sequence']}")
            if rule['pricing_cut_id']:
                cut=c.execute(select(m.valuation_cut).where(m.valuation_cut.c.valuation_cut_id==rule['pricing_cut_id'])).mappings().one()
                add(cut['market_calendar_id'],'RULE_PRICING_CUT',label+f" / rule {rule['rule_sequence']}")
    # Venue-use information is trade-scoped, even when the calendar itself is a
    # shared reference. Calendar-only users do not learn the strategy's bookings.
    actor=c.info.get('request_actor')
    if actor:
        try:require_strategy_action(c,tenant,actor,'TRADE_READ',strategy)
        except PermissionError:pass
        else:
            for calendar_id,label in c.execute(select(m.market_venue.c.market_calendar_id,m.market_venue.c.display_name)
                .join(m.trade,m.trade.c.execution_venue_id==m.market_venue.c.market_venue_id)
                .where(m.trade.c.strategy_id==strategy,m.trade.c.trade_datetime_utc<=datetime.combine(day,time.max,timezone.utc)).distinct()):
                add(calendar_id,'BOOKED_VENUE',label+' (booked venue history, not a direct assignment)')
    return dict(asOf=day,assignments=assignments,indirectCalendars=indirect)


def strategy_workspace_router(connection_dependency,membership):
    router=APIRouter(prefix='/v1/strategies',tags=['strategy workspace'])
    def guard(c,context,strategy,action):
        actor=membership(c,context)
        require_strategy_action(c,context.tenant_id,actor,'STRATEGY_READ',strategy)
        require_strategy_action(c,context.tenant_id,actor,action,strategy)
    def run(c,context,strategy,action,operation):
        try:
            guard(c,context,strategy,action);return canonical(operation())
        except PermissionError as exc:raise ApiProblem(403,'strategy.forbidden','Strategy access required',str(exc)) from exc
        except LookupError as exc:raise ApiProblem(404,'strategy.position_not_found','Position not found',str(exc)) from exc
        except (ValueError,PositionError) as exc:raise ApiProblem(422,'strategy.reconstruction_blocked','Holdings unavailable',str(exc)) from exc
    @router.get('/{strategy_id}/positions')
    def positions(strategy_id:UUID,asOf:date,basis:Literal['EXECUTED','VALUATION_RECOGNISED']='EXECUTED',
        informationCutoff:datetime|None=None,includeClosed:bool=False,q:str=Query('',max_length=100),
        limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        def operation():
            projection,descriptions,information=snapshot(c,context.tenant_id,strategy_id,asOf,basis,informationCutoff)
            rows=[row for row in position_rows(projection,descriptions) if (includeClosed or row['direction']!='FLAT') and (not q or q.casefold() in (row['name']+' '+row['subjectId']).casefold())]
            return dict(asOf=asOf,basis=basis,informationCutoff=information,total=len(rows),items=rows[offset:offset+limit],limit=limit,offset=offset)
        return run(c,context,strategy_id,'TRADE_READ',operation)
    @router.get('/{strategy_id}/positions/{position_id}/movements')
    def movements(strategy_id:UUID,position_id:str,asOf:date,basis:Literal['EXECUTED','VALUATION_RECOGNISED']='EXECUTED',
        informationCutoff:datetime|None=None,limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        def operation():
            projection,descriptions,information=snapshot(c,context.tenant_id,strategy_id,asOf,basis,informationCutoff)
            items,closing=movement_rows(projection,descriptions,position_id)
            from positions.chart import movement_chart
            bucket=next(b for b in projection.buckets if key_identity(b.key)==position_id)
            chart=dict(quantityUnit=bucket.key.quantity_unit,through=projection.request.closing_cutoff,points=movement_chart(items))
            return dict(asOf=asOf,basis=basis,informationCutoff=information,total=len(items),closingQuantity=canonical(closing),items=items[offset:offset+limit],chart=chart,limit=limit,offset=offset)
        return run(c,context,strategy_id,'TRADE_READ',operation)
    @router.get('/{strategy_id}/measures')
    def measures(strategy_id:UUID,asOf:date,policyId:UUID,basis:Literal['EXECUTED','VALUATION_RECOGNISED']='EXECUTED',
        informationCutoff:datetime|None=None,limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        def operation():
            from security_master_schema.tenant_workspace import resolve_tenant_workspace,require_tenant_action
            from .resource_limits import governance_date
            from valuation.service import ValuationRequest
            from valuation.measure_inputs import preview_measures
            actor=membership(c,context)
            for action in ('VALUATION_READ','VALUATION_RUN'):
                require_strategy_action(c,context.tenant_id,actor,action,strategy_id)
            require_tenant_action(resolve_tenant_workspace(c,context.tenant_id,actor,governance_date()),'MARKET_DATA_READ')
            policy=c.execute(select(m.valuation_policy).where(m.valuation_policy.c.valuation_policy_id==policyId,
                m.valuation_policy.c.tenant_id==context.tenant_id,m.valuation_policy.c.status=='ACTIVE',
                m.valuation_policy.c.valid_from<=asOf,or_(m.valuation_policy.c.valid_to.is_(None),m.valuation_policy.c.valid_to>=asOf),
                or_(m.valuation_policy.c.strategy_id.is_(None),m.valuation_policy.c.strategy_id==strategy_id))).mappings().one_or_none()
            if not policy:raise ValueError('An active tenant policy valid for this strategy and date is required')
            strategy=c.execute(select(m.strategy).where(m.strategy.c.strategy_id==strategy_id,m.strategy.c.tenant_id==context.tenant_id)).mappings().one()
            currency=strategy['base_currency_id']
            if not currency:raise ValueError('Strategy base currency is required for monetary measures')
            projection,descriptions,information=snapshot(c,context.tenant_id,strategy_id,asOf,basis,informationCutoff)
            closing=datetime.combine(asOf,time.max,timezone.utc)
            request=ValuationRequest(context.tenant_id,strategy_id,policyId,policy['valuation_cut_id'],currency,
                closing-timedelta(days=1),closing,information)
            from market_data.read_scope import resolution_read_scope
            with resolution_read_scope(c,tenant=context.tenant_id,actor=actor,strategy=strategy_id,
                    policy=policyId,information_cutoff=information,economic_date=asOf):
                rows=measure_position_rows(c,request,projection,descriptions)
                result=preview_measures(c,request,projection,descriptions,rows[offset:offset+limit])
            c.info['preview_release']=(context.tenant_id,actor,strategy_id,result)
            return result|dict(total=len(rows),limit=limit,offset=offset,basis=basis)
        return run(c,context,strategy_id,'TRADE_READ',operation)
    @router.get('/{strategy_id}/calendars')
    def calendars(strategy_id:UUID,asOf:date,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,context,strategy_id,'CALENDAR_READ',lambda:calendar_register(c,context.tenant_id,strategy_id,asOf))
    return router
