"""Review signals from retained coverage only; never financial amounts or gates."""


def pnl_completeness(accrual,stock,cash):
    return 'PARTIAL' if any((coverage or {}).get('missingCount',0)>0 for coverage in (accrual,stock,cash)) else 'RECORDED_COMPONENTS'


def position_attention(evidence,missing_by_instrument=None,subject_id=None):
    evidence=evidence or {};inputs=evidence.get('economicInputs',[]);found=set()
    kinds={value.get('kind') for value in inputs}
    if 'MISSING_DAILY_ACCRUAL' in kinds:found.add('Interest not supplied')
    if 'MISSING_DAILY_ACCRUAL_FX' in kinds:found.add('Interest FX unavailable')
    if 'REINVESTMENT_INCOME_NOT_ASSESSED' in kinds:found.add('Reinvestment income unassessed')
    if any((s.get('staleness_business_days') or 0)>0 for s in evidence.get('selections',[])):found.add('Prior-session input')
    def reason(value):
        if value=='ACCRUED_BALANCE_FX_UNAVAILABLE':found.add('Accrued FX unavailable')
        elif value=='ACCRUAL_CURRENCY_CHANGED_WITHOUT_SINGLE_BASIS':found.add('Accrued currency needs review')
        elif value:found.add('Accrued balance unavailable')
    for value in inputs:
        if value.get('kind')!='ACCRUED_BALANCE_FX':continue
        for day in value.get('days',[]):
            reason(day.get('reason'))
            warnings=day.get('balance',{}).get('warnings',[])
            if any('ANCHOR_DIFFERS' in warning for warning in warnings):found.add('Accrued balance mismatch')
            if any(w in {'TRADE_ACCRUAL_UNAVAILABLE','COUPON_CURRENCY_CONVERSION_UNAVAILABLE'} for w in warnings):found.add('Accrued movements unavailable')
    # A currency/scope failure can leave no balance line. Associate its retained
    # canonical ID with frozen booking facts, never current reference metadata.
    instruments={str(subject_id)} if subject_id else set()
    for fact in (evidence.get('identity') or {}).get('facts',[]):
        instrument=((fact.get('booking') or {}).get('product_evidence') or {}).get('instrumentId')
        if instrument:instruments.add(str(instrument))
    for value in inputs:
        instrument=value.get('instrumentId') or (value.get('payload') or {}).get('instrumentId')
        if instrument:instruments.add(str(instrument))
    for instrument in instruments:
        for missing in (missing_by_instrument or {}).get(instrument,[]):reason(missing.get('reason'))
    order=('Interest not supplied','Interest FX unavailable','Accrued FX unavailable','Accrued balance unavailable',
        'Accrued currency needs review','Accrued balance mismatch','Accrued movements unavailable','Reinvestment income unassessed','Prior-session input')
    return [label for label in order if label in found]
