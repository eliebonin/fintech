"""Exact-date maintained bond stocks for monetary previews; no reconstruction."""
from uuid import UUID
from .balance_history import _history_rows,source_signature,signature_matches
from security_master_schema.evidence import evidence_hash
from security_master_schema.tenancy import assert_tenant_owns_strategy


def load_measure_stocks(c,request):
    assert_tenant_owns_strategy(c,request.tenant_id,request.strategy_id)
    day=request.closing_cutoff.date()
    rows=_history_rows(c,request.tenant_id,request.strategy_id,day,day,request.information_cutoff)
    signatures={};result={}
    for row in rows:
        build=row['build_id']
        if build not in signatures:
            signatures[build]=signature_matches(row['source_proof'],source_signature(c,request.tenant_id,
                request.strategy_id,row['to_date'],request.information_cutoff))
        result[(row['instrument_id'],row['currency_id'])]=dict(row,source_status='CURRENT' if signatures[build] else 'STALE')
    return result


def position_stock(stocks,instrument,currency,nominal,*,compatible_positions,zero_coupon=False):
    """A strategy/bond stock cannot be apportioned between separate positions implicitly."""
    if compatible_positions!=1:
        raise ValueError('Instrument-level accrued balance cannot be duplicated across listings/currencies')
    instrument=UUID(str(instrument));row=stocks.get((instrument,currency))
    if row is None:
        if any(key[0]==instrument for key in stocks):raise ValueError('Maintained accrued-balance currency differs from bond quote currency')
        if zero_coupon:
            from decimal import Decimal
            return Decimal(0),dict(basis='FROZEN_ZERO_COUPON_TERMS',amount='0',sourceStatus='NOT_APPLICABLE')
        raise ValueError('Exact-date maintained accrued-interest balance is missing; review and rebuild balance history')
    if row['source_status']!='CURRENT':raise ValueError('Maintained accrued-balance history is stale; rebuild before using market value')
    amount=row['closing_balance']
    if amount is None:raise ValueError('Maintained closing accrued balance is not assessed; missing is not zero')
    if not nominal and amount:raise ValueError('A remaining accrued receivable cannot be allocated to a flat security position')
    return amount,dict(historyId=str(row['history_id']),buildId=str(row['build_id']),valueDate=row['value_date'].isoformat(),
        amount=str(amount),currencyId=str(currency),eligibleNominal=str(nominal),nominalBasis='CURRENT_SCOPED_BOND_HOLDING',
        sourceStatus='CURRENT',basis='MAINTAINED_CLOSING_BALANCE',sourceProofHash=evidence_hash(row['source_proof']),warnings=row['evidence'].get('warnings',[]))
