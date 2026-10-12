"""Policy-selected FX, quote-per-base orientation and immutable conversion proof."""
from dataclasses import asdict,dataclass
from datetime import date
from decimal import Decimal,ROUND_HALF_EVEN,localcontext
from uuid import UUID
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.market_data_resolver import ResolutionRequest,resolve_market_data
from .economics import finite_decimal


@dataclass(frozen=True)
class FxConversion:
    source_currency_id: UUID
    target_currency_id: UUID
    rate: Decimal
    economic_date: date
    observation_date: date | None
    evidence: dict
    selection: object | None = None
    resolution_request: object | None = None


def conversion_rate(value, *, inverse=False):
    finite_decimal(value,'FX rate',positive=True)
    if not inverse: return value
    with localcontext() as ctx:
        ctx.prec=100
        rate=(Decimal(1)/value).quantize(Decimal('0.000000000001'),rounding=ROUND_HALF_EVEN)
    if rate<=0: raise ValueError('Inverse FX rate below supported precision')
    return rate


def resolve_fx(c,request,source_currency_id,target_currency_id,economic_date):
    if source_currency_id==target_currency_id:
        return FxConversion(source_currency_id,target_currency_id,Decimal(1),economic_date,None,{'method':'IDENTITY'})
    codes=dict(c.execute(select(m.currency.c.currency_id,m.currency.c.currency_code).where(
        m.currency.c.currency_id.in_([source_currency_id,target_currency_id]),m.currency.c.status=='ACTIVE')).all())
    if len(codes)!=2: raise ValueError('Active FX source and reporting currency required')
    dims=m.market_data_series_dimension;s=m.market_data_series;n=m.financial_reference_node;t=m.reference_node_type
    def subjects(base,quote):
        def dimension(code,value):
            return s.c.market_data_series_id.in_(select(dims.c.market_data_series_id).where(dims.c.dimension_code==code,dims.c.dimension_value==value))
        return list(c.scalars(select(s.c.reference_node_id).join(n,s.c.reference_node_id==n.c.reference_node_id).join(t).where(
            t.c.type_code=='FX_PAIR',s.c.status=='ACTIVE',s.c.series_type=='FX_SPOT',s.c.value_type=='RATE',
            dimension('BASE_CURRENCY',base),dimension('QUOTE_CURRENCY',quote)).distinct()))
    pairs=subjects(codes[source_currency_id],codes[target_currency_id]);inverse=False
    if not pairs:
        pairs=subjects(codes[target_currency_id],codes[source_currency_id]);inverse=True
    if len(pairs)!=1: raise ValueError('Missing or ambiguous governed FX currency pair')
    rr=ResolutionRequest(request.tenant_id,pairs[0],request.policy_id,economic_date,request.cut_id,
        request.information_cutoff,'VALUATION',request.strategy_id)
    selected=resolve_market_data(c,rr)
    if selected.status!='SELECTED': raise ValueError(f'FX input selection blocked: {selected.exception_code or selected.status}')
    rule=c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==selected.policy_rule_id)).mappings().one()
    series=c.execute(select(s).where(s.c.market_data_series_id==selected.market_data_series_id)).mappings().one()
    dimensions={}
    measure=c.scalar(select(m.series_measure_definition.c.measure_code).where(
        m.series_measure_definition.c.series_measure_definition_id==series['measure_definition_id']))
    for code,value in c.execute(select(dims.c.dimension_code,dims.c.dimension_value).where(dims.c.market_data_series_id==selected.market_data_series_id)):
        dimensions.setdefault(code,set()).add(value)
    base,quote=(target_currency_id,source_currency_id) if inverse else (source_currency_id,target_currency_id)
    if (dimensions.get('BASE_CURRENCY')!={codes[base]} or dimensions.get('QUOTE_CURRENCY')!={codes[quote]}
            or series['currency_id']!=quote or series['value_type']!='RATE' or series['series_type']!='FX_SPOT'
            or rule['value_basis']!='RAW' or measure!='FX_RATE'):
        raise ValueError('FX selection currency orientation or rate semantics mismatch')
    if inverse and not rule.get('allow_inverse_fx',False): raise ValueError('Inverse FX requires explicit policy permission')
    proof=selected.pricing_evidence or {}
    from datetime import datetime
    target=datetime.fromisoformat(proof.get('pricingTargetUtc',''))
    if target.utcoffset() is None or target>request.closing_cutoff:
        raise ValueError('FX pricing target is later than economic cutoff')
    calendar=proof.get('calendarEvidence',{})
    if (rule['pricing_convention'] not in ('NAMED_FIXING','EXPLICIT_TIME')
        or calendar.get('source')!='GOVERNED_SESSIONS' or not calendar.get('sealed')
        or rule['max_staleness_business_days'] is None):
        raise ValueError('FX requires explicit timing, bounded freshness and sealed governed calendar')
    rate=conversion_rate(selected.selected_value,inverse=inverse)
    return FxConversion(source_currency_id,target_currency_id,rate,economic_date,selected.pricing_date_used,
        dict(method='RECIPROCAL' if inverse else 'DIRECT',rate=str(rate),sourceValue=str(selected.selected_value),
            sourceCurrencyId=str(source_currency_id),targetCurrencyId=str(target_currency_id),
            economicDate=economic_date.isoformat(),observationDate=selected.pricing_date_used.isoformat(),
            rounding='ROUND_HALF_EVEN_12DP' if inverse else 'NONE',selection=asdict(selected)),selected,rr)
