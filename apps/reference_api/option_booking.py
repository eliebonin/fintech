"""Authoritative listing-backed option booking, not position maintenance."""
from datetime import date,timezone
from decimal import Decimal
from hashlib import sha256
import json
from uuid import UUID,uuid4
from sqlalchemy import select,and_,or_,func,exists
from security_master_schema import models as m
from security_master_schema.option_booking import OptionBookingError,gross_option_premium,validate_option_execution
from security_master_schema.fx_forward_booking import decimal_text
from .contracts import OptionBookingListingView,OptionTradeEconomicsView,OptionBookingRequest
from .booking_controls import authorize_booking, lock_booking_strategy, find_booking_replay, record_booking_replay

ENDPOINT='/v1/trades/options'


def query(tenant_id):
    from .repository import _visible_node_clause
    node=m.financial_reference_node.alias('option_node')
    listing_node=m.financial_reference_node
    definition=m.instrument_definition_version
    ld=m.listing_definition_version
    currency=m.currency.alias('option_premium_currency')
    strike_currency=m.currency.alias('option_strike_currency')
    def visible(reference_id):
        scope=m.reference_node_scope.alias()
        return ~exists(select(1).select_from(scope).where(scope.c.reference_node_id==reference_id,~and_(scope.c.status=='ACTIVE',or_(scope.c.scope_type=='SHARED_CANONICAL',and_(scope.c.scope_type=='TENANT_PRIVATE',scope.c.owner_tenant_id==tenant_id)))))
    return select(m.listing.c.listing_node_id,m.listing.c.instrument_node_id,m.listing.c.market_venue_id,m.listing.c.status.label('listing_status'),listing_node.c.canonical_name.label('listing_name'),listing_node.c.status.label('listing_node_status'),listing_node.c.is_tradable.label('listing_tradable'),node.c.canonical_name.label('name'),node.c.status.label('node_status'),node.c.is_tradable,m.instrument.c.is_current,m.instrument.c.effective_from,m.instrument.c.effective_to,m.instrument.c.base_currency_id,m.instrument_type.c.status.label('type_status'),definition.c.instrument_definition_version_id,definition.c.effective_from.label('definition_from'),definition.c.effective_to.label('definition_to'),definition.c.base_currency_id.label('definition_currency'),ld.c.listing_definition_version_id,ld.c.effective_from.label('listing_from'),ld.c.effective_to.label('listing_to'),ld.c.quote_factor,ld.c.trading_currency_id,m.option_terms,m.instrument_dates.c.expiry_date,currency.c.currency_code.label('premium_currency'),currency.c.status.label('currency_status'),strike_currency.c.currency_code.label('strike_currency'),m.instrument_contract_unit_terms.c.unit_multiplier.label('deliverable_units'))\
        .select_from(m.listing.join(listing_node,listing_node.c.reference_node_id==m.listing.c.listing_node_id).join(m.instrument,m.instrument.c.instrument_node_id==m.listing.c.instrument_node_id).join(node,node.c.reference_node_id==m.instrument.c.instrument_node_id).join(m.instrument_type,m.instrument_type.c.instrument_type_id==m.instrument.c.instrument_type_id)
        .outerjoin(m.reference_node_scope,m.reference_node_scope.c.reference_node_id==listing_node.c.reference_node_id)
        .outerjoin(definition,and_(definition.c.instrument_node_id==m.instrument.c.instrument_node_id,definition.c.status=='APPROVED',definition.c.is_current,definition.c.instrument_type_id==m.instrument.c.instrument_type_id))
        .outerjoin(ld,and_(ld.c.listing_node_id==m.listing.c.listing_node_id,ld.c.status=='APPROVED',ld.c.is_current))
        .outerjoin(m.option_terms,and_(m.option_terms.c.instrument_node_id==m.instrument.c.instrument_node_id,m.option_terms.c.is_current))
        .outerjoin(m.instrument_dates,m.instrument_dates.c.instrument_node_id==m.instrument.c.instrument_node_id)
        .outerjoin(currency,currency.c.currency_id==m.option_terms.c.premium_currency_id).outerjoin(strike_currency,strike_currency.c.currency_id==m.option_terms.c.strike_currency_id)
        .outerjoin(m.instrument_contract_unit_terms,and_(m.instrument_contract_unit_terms.c.instrument_node_id==m.instrument.c.instrument_node_id,m.instrument_contract_unit_terms.c.valid_from<=date.today(),or_(m.instrument_contract_unit_terms.c.valid_to.is_(None),m.instrument_contract_unit_terms.c.valid_to>=date.today()))))\
        .where(m.instrument_type.c.type_code=='OPTION',visible(listing_node.c.reference_node_id),visible(node.c.reference_node_id),visible(m.option_terms.c.underlying_reference_node_id))\
        .add_columns(m.option_terms.c.effective_from.label('terms_from'),m.option_terms.c.effective_to.label('terms_to'))


