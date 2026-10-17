"""Contract-rate inputs, never an automatic spot substitution before maturity."""
from datetime import datetime
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.market_data_resolver import resolve_market_data,ResolutionRequest


def select_forward_rate(c,request,subject,cutoff,conventions):
    rr=ResolutionRequest(request.tenant_id,subject,request.policy_id,cutoff.date(),request.cut_id,request.information_cutoff,'VALUATION',request.strategy_id)
    selected=resolve_market_data(c,rr)
    if selected.status!='SELECTED':raise ValueError(f'Forward contract-rate input blocked: {selected.exception_code or selected.status}')
    s=c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==selected.market_data_series_id)).mappings().one()
    rule=c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==selected.policy_rule_id)).mappings().one()
    dims={}
    for code,value in c.execute(select(m.market_data_series_dimension.c.dimension_code,m.market_data_series_dimension.c.dimension_value).where(
        m.market_data_series_dimension.c.market_data_series_id==selected.market_data_series_id)):dims.setdefault(code,set()).add(value)
    codes=dict(c.execute(select(m.currency.c.currency_id,m.currency.c.currency_code).where(m.currency.c.currency_id.in_(
        [conventions['baseCurrencyId'],conventions['priceCurrencyId']]))).all())
    from uuid import UUID
    base=codes[UUID(conventions['baseCurrencyId'])];quote=codes[UUID(conventions['priceCurrencyId'])]
    measure=c.scalar(select(m.series_measure_definition.c.measure_code).where(m.series_measure_definition.c.series_measure_definition_id==s['measure_definition_id']))
    if (s['reference_node_id']!=subject or s['series_type']!='FX_FORWARD' or s['value_type']!='RATE' or measure!='FX_RATE'
        or rule['series_type']!='FX_FORWARD' or rule['value_basis']!='RAW' or s['currency_id']!=selected.currency_id
        or str(s['currency_id'])!=conventions['priceCurrencyId'] or dims.get('BASE_CURRENCY')!={base} or dims.get('QUOTE_CURRENCY')!={quote}
        or dims.get('RATE_BASIS')!={'FORWARD_OUTRIGHT'} or dims.get('MATURITY_DATE')!={conventions['maturityDate']}):
        raise ValueError('Forward input requires contract-specific outright rate, currencies and maturity; spot/MTM cannot substitute')
    proof=selected.pricing_evidence or {};calendar=proof.get('calendarEvidence',{})
    if (rule['pricing_convention'] not in ('EXPLICIT_TIME','NAMED_FIXING') or calendar.get('source')!='GOVERNED_SESSIONS' or not calendar.get('sealed')
        or rule['max_staleness_business_days'] is None or datetime.fromisoformat(proof['pricingTargetUtc'])>cutoff):
        raise ValueError('Forward rates require governed timed selection and explicit freshness')
    from .economics import finite_decimal
    finite_decimal(selected.selected_value,'forward rate',positive=True)
    return rr,selected
