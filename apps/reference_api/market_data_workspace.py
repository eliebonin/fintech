"""Bounded discovery projection: metadata and one permitted mark, never history."""
from datetime import date, datetime
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_, true, String
from security_master_schema import models as m
from market_data.rights import denied_display_datasets
from .contracts import ApiMeta
from .tenant_context import TenantContext, get_tenant_context
from .repository import (_market_data_visible_node_clause,
    _market_data_display_entitlement_clause, _current_market_data_observation_clause)
from .problem_details import current_request_id

class MarketDataCatalogueItem(BaseModel):
    seriesId: UUID
    referenceNodeId: UUID
    referenceNodeName: str
    seriesType: str
    closingMethod: str
    valueType: str
    currency: str | None
    datasetName: str | None
    expectedFrequency: str
    latestMarketDate: date | None
    latestValue: str | None
    latestReceivedAt: datetime | None
    latestDatasetName: str | None
    latestValueBasis: str | None

class MarketDataCatalogueResponse(BaseModel):
    data: list[MarketDataCatalogueItem]
    meta: ApiMeta


def market_data_catalogue(c, tenant, query, as_of, limit, offset, api_version):
    series, node, dataset = m.market_data_series, m.financial_reference_node, m.dataset
    denied = denied_display_datasets(c, tenant, date.today())
    filters = [series.c.status=='ACTIVE', node.c.status=='ACTIVE',
        _market_data_visible_node_clause(series.c.reference_node_id, tenant),
        or_(series.c.default_dataset_id.is_(None),
            (series.c.default_dataset_id.not_in(denied) &
             _market_data_display_entitlement_clause(series.c.default_dataset_id,tenant,series.c.market_data_series_id) &
             (dataset.c.status=='ACTIVE') & (dataset.c.valid_from<=date.today()) &
             or_(dataset.c.valid_to.is_(None),dataset.c.valid_to>=date.today())))]
    base = select(series.c.market_data_series_id.label('seriesId'),
        series.c.reference_node_id.label('referenceNodeId'), node.c.canonical_name.label('referenceNodeName'),
        series.c.series_type.label('seriesType'), series.c.closing_method.label('closingMethod'),
        series.c.value_type.label('valueType'), m.currency.c.currency_code.label('currency'),
        dataset.c.display_name.label('datasetName'),series.c.expected_frequency_code.label('expectedFrequency'))        .select_from(series.join(node,node.c.reference_node_id==series.c.reference_node_id)
            .outerjoin(dataset,dataset.c.dataset_id==series.c.default_dataset_id)
            .outerjoin(m.currency,m.currency.c.currency_id==series.c.currency_id)).where(*filters)
    if query:
        base=base.where(or_(node.c.canonical_name.icontains(query,autoescape=True),
            func.cast(node.c.reference_node_id, String).icontains(query,autoescape=True),
            dataset.c.display_name.icontains(query,autoescape=True),series.c.series_type.icontains(query,autoescape=True)))
    total=int(c.scalar(select(func.count()).select_from(base.subquery())))
    page=base.order_by(node.c.canonical_name,series.c.series_type,series.c.market_data_series_id).limit(limit).offset(offset).subquery('catalogue_page')
    observation=m.market_data_observation
    actual=m.dataset.alias('catalogue_actual_dataset')
    latest=select(observation.c.market_date.label('latestMarketDate'),observation.c.value.label('latestValue'),
        observation.c.received_at_utc.label('latestReceivedAt'),actual.c.display_name.label('latestDatasetName'),
        observation.c.value_basis.label('latestValueBasis')).select_from(observation.join(actual,actual.c.dataset_id==observation.c.dataset_id))        .where(observation.c.market_data_series_id==page.c.seriesId,
            observation.c.quality_status=='ACCEPTED',observation.c.market_date<=as_of,
            observation.c.dataset_id.not_in(denied),actual.c.status=='ACTIVE',actual.c.valid_from<=date.today(),
            or_(actual.c.valid_to.is_(None),actual.c.valid_to>=date.today()),
            _current_market_data_observation_clause(observation),
            _market_data_display_entitlement_clause(observation.c.dataset_id,tenant,observation.c.market_data_series_id))        .order_by(observation.c.market_date.desc().nulls_last(),observation.c.observed_at_utc.desc(),
            observation.c.received_at_utc.desc(),observation.c.market_data_observation_id.desc()).limit(1).lateral('catalogue_latest')
    rows=c.execute(select(page,latest).select_from(page.outerjoin(latest,true()))
        .order_by(page.c.referenceNodeName,page.c.seriesType,page.c.seriesId)).mappings().all()
    items=[]
    for row in rows:
        values=dict(row)
        values['latestValue']=str(values['latestValue']) if values['latestValue'] is not None else None
        items.append(MarketDataCatalogueItem(**values))
    return MarketDataCatalogueResponse(data=items,meta=ApiMeta(tenantContext=str(tenant),source='live-reference-api',
        apiVersion=api_version,correlationId=current_request_id(),limit=limit,offset=offset,total=total))


def market_data_workspace_router(connection_dependency, authority, api_version):
    router=APIRouter(prefix='/v1/market-data',tags=['market data workspace'])
    @router.get('/catalogue',response_model=MarketDataCatalogueResponse)
    def catalogue(q:str=Query(default='',max_length=250),as_of:date|None=Query(default=None,alias='asOf'),
        limit:int=Query(default=25,ge=1,le=100),offset:int=Query(default=0,ge=0,le=100000),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        authority(c,context)
        return market_data_catalogue(c,context.tenant_id,q.strip(),as_of or date.today(),limit,offset,api_version)
    return router
