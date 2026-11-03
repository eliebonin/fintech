"""Thin HTTP adapter for validated interest and maintained local bond balances."""
from datetime import date,datetime,timezone
from uuid import UUID
from fastapi import Depends,Header,Query
from sqlalchemy import select,or_,exists
from security_master_schema import models as m
from security_master_schema.tenant_workspace import TenantActionForbidden
from security_master_schema.reference_visibility import visible_clause
from valuation.balance_history_contracts import BalanceInputCreate,BalanceHistoryRefresh
from valuation import balance_history as service
from valuation.economics import canonical_payload
from .request_audit import AuditRouter as APIRouter
from .tenant_context import TenantContext,get_tenant_context
from .valuation_input_routes import input_authority
from .problem_details import ApiProblem


def balance_history_router(connection_dependency,membership):
    router=APIRouter(prefix='/v1/valuation',tags=['maintained accrued balances'])

    def actor(c,context,strategy,write=False):
        user=input_authority(c,context,membership,write)
        try:service.authorize(c,context.tenant_id,user,strategy,write)
        except (TenantActionForbidden,PermissionError,ValueError) as exc:raise ApiProblem(403,'valuation.forbidden','Access denied','Applicable strategy valuation authority required.') from exc
        return user

    def interval(start,end):
        if end<start or (end-start).days>366:raise ApiProblem(422,'valuation.invalid_input','Invalid dates','Choose an ordered interval of at most 366 days.')

    def decorate(c,rows):
        nodes={r['instrument_id'] for r in rows};currencies={r['currency_id'] for r in rows}
        names=dict(c.execute(select(m.financial_reference_node.c.reference_node_id,m.financial_reference_node.c.canonical_name).where(m.financial_reference_node.c.reference_node_id.in_(nodes))).all()) if nodes else {}
        codes=dict(c.execute(select(m.currency.c.currency_id,m.currency.c.currency_code).where(m.currency.c.currency_id.in_(currencies))).all()) if currencies else {}
        return canonical_payload([dict(row,instrument_name=names.get(row['instrument_id'],'Bond'),currency_code=codes.get(row['currency_id'])) for row in rows])

    @router.post('/balance-inputs',status_code=201,response_model=dict[str,object])
    def create(payload:BalanceInputCreate,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        user=actor(c,context,payload.strategy_id,True)
        try:return canonical_payload(service.record_balance_input(c,context.tenant_id,user,payload,key))
        except LookupError as exc:raise ApiProblem(404,'resource.not_found','Not found','Bond source unavailable.') from exc
        except ValueError as exc:raise ApiProblem(422,'valuation.invalid_input','Invalid assessed balance',str(exc)) from exc

    @router.get('/balance-inputs',response_model=dict[str,object])
    def inputs(strategy:UUID=Query(alias='strategyId'),start:date=Query(alias='fromDate'),end:date=Query(alias='toDate'),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        actor(c,context,strategy);interval(start,end)
        rows=service.read_inputs(c,context.tenant_id,strategy,start,end,datetime.now(timezone.utc))
        return {'items':decorate(c,rows)}

    @router.post('/balance-history-refresh',status_code=201,response_model=dict[str,object])
    def refresh(payload:BalanceHistoryRefresh,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        user=actor(c,context,payload.strategy_id,True)
        try:return canonical_payload(service.refresh_history(c,context.tenant_id,user,payload,key))
        except ValueError as exc:raise ApiProblem(422,'valuation.invalid_input','Balance history update failed',str(exc)) from exc

    @router.get('/balance-history',response_model=dict[str,object])
    def history(strategy:UUID=Query(alias='strategyId'),start:date=Query(alias='fromDate'),end:date=Query(alias='toDate'),
        limit:int=Query(default=25,ge=1,le=100),offset:int=Query(default=0,ge=0),
        instrument:UUID|None=Query(default=None,alias='instrumentId'),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        user=actor(c,context,strategy);interval(start,end)
        rows,total=service.list_history(c,context.tenant_id,user,strategy,start,end,datetime.now(timezone.utc),limit=limit,offset=offset,instrument_id=instrument,compact_sources=True)
        # Full source catalogs are retained once per build, not duplicated in
        # every displayed day. The exact build remains inspectable below.
        for row in rows:row['source_proof']={k:v for k,v in row['source_proof'].items() if k!='bondSources'}
        return {'items':decorate(c,rows),'total':total,'limit':limit,'offset':offset}

    @router.get('/balance-series',response_model=dict[str,object])
    def series(strategy:UUID=Query(alias='strategyId'),instrument:UUID=Query(alias='instrumentId'),
        start:date=Query(alias='fromDate'),end:date=Query(alias='toDate'),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        user=actor(c,context,strategy)
        if end<start:raise ApiProblem(422,'valuation.invalid_input','Invalid dates','From date must be on or before To date.')
        info=datetime.now(timezone.utc)
        # One instrument across the full read window; table pagination must not
        # truncate its chart. Maintenance retains its separate update budget.
        rows=service.list_history(c,context.tenant_id,user,strategy,start,end,info,
            instrument_id=instrument,compact_sources=True)
        return {'items':decorate(c,rows),'total':len(rows),'informationCutoff':info.isoformat()}

    @router.get('/balance-trades',response_model=dict[str,object])
    def trades(strategy:UUID=Query(alias='strategyId'),instrument:UUID=Query(alias='instrumentId'),
        start:date=Query(alias='fromDate'),end:date=Query(alias='toDate'),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        from valuation.balance_trade_events import trade_events
        user=actor(c,context,strategy);info=datetime.now(timezone.utc)
        try:items=trade_events(c,context.tenant_id,user,strategy,instrument,start,end,info)
        except TenantActionForbidden as exc:raise ApiProblem(403,'valuation.forbidden','Trade access denied','Applicable strategy trade-read authority required.') from exc
        except LookupError as exc:raise ApiProblem(404,'resource.not_found','Not found','Bond unavailable.') from exc
        except ValueError as exc:raise ApiProblem(422,'valuation.invalid_input','Trade markers unavailable',str(exc)) from exc
        return canonical_payload(dict(strategyId=strategy,instrumentId=instrument,fromDate=start,toDate=end,
            items=items,total=len(items),informationCutoff=info))

    @router.get('/balance-builds/{build_id}',response_model=dict[str,object])
    def build_detail(build_id:UUID,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        from valuation.balance_history_tables import history_build
        row=c.execute(select(history_build).where(history_build.c.build_id==build_id,history_build.c.tenant_id==context.tenant_id)).mappings().one_or_none()
        if not row:raise ApiProblem(404,'resource.not_found','Not found','Balance update unavailable.')
        actor(c,context,row['strategy_id'])
        return canonical_payload(dict(row))

    @router.get('/interest-options',response_model=dict[str,object])
    def options(strategy:UUID=Query(alias='strategyId'),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        user=actor(c,context,strategy);node=m.instrument
        from valuation import tables as vt
        from valuation.balance_history_tables import balance_input
        # The listing lookup crosses two enclosing SELECTs. Explicit correlation
        # prevents any listing trade from accidentally matching every bond.
        listed=exists(select(1).select_from(m.listing).where(m.listing.c.listing_node_id==m.trade.c.trade_subject_reference_node_id,
            m.listing.c.instrument_node_id==node.c.instrument_node_id).correlate(m.trade,node))
        traded=exists(select(1).select_from(m.trade).where(m.trade.c.strategy_id==strategy,or_(m.trade.c.trade_subject_reference_node_id==node.c.instrument_node_id,
            m.trade.c.reference_instrument_node_id==node.c.instrument_node_id,listed)).correlate(node))
        supplied=exists(select(1).select_from(vt.accrual_input).where(vt.accrual_input.c.tenant_id==context.tenant_id,vt.accrual_input.c.strategy_id==strategy,vt.accrual_input.c.instrument_id==node.c.instrument_node_id))
        anchored=exists(select(1).select_from(balance_input).where(balance_input.c.tenant_id==context.tenant_id,balance_input.c.strategy_id==strategy,balance_input.c.instrument_id==node.c.instrument_node_id))
        rows=c.execute(select(node.c.instrument_node_id,m.financial_reference_node.c.canonical_name,node.c.base_currency_id,m.currency.c.currency_code).join(m.instrument_type).join(m.financial_reference_node,
            m.financial_reference_node.c.reference_node_id==node.c.instrument_node_id).join(m.currency,node.c.base_currency_id==m.currency.c.currency_id).where(
            m.instrument_type.c.type_code=='BOND',visible_clause(node.c.instrument_node_id,context.tenant_id),or_(traded,supplied,anchored)).order_by(m.financial_reference_node.c.canonical_name)).mappings().all()
        writable=True
        try:service.authorize(c,context.tenant_id,user,strategy,True)
        except TenantActionForbidden:writable=False
        currencies=c.execute(select(m.currency.c.currency_id,m.currency.c.currency_code).where(m.currency.c.status=='ACTIVE').order_by(m.currency.c.currency_code)).all()
        return {'bonds':[dict(id=str(r['instrument_node_id']),label=r['canonical_name'],currencyId=str(r['base_currency_id']),currency=r['currency_code']) for r in rows],
            'currencies':[dict(id=str(identity),label=code) for identity,code in currencies],'canWrite':writable,
            'strategyLabel':c.scalar(select(m.strategy.c.display_name).where(m.strategy.c.strategy_id==strategy,m.strategy.c.tenant_id==context.tenant_id))}
    return router
