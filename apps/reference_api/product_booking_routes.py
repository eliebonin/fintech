from datetime import date
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Header, Query, HTTPException, Response
from security_master_schema.tenant_workspace import resolve_tenant_workspace, require_tenant_action, TenantActionForbidden
from .tenant_context import TenantContext, get_tenant_context
from .problem_details import ApiProblem, ValidationIssue, current_request_id
from .contracts import TradeDetailResponse, ReferenceDataProposalResponse
from .product_booking_contracts import (ProductBookingRequest, ProductBookingContextResponse,
    ProductBookingSearchResponse, ConventionProposalRequest, FutureProposalRequest, FutureFamilyProposalRequest, FutureFamilySearchResponse)
from . import product_booking as service
from .repository import RepositoryNotFound, IdempotencyKeyConflict, InvalidWorkflowState
from .trade_properties import TradeFieldError
from .swap_creation_contracts import SwapProposalRequest


def product_booking_router(connection_dependency, membership):
    router = APIRouter()

    def authorized(connection, context):
        actor = membership(connection, context)
        try: require_tenant_action(resolve_tenant_workspace(connection, context.tenant_id, actor, date.today()), 'TRADE_WRITE')
        except TenantActionForbidden as error: raise HTTPException(403, 'Trade writing is not permitted.') from error
        return actor

    def meta(context, **pagination):
        return dict(tenantContext=str(context.tenant_id), source='live-reference-api', apiVersion='v1',
                    correlationId=current_request_id(), **pagination)

    @router.get('/v1/trades/product-instruments', response_model=ProductBookingSearchResponse)
    def search(kind: Literal['STRUCTURED_PRODUCT', 'FUTURE', 'BOND', 'SWAP'], route: Literal['LISTED', 'OTC'],
               q: str = Query(default='', max_length=250), limit: int = Query(default=20, ge=1, le=100),
               offset: int = Query(default=0, ge=0), as_of: date = Query(default=None, alias='asOfDate'),
               context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency)):
        authorized(connection, context)
        items, total = service.search(connection, context.tenant_id, kind, route, q, limit, offset, as_of or date.today())
        return ProductBookingSearchResponse(data=items, meta=meta(context, total=total, limit=limit, offset=offset))

    @router.get('/v1/trades/product-instruments/{instrument_id}', response_model=ProductBookingContextResponse)
    def detail(instrument_id: UUID, listing_id: UUID | None = Query(default=None, alias='listingId'),
               as_of: date | None = Query(default=None, alias='asOfDate'),
               context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency)):
        authorized(connection, context)
        try: item = service.load_context(connection, context.tenant_id, instrument_id, listing_id, as_of)
        except RepositoryNotFound as error: raise HTTPException(404, str(error)) from error
        return ProductBookingContextResponse(data=item, meta=meta(context))

    def booking(request, response, key, context, connection, kind):
        actor = authorized(connection, context)
        try: result = service.book(connection, context.tenant_id, actor, request, key, kind, current_request_id())
        except RepositoryNotFound as error: raise HTTPException(404, str(error)) from error
        except IdempotencyKeyConflict as error: raise ApiProblem(409, 'idempotency.key_reused', 'Idempotency conflict', str(error)) from error
        except (service.ProductBookingError, TradeFieldError) as error:
            code = getattr(error, 'code', 'request.validation_failed')
            raise ApiProblem(409 if code == 'product.terms_changed' else 422, code, 'Product booking failed', str(error),
                errors=[ValidationIssue(location=['body', error.field], message=str(error), kind='value_error')]) from error
        response.headers['Location'] = f'/v1/trades/{result.data.trade.trade_id}'
        return result

    @router.post('/v1/trades/structured-products', response_model=TradeDetailResponse, status_code=201)
    def structured(request: ProductBookingRequest, response: Response,
                   key: str = Header(alias='Idempotency-Key', min_length=1, max_length=255),
                   context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency)):
        return booking(request, response, key, context, connection, 'STRUCTURED_PRODUCT')

    @router.post('/v1/trades/futures', response_model=TradeDetailResponse, status_code=201)
    def futures(request: ProductBookingRequest, response: Response,
                key: str = Header(alias='Idempotency-Key', min_length=1, max_length=255),
                context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency)):
        return booking(request, response, key, context, connection, 'FUTURE')

    @router.post('/v1/trades/swaps', response_model=TradeDetailResponse, status_code=201)
    def swaps(request: ProductBookingRequest, response: Response,
              key: str = Header(alias='Idempotency-Key', min_length=1, max_length=255),
              context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency)):
        return booking(request, response, key, context, connection, 'SWAP')

    def propose(request, context, connection):
        actor = authorized(connection, context)
        try:
            with connection.begin_nested(): data = service.submit_proposal(connection, context.tenant_id, actor, request)
        except RepositoryNotFound as error: raise HTTPException(404, str(error)) from error
        except (service.ProductBookingError, InvalidWorkflowState) as error:
            raise ApiProblem(422, 'product.invalid_terms', 'Invalid product terms', str(error)) from error
        return ReferenceDataProposalResponse(data=data, meta=meta(context))

    @router.post('/v1/trades/bonds', response_model=TradeDetailResponse, status_code=201)
    def bonds(request: ProductBookingRequest, response: Response,
              key: str = Header(alias='Idempotency-Key', min_length=1, max_length=255),
              context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency)):
        return booking(request, response, key, context, connection, 'BOND')

    @router.post('/v1/instrument-booking-convention-proposals', response_model=ReferenceDataProposalResponse, status_code=201)
    def conventions(request: ConventionProposalRequest, context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency)):
        return propose(request, context, connection)

    @router.post('/v1/instruments/swap-proposals', response_model=ReferenceDataProposalResponse, status_code=201)
    def swap_proposal(request: SwapProposalRequest, context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency)):
        return propose(request, context, connection)

    @router.post('/v1/future-proposals', response_model=ReferenceDataProposalResponse, status_code=201)
    def future_proposal(request: FutureProposalRequest, context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency)):
        return propose(request, context, connection)
    @router.post('/v1/future-family-proposals', response_model=ReferenceDataProposalResponse, status_code=201)
    def family_proposal(request: FutureFamilyProposalRequest, context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency)):
        return propose(request, context, connection)

    @router.get('/v1/future-families', response_model=FutureFamilySearchResponse)
    def families(q: str = Query(default='', max_length=250), limit: int = Query(default=20, ge=1, le=100),
                 offset: int = Query(default=0, ge=0), context: TenantContext = Depends(get_tenant_context),
                 connection=Depends(connection_dependency)):
        authorized(connection, context)
        items, total = service.search_families(connection, context.tenant_id, q, limit, offset)
        return FutureFamilySearchResponse(data=items, meta=meta(context, total=total, limit=limit, offset=offset))
    return router
