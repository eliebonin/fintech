"""Response-only coverage of retained P&L components, never a new calculator.

Amounts below are exact sums of already stored reporting-currency components.
Their presence does not prove that Ops supplied every economic flow due. In
particular, cash snapshots are stocks and are not cash FX earnings in this result.
"""
from decimal import Decimal, localcontext


# Disjoint groups: do not add the inclusive market/gross/net totals as sources.
SOURCES = (
    ('PRICE', 'Price movements', ('PRICE',), 'Price movement on investment positions, including futures price variation translated at daily closing FX.'),
    ('FX', 'Position FX movements', ('FX',), 'Currency translation of investment positions; excludes cash balances.'),
    ('PRICE_FX_CROSS', 'Price × FX interaction', ('PRICE_FX_CROSS',), 'Joint price and FX movement, counted once.'),
    ('ACCRUAL', 'Daily interest earned', ('ACCRUAL',), 'Daily added interest only, not the accumulated accrued balance.'),
    ('CARRY', 'Accrued-interest FX', ('CARRY',), 'Opening assessed or reconstructed accrued balance × daily FX change.'),
    ('RESET', 'Resets', ('RESET',), 'Recorded income-classified reset flows, not cumulative holdings.'),
    ('DIVIDEND', 'Dividends', ('DIVIDEND',), 'Recorded income-classified dividend flows.'),
    ('OTHER_INCOME', 'Other recognised income', ('COUPON', 'CASHFLOW'), 'Recorded coupon or other income flows; payment confirmations alone do not create earnings.'),
    ('COSTS', 'Fees and taxes', ('BROKER_FEE', 'CUSTODY_FEE', 'MANAGEMENT_FEE', 'PERFORMANCE_FEE', 'TAX', 'OTHER_COST'), 'Signed recorded costs; negative amounts reduce the result.'),
    ('ADJUSTMENT', 'Controlled adjustments', ('ADJUSTMENT',), 'Retained review adjustments included in this result version.'),
    ('CASH_BALANCE_FX', 'Cash-balance FX P&L', ('CASH_FX',), 'Opening cash balance × daily FX change; intraday movements are treated at closing FX.'),
)


def source_coverage(batch):
    """Project one already-authorized batch, without queries or evidence mutation."""
    summary = batch.get('summary') or {}
    if summary.get('evidenceAccess') == 'DENIED':
        return None
    items = batch.get('items') or []
    components = [item.get('components') or {} for item in items]
    complete_breakdown = all(bool(part) for part in components)
    known = {key for _, _, codes, _ in SOURCES for key in codes}
    groups = list(SOURCES)
    if any('MODEL_MARK_CHANGE' in part for part in components):
        groups.append(('MODEL_MARK_CHANGE', 'Supplied valuation mark changes', ('MODEL_MARK_CHANGE',),
            'Separately stored mark-change attribution; no model is run by this view.'))
    known.add('MODEL_MARK_CHANGE')
    unknown = sorted({key for part in components for key in part if key not in known})
    if unknown:
        groups.append(('OTHER_STORED', 'Other stored components', tuple(unknown),
            'Unclassified retained component codes. Inspect their evidence before relying on the category.'))
    missing = (summary.get('accrualCoverage') or {}).get('missingCount')
    if missing is None:
        missing = sum(1 for item in items for value in (item.get('evidence') or {}).get('economicInputs', [])
            if value.get('kind') in {'MISSING_DAILY_ACCRUAL','MISSING_DAILY_ACCRUAL_FX'})
    rows = []
    cash_coverage=summary.get('cashCoverage') or {}
    balance_coverage=summary.get('accruedBalanceCoverage') or {}
    price_gaps=sum(gap.get('role') in {'PRICE','FX'} for gap in (summary.get('inputCoverage') or {}).get('gaps',[]))
    with localcontext() as context:
        context.prec = 512
        for code, label, codes, description in groups:
            amounts = [Decimal(str(part[key])) for part in components for key in codes if key in part]
            count = sum(any(key in part for key in codes) and not item.get('cash_account_id') for item,part in zip(items,components))
            cash_count = sum(any(key in part for key in codes) and bool(item.get('cash_account_id')) for item,part in zip(items,components))
            status = 'INCLUDED' if amounts else ('NOT_RECORDED' if complete_breakdown else 'NOT_ASSESSED')
            if code == 'ACCRUAL' and missing:
                status = 'PARTIAL' if amounts else 'MISSING_INPUTS'
            if code=='CARRY' and balance_coverage.get('missingCount'):
                status='PARTIAL' if amounts else 'MISSING_INPUTS'
            omitted=missing if code=='ACCRUAL' else cash_coverage.get('missingCount',0) if code=='CASH_BALANCE_FX' else 0
            if code=='CARRY':omitted=balance_coverage.get('missingCount',0)
            if code in {'PRICE','FX','PRICE_FX_CROSS'} and price_gaps:
                omitted=price_gaps
                status='PARTIAL' if amounts else 'MISSING_INPUTS'
            if code=='CASH_BALANCE_FX':
                omitted+=cash_coverage.get('missingFxCount',0)
                if amounts:status='PARTIAL' if cash_coverage.get('status')!='INCLUDED' else 'INCLUDED'
                else:status='MISSING_INPUTS' if omitted else 'NOT_ASSESSED'
            rows.append(dict(code=code, label=label, componentCodes=list(codes), description=description,
                amount=format(sum(amounts, Decimal(0)), 'f') if amounts else None,
                status=status, positionCount=count, cashAccountCount=cash_count, missingCount=omitted))
        total = sum((Decimal(row['amount']) for row in rows if row['amount'] is not None), Decimal(0))
        net = summary.get('netPnl')
        reconciliation = 'NOT_ASSESSED' if net is None or not complete_breakdown else (
            'MATCH' if total == Decimal(str(net)) else 'MISMATCH')
    included_total = format(total, 'f') if complete_breakdown or any(part for part in components) else None
    if summary.get('hasCalculatedContributions') is False:included_total=None;net=None;reconciliation='NOT_ASSESSED'
    return dict(rows=rows, includedTotal=included_total, recordedNet=net,
        reconciliation=reconciliation, basis='STORED_REPORTING_CURRENCY_COMPONENTS')
