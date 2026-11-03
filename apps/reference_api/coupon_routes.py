"""Full bond cashflow schedules and coupon receipts; never new interest income."""
from datetime import date
from uuid import UUID
from fastapi import Depends, Header, Query, Request
from .request_audit import AuditRouter as APIRouter
from sqlalchemy import select, func
from security_master_schema import models as m
from security_master_schema.strategy_access import require_strategy_action, strategy_predicate
from lifecycle import coupon_service as service
from lifecycle.coupon_contracts import ScheduleCreate, PaymentCreate, PaymentReverse
from valuation.economics import canonical_payload
from .reference_authority import require_reference_action
from .tenant_context import TenantContext, get_tenant_context
from .problem_details import ApiProblem


def coupon_router(connection_dependency, membership):
    router = APIRouter(prefix='/v1/lifecycle/coupons', tags=['Bond schedules and coupons'])

    def call(c, context, request, operation):
        actor = membership(c, context)
        operator = getattr(request.state, 'real_actor_id', actor)
        try:
            return canonical_payload(operation(actor, operator))
        except PermissionError as exc:
            raise ApiProblem(403, 'coupon.forbidden', 'Access denied', str(exc)) from exc
        except LookupError as exc:
            raise ApiProblem(404, 'coupon.not_found', 'Not found', str(exc)) from exc
        except ValueError as exc:
            raise ApiProblem(422, 'coupon.invalid', 'Bond schedule or coupon evidence rejected', str(exc)) from exc

    @router.get('/options', response_model=dict[str, object])
    def options(request: Request, strategyId: UUID | None = None,
                context: TenantContext = Depends(get_tenant_context), c=Depends(connection_dependency, scope='function')):
        def read(actor, operator):
            strategies = [dict(id=r.strategy_id, label=r.display_name) for r in c.execute(
                select(m.strategy.c.strategy_id, m.strategy.c.display_name).where(m.strategy.c.tenant_id == context.tenant_id,
                    strategy_predicate(c, context.tenant_id, actor, 'LIFECYCLE_READ', m.strategy.c.strategy_id))
                .order_by(m.strategy.c.display_name))]
            permissions = {}
            accounts = []
            bonds = []
            if strategyId:
                require_strategy_action(c, context.tenant_id, actor, 'LIFECYCLE_READ', strategyId)
                for action in ('LIFECYCLE_BOOK', 'TRADE_CORRECT'):
                    try:
                        require_strategy_action(c, context.tenant_id, actor, action, strategyId)
                        permissions[action] = True
                    except PermissionError:
                        permissions[action] = False
                accounts = [dict(id=r.cash_account_id, label=r.display_label or 'Unlabelled account') for r in c.execute(
                    select(m.cash_account.c.cash_account_id, m.cash_account.c.display_label).where(
                        m.cash_account.c.strategy_id == strategyId, m.cash_account.c.status == 'ACTIVE'))]
                from .product_booking import visible_clause
                subjects = select(func.coalesce(m.trade.c.reference_instrument_node_id, m.listing.c.instrument_node_id,
                    m.trade.c.trade_subject_reference_node_id)).select_from(m.trade.outerjoin(m.listing,
                        m.trade.c.trade_subject_reference_node_id == m.listing.c.listing_node_id)).where(m.trade.c.strategy_id == strategyId)
                bonds = [dict(id=r.reference_node_id, label=r.canonical_name) for r in c.execute(
                    select(m.financial_reference_node.c.reference_node_id, m.financial_reference_node.c.canonical_name)
                    .join(m.instrument, m.instrument.c.instrument_node_id == m.financial_reference_node.c.reference_node_id)
                    .join(m.instrument_type).where(m.instrument_type.c.type_code == 'BOND',
                        m.instrument.c.instrument_node_id.in_(subjects), m.financial_reference_node.c.status == 'ACTIVE',
                        visible_clause(m.financial_reference_node.c.reference_node_id, context.tenant_id))
                    .order_by(m.financial_reference_node.c.canonical_name).limit(100))]
            try:
                require_reference_action(c, context.tenant_id, actor, 'REFERENCE_APPROVE')
                permissions['REFERENCE_APPROVE'] = True
            except PermissionError:
                permissions['REFERENCE_APPROVE'] = False
            currencies = [dict(id=r.currency_id, label=r.currency_code) for r in c.execute(
                select(m.currency.c.currency_id, m.currency.c.currency_code).where(m.currency.c.status == 'ACTIVE').order_by(m.currency.c.currency_code))]
            return dict(strategies=strategies, permissions=permissions, currencies=currencies, accounts=accounts, bonds=bonds)
        return call(c, context, request, read)

    @router.get('/schedule', response_model=dict[str, object])
    def schedule(request: Request, strategyId: UUID, instrumentId: UUID, scheduleId: UUID | None = None,
                 context: TenantContext = Depends(get_tenant_context), c=Depends(connection_dependency, scope='function')):
        return call(c, context, request, lambda a, o: service.read_schedule(c, context.tenant_id, a, strategyId, instrumentId, scheduleId))

    @router.post('/schedules', status_code=201, response_model=dict[str, object])
    def save(payload: ScheduleCreate, request: Request, key: str = Header(alias='Idempotency-Key', min_length=1, max_length=255),
             context: TenantContext = Depends(get_tenant_context), c=Depends(connection_dependency, scope='function')):
        return call(c, context, request, lambda a, o: service.save_schedule(c, context.tenant_id, a, payload, key, operator=o))

    @router.get('/payments', response_model=dict[str, object])
    def payments(request: Request, strategyId: UUID, fromDate: date, toDate: date,
                 limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0, le=100000),
                 context: TenantContext = Depends(get_tenant_context), c=Depends(connection_dependency, scope='function')):
        def read(a, o):
            items, total = service.payment_report(c, context.tenant_id, a, strategyId, fromDate, toDate, limit, offset)
            return dict(items=items, total=total, scope='PAYMENT_CONFIRMATIONS_NOT_PNL')
        return call(c, context, request, read)

    def receipt(value):
        return dict(payment=value, effects=dict(additionalInterestPnl='0', cashBalanceUpdated=False,
                                               accrualInputsUpdated=False, tradeCreated=False))

    @router.post('/payments', status_code=201, response_model=dict[str, object])
    def confirm(payload: PaymentCreate, request: Request, key: str = Header(alias='Idempotency-Key', min_length=1, max_length=255),
                context: TenantContext = Depends(get_tenant_context), c=Depends(connection_dependency, scope='function')):
        return call(c, context, request, lambda a, o: receipt(service.record_payment(c, context.tenant_id, a, payload, key, operator=o)))

    @router.post('/payments/correct', status_code=201, response_model=dict[str, object])
    def correct(payload: PaymentCreate, request: Request, key: str = Header(alias='Idempotency-Key', min_length=1, max_length=255),
                context: TenantContext = Depends(get_tenant_context), c=Depends(connection_dependency, scope='function')):
        return call(c, context, request, lambda a, o: receipt(service.record_payment(c, context.tenant_id, a, payload, key, operator=o, correction=True)))

    @router.post('/payments/reverse', status_code=201, response_model=dict[str, object])
    def reverse(payload: PaymentReverse, request: Request, key: str = Header(alias='Idempotency-Key', min_length=1, max_length=255),
                context: TenantContext = Depends(get_tenant_context), c=Depends(connection_dependency, scope='function')):
        return call(c, context, request, lambda a, o: receipt(service.reverse_payment(c, context.tenant_id, a,
            payload.strategy_id, payload.payment_id, payload.reason, key, operator=o)))

    @router.get('/history', response_model=dict[str, object])
    def history(request: Request, strategyId: UUID, paymentId: UUID,
                context: TenantContext = Depends(get_tenant_context), c=Depends(connection_dependency, scope='function')):
        return call(c, context, request, lambda a, o: dict(items=service.payment_history(c, context.tenant_id, a, strategyId, paymentId)))

    return router
