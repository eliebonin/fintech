"""Readable, versioned decisions derived solely from frozen calculation facts.

These records explain economics; they never select inputs or override a result.
Absent historical evidence stays absent rather than being retrospectively invented.
"""


def applied_decisions(evidence):
    rules=[]

    def add(code,explanation,refs=(),**facts):
        rules.append(dict(code=code,version=1,explanation=explanation,
            evidenceRefs=[str(r) for r in refs if r is not None],**facts))

    buckets=(evidence.get('projection') or {}).get('buckets',[])
    own=(evidence.get('identity') or {}).get('bucket')
    if own:buckets=[own]
    if any(b.get('key',{}).get('product_basis')=='FX_FORWARD' for b in buckets):
        add('FX_FORWARD_RATE_PNL','Signed base notional times contract-rate change; quote-currency P&L converts to reporting currency. Net rate-difference value subtracts the frozen agreed rate; it is not discounted model MTM.',
            valueBasis='UNDISCOUNTED_RATE_DIFFERENCE')

    for selection in evidence.get('selections',[]):
        day=str(selection.get('valuation_date',''))
        actual=selection.get('pricing_date_used')
        proof=selection.get('pricing_evidence') or {}
        refs=[selection.get(k) for k in ('policy_rule_id','market_data_observation_id','dataset_id')]
        facts=dict(valuationDate=day,requestedDate=selection.get('pricing_date_requested'),actualDate=actual,
            sourcePublishedAt=selection.get('source_published_at_utc'),receivedAt=selection.get('received_at_utc'),
            stalenessBusinessDays=selection.get('staleness_business_days'))
        if selection.get('input_role')=='FX_MATURITY_SUGGESTION':
            add('FX_MATURITY_RATE_SOURCE',f"Maturity spot suggestion {selection.get('selected_value')} is retained as source evidence; the actual booked closing rate is {selection.get('bookedClosingRate')}. It is not a cash movement.",refs,**facts)
        elif selection.get('input_role')=='FX':
            conversion=selection.get('conversion') or {}
            method=conversion.get('method','DIRECT')
            add('FX_'+method,f"Valuation {day} uses {method.lower()} FX conversion {conversion.get('rate',selection.get('selected_value'))}, from market date {actual}.",refs,**facts)
        else:
            code='FX_FORWARD_POLICY_RATE' if selection.get('input_role')=='FORWARD_RATE' else 'FUND_NAV_DATE' if proof.get('convention')=='NAV_DATE' else 'POLICY_MARK'
            label='forward contract rate' if code=='FX_FORWARD_POLICY_RATE' else 'fund NAV' if code=='FUND_NAV_DATE' else 'market mark'
            value=selection.get('valuation_value')
            if value is None: value=selection.get('selected_value')
            add(code,f"Valuation {day} uses {label} {value} from market date {actual}, under the recorded pricing rule.",refs,**facts)
        basis=proof.get('priceBasis')
        if basis:
            add('AS_TRADED_PRICE_BASIS',f"Source price basis {basis.get('sourceBasis')} was normalised to {basis.get('valuationBasis')} using retained conversion proof.",refs)
    for effect in evidence.get('executionInputs',[]):
        booking=effect['booking']
        add('BOOKED_EXECUTION_PRICE',f"Period execution uses booked price {booking['price']} and signed quantity {booking['quantity']}; it does not replace the opening market mark.",
            [effect.get('event_id'),booking.get('trade_id')],effectiveAt=effect.get('effective_at'))
        redemption=(booking.get('product_evidence') or {}).get('redemptionEvidence')
        if booking.get('product_basis')=='FX_FORWARD':
            terms=booking.get('product_evidence') or {}
            closing=terms.get('maturityEvidence')
            if closing:add('FX_FORWARD_MATURITY_CLOSE','Maturity uses the retained booked closing rate, including any sourced Ops override; it removes exposure without a cash movement.',[booking.get('trade_id')],closingRate=closing['price'])
        if redemption:
            inputs=redemption['inputs']
            add('BOND_MATURITY_REDEMPTION',f"Principal maturity closing on {inputs['valueDate']} uses sourced redemption price {inputs['price']} per 100 nominal. Proceeds contribute to that day's P&L; final interest and payment are separate.",
                [inputs.get('termId'),booking.get('trade_id')],effectiveDate=inputs['valueDate'])
    if evidence.get('noMarketMarksRequired'):
        add('ZERO_BOUNDARY_NO_MARK','Opening and closing quantities are zero; no boundary market marks are required. Period execution effects are retained.')
    if evidence.get('executionFxConvention')=='ECONOMIC_DAY_END':
        add('EXECUTION_DAY_END_FX','Period executions use their economic day closing FX, not the preceding day FX; new positions do not acquire overnight FX P&L.')
    identity=evidence.get('identity') or {}
    key=identity.get('bucket',{}).get('key',{})
    if key.get('product_basis')=='BOND' and key.get('quantity_unit')=='NOMINAL':
        add('CLEAN_BOND_NOMINAL','Bond market values use clean quotations per 100 nominal. Booked dirty executions are normalised once using frozen accrued-interest evidence; daily earned interest is separate from the accumulated balance.',
            quoteFactor=key.get('quote_factor'),unitMultiplier=key.get('unit_multiplier'))
    boundary_fields=('openingValue','closingValue','executionValue','components')
    if all(name in identity for name in boundary_fields):
        # Explain the stored bridge without repricing, rounding or inventing missing
        # legacy values. PRICE/FX/CROSS are market components; income/costs are separate.
        add('POSITION_VALUE_BRIDGE',f"Market P&L is closing value {identity['closingValue']} minus opening value {identity['openingValue']} minus signed period execution value {identity['executionValue']}. Recorded income and costs are added separately; these are not cash-account balances.",
            **{name:identity[name] for name in boundary_fields})
    currency=identity.get('bucket',{}).get('key',{}).get('currency_id')
    if currency is not None and currency==identity.get('reportingCurrency'):
        add('SAME_CURRENCY_FX_IDENTITY','Position and reporting currencies are identical; FX conversion is one and no market FX observation is needed.')
    for adjustment in evidence.get('splitAdjustments',[]):
        event=adjustment.get('event') or {}
        add('REVIEWED_SHARE_RATIO',f"An approved share-ratio event adjusts derived quantity from {adjustment.get('quantity_before')} to {adjustment.get('quantity_after')}; original booked trades remain unchanged.",
            [event.get('action_id'),event.get('review_id')],adjustment=adjustment)
    for item in evidence.get('economicInputs',[]):
        booking=item.get('booking') or {}
        if booking:
            payment=booking.get('recognitionRole')=='PAYMENT_ONLY'
            add('PAYMENT_ONLY_NO_INCOME' if payment else 'RECORDED_ECONOMIC_INCOME',
                'Payment settles a recorded flow without recognising income again.' if payment else f"Recorded {booking.get('component')} contributes income under its explicit recognition role.",
                [item.get('tradeId')])
        elif item.get('kind')=='DAILY_ACCRUAL':
            balance=(item.get('payload') or {}).get('balanceReconciliation')
            text='Only daily earned interest contributes accrual P&L; the accumulated balance is retained separately.'
            if balance=='NOT_PROVIDED':
                text='Recorded daily earned interest contributes accrual P&L. Accumulated balances and receivable FX were not assessed; missing is not zero.'
            add('DAILY_EARNED_ACCRUAL',text,[item.get('inputId')],**({'balanceReconciliation':balance} if balance else {}))
    return rules