def view(connection,tenant_id,row):
    from .repository import _visible_reference_node
    def text(value): return decimal_text(value) if value is not None else None
    # SQL option_terms contributes instrument_node_id twice; projection uses the
    # leading listing instrument key consistently.
    values=dict(listingId=row.listing_node_id,instrumentId=row.instrument_node_id,name=row.name,listingName=row.listing_name,optionType=row.option_type,underlyingId=row.underlying_reference_node_id,strike=text(row.strike_value),strikeCurrency=row.strike_currency,deliverableUnits=text(row.deliverable_units),expiryDate=str(row.expiry_date) if row.expiry_date else None,lastTradingAtUtc=row.last_trading_at_utc.astimezone(timezone.utc).isoformat() if row.last_trading_at_utc else None,exerciseStyle=row.exercise_style,settlementMethod=row.settlement_method,premiumCurrency=row.premium_currency,premiumMultiplier=text(row.premium_multiplier),quoteFactor=text(row.quote_factor),termsFingerprint=None,bookingEligible=False)
    try:
        from .option_onboarding import underlying_kind
        _visible_reference_node(connection,tenant_id,row.instrument_node_id)
        if not row.underlying_reference_node_id:
            raise ValueError('Approved underlying terms are required.')
        _visible_reference_node(connection,tenant_id,row.underlying_reference_node_id)
        kind=underlying_kind(connection,tenant_id,row.underlying_reference_node_id)
        if kind=='INDEX' and row.settlement_method!='CASH': raise ValueError('Index options must cash settle.')
        if row.terms_from>date.today() or (row.terms_to and row.terms_to<date.today()): raise ValueError('Option terms must be currently effective.')
        today=date.today()
        if not row.instrument_definition_version_id or not row.listing_definition_version_id: raise ValueError('Current approved instrument and listing definitions are required.')
        if any(start is None or start>today or (end and end<today) for start,end in [(row.definition_from,row.definition_to),(row.listing_from,row.listing_to),(row.effective_from,row.effective_to)]): raise ValueError('Definitions must be currently effective.')
        if not row.is_current or not row.is_tradable or not row.listing_tradable or any(state!='ACTIVE' for state in [row.node_status,row.listing_status,row.listing_node_status,row.type_status,row.currency_status,row.status]): raise ValueError('Option, listing and currencies must be active and tradable.')
        if row.strike_mode!='FIXED' or row.strike_basis!='ABSOLUTE' or row.exercise_style not in {'AMERICAN','EUROPEAN'} or row.settlement_method not in {'CASH','PHYSICAL'} or row.premium_style!='UPFRONT': raise ValueError('Only fixed-strike vanilla upfront-premium options are supported.')
        if not row.expiry_date or not row.last_trading_at_utc or row.last_trading_at_utc.astimezone(timezone.utc).date()>row.expiry_date or not row.deliverable_units or not row.strike_currency: raise ValueError('Complete explicit dates, deliverable and strike currency are required.')
        if row.premium_currency_id!=row.trading_currency_id or row.definition_currency!=row.base_currency_id or row.premium_currency_id!=row.base_currency_id: raise ValueError('Approved premium and listing currency must agree.')
        if row.settlement_method=='CASH' and row.settlement_currency_id!=row.premium_currency_id: raise ValueError('Cross-currency exercise settlement is deferred.')
        venue=connection.execute(select(m.market_venue.c.status).where(m.market_venue.c.market_venue_id==row.market_venue_id)).scalar_one_or_none()
        if venue!='ACTIVE': raise ValueError('Execution venue must be active.')
        strike_status=connection.scalar(select(m.currency.c.status).where(m.currency.c.currency_id==row.strike_currency_id))
        if strike_status!='ACTIVE': raise ValueError('Strike currency must be active.')
        units=m.instrument_contract_unit_terms
        count=connection.scalar(select(func.count()).select_from(units).where(units.c.instrument_node_id==row.instrument_node_id,units.c.valid_from<=today,or_(units.c.valid_to.is_(None),units.c.valid_to>=today)))
        if count!=1: raise ValueError('Exactly one effective contract-unit convention is required.')
        approved=connection.execute(select(m.listing_definition_version).where(m.listing_definition_version.c.listing_definition_version_id==row.listing_definition_version_id)).mappings().one()
        operational=connection.execute(select(m.listing).where(m.listing.c.listing_node_id==row.listing_node_id)).mappings().one()
        if any(approved[key]!=operational[key] for key in ('market_venue_id','trading_currency_id','quote_factor','unit_multiplier','effective_from','effective_to')): raise ValueError('Listing conventions differ from their approved definition.')
        if row.premium_multiplier is None or row.quote_factor is None or row.strike_value is None or row.strike_value <= 0:
            raise ValueError('Explicit positive premium conventions and strike are required.')
        gross_option_premium(1,Decimal(1),row.premium_multiplier,row.quote_factor)
        facts=values|{'optionTermsId':str(row.option_terms_id),'definitionId':str(row.instrument_definition_version_id),'listingDefinitionId':str(row.listing_definition_version_id),'venueId':str(row.market_venue_id)}
        values.update(bookingEligible=True,termsFingerprint=sha256(json.dumps(facts,sort_keys=True,default=str).encode()).hexdigest())
    except (ValueError,TypeError) as error: values['ineligibilityMessage']=str(error)
    except Exception as error:
        from .repository import RepositoryNotFound,InvalidWorkflowState
        if not isinstance(error,(RepositoryNotFound,InvalidWorkflowState)): raise
        values['ineligibilityMessage']='Active governed underlying terms are required.'
    return OptionBookingListingView(**values)


