"""Read-only exact stock translation using retained evidence, with no data fetch."""
from decimal import Decimal,InvalidOperation,localcontext
from datetime import date,timedelta


def _decimal(value):
    if not isinstance(value,(str,Decimal)):return None
    try:
        result=Decimal(value)
        return result if result.is_finite() else None
    except InvalidOperation:return None


def _translated(stock,rate,identity):
    value=_decimal(stock)
    if value is None:return None,'STOCK_NOT_RECORDED'
    if value==0:return '0','ZERO_STOCK'
    if identity:return format(value,'f'),'SAME_CURRENCY'
    fx=_decimal(rate)
    if fx is None or fx<=0:return None,'FX_NOT_RECORDED'
    with localcontext() as ctx:
        ctx.prec=512
        return format(value*fx,'f'),'FROZEN_FX'


def _boundary_rates(evidence):
    candidates={}
    for selection in (evidence or {}).get('selections',[]):
        conversion=selection.get('conversion') or {}
        if selection.get('input_role')!='FX' or not conversion.get('sourceCurrencyId') or not conversion.get('targetCurrencyId'):continue
        key=(selection.get('valuation_date'),str(conversion['sourceCurrencyId']),str(conversion['targetCurrencyId']))
        rate=_decimal(conversion.get('rate'))
        if rate is not None and rate>0:candidates.setdefault(key,{})[rate]=format(rate,'f')
    return {key:next(iter(values.values())) if len(values)==1 else None for key,values in candidates.items()}


def project_stocks(evidence,reporting_currency_id):
    rows=[]
    proofs=[p for p in (evidence or {}).get('economicInputs',[]) if p.get('kind')=='ACCRUED_BALANCE_FX']
    if not proofs:return rows
    rates=_boundary_rates(evidence)
    for proof in proofs:
        local=proof.get('currencyId');identity=bool(local and reporting_currency_id and str(local)==str(reporting_currency_id))
        for day in proof.get('days',[]):
            balance=day.get('balance') or {}
            fx0=day.get('opening_fx');fx1=day.get('closing_fx')
            if local and reporting_currency_id and not identity:
                try:prior=(date.fromisoformat(balance['value_date'])-timedelta(days=1)).isoformat()
                except (KeyError,ValueError,TypeError):prior=None
                if fx0 is None and prior:fx0=rates.get((prior,str(local),str(reporting_currency_id)))
                if fx1 is None:fx1=rates.get((balance.get('value_date'),str(local),str(reporting_currency_id)))
            opening,basis0=_translated(balance.get('opening'),fx0,identity) if local and reporting_currency_id else (None,'CURRENCY_NOT_RECORDED')
            closing,basis1=_translated(balance.get('closing'),fx1,identity) if local and reporting_currency_id else (None,'CURRENCY_NOT_RECORDED')
            rows.append(dict(valueDate=balance.get('value_date'),currencyId=local,reportingCurrencyId=reporting_currency_id,
                openingReporting=opening,closingReporting=closing,openingBasis=basis0,closingBasis=basis1,
                openingFx='1' if identity else fx0,closingFx='1' if identity else fx1))
    return rows