def load(connection,tenant_id,listing_id,lock=False):
    from .repository import RepositoryNotFound
    statement=query(tenant_id).where(m.listing.c.listing_node_id==listing_id)
    row=connection.execute(statement).mappings().first()
    if row is None: raise RepositoryNotFound('Visible option listing was not found.')
    if lock:
        # Stable lock ordering for shared references prevents retirements racing
        # the final eligibility check; historical replay remains before this.
        for reference_id in sorted({listing_id,row.instrument_node_id,row.underlying_reference_node_id},key=str):
            if reference_id is not None:
                connection.execute(select(m.financial_reference_node).where(m.financial_reference_node.c.reference_node_id==reference_id).with_for_update()).all()
                connection.execute(select(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id==reference_id).with_for_update()).all()
        for currency_id in sorted({row.premium_currency_id,row.strike_currency_id},key=str):
            connection.execute(select(m.currency).where(m.currency.c.currency_id==currency_id).with_for_update()).all()
        connection.execute(select(m.market_venue).where(m.market_venue.c.market_venue_id==row.market_venue_id).with_for_update()).all()
        connection.execute(select(m.instrument_type).where(m.instrument_type.c.type_code=='OPTION').with_for_update()).all()
        if row.underlying_reference_node_id:
            connection.execute(select(m.instrument).where(m.instrument.c.instrument_node_id==row.underlying_reference_node_id).with_for_update()).all()
            connection.execute(select(m.instrument_definition_version).where(m.instrument_definition_version.c.instrument_node_id==row.underlying_reference_node_id).with_for_update()).all()
            connection.execute(select(m.index_terms).where(m.index_terms.c.index_node_id==row.underlying_reference_node_id).with_for_update()).all()
        for table,key,value in [(m.listing,'listing_node_id',listing_id),(m.financial_reference_node,'reference_node_id',listing_id),(m.financial_reference_node,'reference_node_id',row.instrument_node_id),(m.instrument,'instrument_node_id',row.instrument_node_id),(m.option_terms,'instrument_node_id',row.instrument_node_id),(m.instrument_dates,'instrument_node_id',row.instrument_node_id),(m.instrument_definition_version,'instrument_node_id',row.instrument_node_id),(m.listing_definition_version,'listing_node_id',listing_id),(m.instrument_contract_unit_terms,'instrument_node_id',row.instrument_node_id)]:
            connection.execute(select(table).where(table.c[key]==value).with_for_update()).all()
        row=connection.execute(statement).mappings().first()
        if row is None: raise RepositoryNotFound('Visible option listing was not found.')
    return row,view(connection,tenant_id,row)


def search(connection,tenant_id,q,limit,offset):
    statement=query(tenant_id)
    if q.strip():
        escaped=q.strip().replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        statement=statement.where(or_(m.financial_reference_node.c.canonical_name.ilike(f'%{escaped}%',escape='\\'),m.financial_reference_node.c.internal_code.ilike(f'%{escaped}%',escape='\\')))
    total=connection.scalar(select(func.count()).select_from(statement.subquery()))
    rows=connection.execute(statement.order_by(m.financial_reference_node.c.canonical_name,m.listing.c.listing_node_id).limit(limit).offset(offset)).mappings()
    return [view(connection,tenant_id,row) for row in rows],total


def book(connection,tenant_id,actor,request,key,request_id):
    from .repository import _trade_booking_fingerprint,IdempotencyKeyConflict,RepositoryNotFound,get_booked_trade_detail,persist_trade_annotations
    from .trade_properties import validate_trade_annotations
    with connection.begin_nested():
        authorize_booking(connection, tenant_id, actor)
        normalized=request.model_copy(update={'quantity':request.quantity.normalize(),'execution_price':request.execution_price.normalize(),'trade_datetime':request.trade_datetime.astimezone(timezone.utc)})
        fingerprint=_trade_booking_fingerprint(normalized,connection,tenant_id)
        existing=find_booking_replay(connection,tenant_id,ENDPOINT,key,fingerprint)
        if existing:
            detail=get_booked_trade_detail(connection,tenant_id,existing,'v1',request_id)
            if detail is None: raise RepositoryNotFound('Booked trade does not exist')
            return detail
        row,terms=load(connection,tenant_id,request.listing_id,True)
        if not terms.booking_eligible: raise OptionBookingError('option.ineligible_listing','listingId',terms.ineligibility_message)
        if terms.terms_fingerprint!=request.expected_terms_fingerprint: raise OptionBookingError('option.terms_changed','listingId','Terms changed. Reselect the option listing.')
        execution=request.trade_datetime.astimezone(timezone.utc)
        validate_option_execution(execution,row.last_trading_at_utc,request.position_effect)
        if execution.date()<row.effective_from or execution.date()<row.listing_from: raise OptionBookingError('option.execution_before_effective','tradeDatetime','Execution is before the approved effective date.')
        if request.settlement_date<execution.date(): raise OptionBookingError('option.invalid_settlement_date','settlementDate','Premium settlement cannot precede execution.')
        lock_booking_strategy(connection, tenant_id, request.strategy_id)
        annotations=validate_trade_annotations(connection,tenant_id,request)
        gross=gross_option_premium(request.quantity,request.execution_price,row.premium_multiplier,row.quote_factor)
        trade_id=uuid4()
        connection.execute(m.trade.insert().values(trade_id=trade_id,trade_subject_reference_node_id=request.listing_id,reference_instrument_node_id=row.instrument_node_id,strategy_id=request.strategy_id,trade_type='INVESTMENT',position_effect=request.position_effect,execution_price=request.execution_price,price_basis='OPTION_PREMIUM',price_currency_id=row.premium_currency_id,quantity=request.quantity if request.side=='BUY' else -request.quantity,quantity_unit='CONTRACTS',trade_datetime_utc=execution,settlement_date=request.settlement_date,execution_venue_id=row.market_venue_id,booked_by_user_account_id=actor,created_by_user_account_id=actor,execution_channel='MANUAL_UI',lifecycle_status='BOOKED',trade_purpose=request.trade_purpose,market_activity=request.market_activity,trader_person_id=request.trader_person_id,comment=request.comment))
        persist_trade_annotations(connection,tenant_id,trade_id,request,annotations)
        economics=OptionTradeEconomicsView(terms=terms,grossPremium=decimal_text(gross),premiumDirection='PAY' if request.side=='BUY' else 'RECEIVE')
        connection.execute(m.trade_lifecycle_event.insert().values(trade_id=trade_id,sequence_no=1,event_type='BOOKED',event_datetime_utc=execution,source_event_id=key,payload_hash=fingerprint,event_payload=json.dumps({'schemaVersion':1,'kind':'OPTION_BOOKING','positionEffect':request.position_effect,'economics':economics.model_dump(mode='json',by_alias=True)},sort_keys=True),recorded_by_user_account_id=actor))
        record_booking_replay(connection,tenant_id,ENDPOINT,key,fingerprint,trade_id)
        return get_booked_trade_detail(connection,tenant_id,trade_id,'v1',request_id)


def load_economics(connection,trade_ids):
    if not trade_ids: return {}
    result={}
    for trade_id,raw in connection.execute(select(m.trade_lifecycle_event.c.trade_id,m.trade_lifecycle_event.c.event_payload).where(m.trade_lifecycle_event.c.trade_id.in_(trade_ids),m.trade_lifecycle_event.c.sequence_no==1,m.trade_lifecycle_event.c.event_type=='BOOKED')):
        payload=json.loads(raw) if raw else {}
        if payload.get('kind')=='OPTION_BOOKING' and payload.get('schemaVersion')==1: result[trade_id]=OptionTradeEconomicsView.model_validate(payload['economics'])
    return result


class OptionValuationUnsupported(ValueError):
    pass


def option_router(connection_dependency,assert_membership):
    from fastapi import APIRouter,Depends,Header,Query,HTTPException,Response
    from .tenant_context import TenantContext,get_tenant_context
    from .contracts import ApiMeta,OptionBookingListingSearchResponse,OptionBookingListingResponse,TradeDetailResponse,OptionProposalRequest,ReferenceDataProposalResponse
    from .problem_details import ApiProblem,ValidationIssue,current_request_id
    from .repository import RepositoryNotFound,IdempotencyKeyConflict,InvalidWorkflowState
    from .trade_properties import TradeFieldError
    from .option_onboarding import submit_option_proposal
    from security_master_schema.tenant_workspace import require_tenant_action,resolve_tenant_workspace,TenantActionForbidden
    router=APIRouter()
    def authorized(connection,context):
        actor=assert_membership(connection,context)
        try: require_tenant_action(resolve_tenant_workspace(connection,context.tenant_id,actor,date.today()),'TRADE_WRITE')
        except TenantActionForbidden as error: raise HTTPException(403,'Option booking is not permitted.') from error
        return actor
    def meta(context,**values): return ApiMeta(tenantContext=str(context.tenant_id),source='live-reference-api',apiVersion='v1',correlationId=current_request_id(),**values)
    @router.get('/v1/trades/option-listings',response_model=OptionBookingListingSearchResponse)
    def listing_search(q:str=Query(default='',max_length=250),limit:int=Query(default=25,ge=1,le=100),offset:int=Query(default=0,ge=0),context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency)):
        authorized(connection,context)
        items,total=search(connection,context.tenant_id,q,limit,offset)
        return OptionBookingListingSearchResponse(data=items,meta=meta(context,total=total,limit=limit,offset=offset))
    @router.get('/v1/trades/option-listings/{listing_id}',response_model=OptionBookingListingResponse)
    def listing_detail(listing_id:UUID,context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency)):
        authorized(connection,context)
        try: _,item=load(connection,context.tenant_id,listing_id)
        except RepositoryNotFound as error: raise HTTPException(404,str(error)) from error
        return OptionBookingListingResponse(data=item,meta=meta(context))
    @router.post(ENDPOINT,response_model=TradeDetailResponse,status_code=201)
    def booking(request:OptionBookingRequest,response:Response,idempotency_key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency)):
        actor=authorized(connection,context)
        try: result=book(connection,context.tenant_id,actor,request,idempotency_key,current_request_id())
        except RepositoryNotFound as error: raise HTTPException(404,str(error)) from error
        except IdempotencyKeyConflict as error: raise ApiProblem(409,'idempotency.key_reused','Idempotency conflict',str(error)) from error
        except (OptionBookingError,TradeFieldError) as error:
            code=getattr(error,'code','request.validation_failed')
            raise ApiProblem(409 if code=='option.terms_changed' else 422,code,'Option booking failed',str(error),errors=[ValidationIssue(location=['body',error.field],message=str(error),kind='value_error')]) from error
        response.headers['Location']=f'/v1/trades/{result.data.trade.trade_id}'
        return result
    @router.post('/v1/option-proposals',response_model=ReferenceDataProposalResponse,status_code=201)
    def propose(request:OptionProposalRequest,context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency)):
        actor=authorized(connection,context)
        try: data=submit_option_proposal(connection,context.tenant_id,actor,request)
        except RepositoryNotFound as error: raise HTTPException(404,str(error)) from error
        except InvalidWorkflowState as error: raise ApiProblem(422,'option.invalid_terms','Option proposal failed',str(error)) from error
        return ReferenceDataProposalResponse(data=data,meta=meta(context))
    return router
