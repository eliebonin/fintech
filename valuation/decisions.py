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
    if not own and any(b.get('key',{}).get('product_basis')=='FUTURE' for b in buckets):
        add('FUTURES_DAILY_VARIATION','Futures price variation uses opening holdings and signed execution prices with each frozen contract multiplier/divisor once. Each economic day converts at closing FX; gross notional is not an asset value and margin cash is separate.',
            valueBasis='PRICE_VARIATION_NOT_CONTRACT_MTM')
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
        normalization=proof.get('bondPriceNormalization')
        if normalization:
            add('BOND_DIRTY_TO_CLEAN',
                f"Source DIRTY {normalization.get('dirtyPrice')} minus quoted accrued {normalization.get('accruedPer100')} per 100 gives CLEAN {normalization.get('cleanPrice')}. Daily earned interest and accrued-stock FX use separate strategy inputs; the quotation component creates no income.",
                refs,quoteSettlementDate=normalization.get('quoteSettlementDate'),**facts)
    for effect in evidence.get('executionInputs',[]):
        booking=effect['booking']
        movement=(booking.get('product_evidence') or {}).get('quantityMovement')
        if movement:
            add('FUND_UNIT_'+movement['kind'],'Fund units move at a separately policy-selected daily NAV for the market bridge. The source zero is not a purchase price; no cash movement or distribution income is generated.',
                [effect.get('event_id'),booking.get('trade_id')],effectiveAt=effect.get('effective_at'),incomeRecognition=movement['incomeRecognition'])
            continue
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
    from security_master_schema.cash_products import QUOTED_WRAPPERS
    if key.get('product_basis') in QUOTED_WRAPPERS:
        add('QUOTED_WRAPPER_PRICE','Signed listed-security units multiply their own whole-wrapper quote and frozen listing factors, translated from trade-price currency. Underlying exposure, commodity entitlement, embedded leverage and fees are not applied a second time. Recorded distributions and costs remain separate.',
            productBasis=key['product_basis'],unitMultiplier=key.get('unit_multiplier'),quoteFactor=key.get('quote_factor'))
    if key.get('product_basis')=='DIGITAL_ASSET':
        add('SPOT_DIGITAL_ASSET_PRICE','Signed token units multiply the selected listing price and frozen factors, then trade-quote/reporting FX. The listing and configured daily cut/calendar remain distinct. No stablecoin peg, staking income, fork units, margin or derivatives are inferred.',
            unitMultiplier=key.get('unit_multiplier'),quoteFactor=key.get('quote_factor'))
    for fact in identity.get('facts',[]):
        b=fact.get('booking') or {};proof=b.get('product_evidence') or {}
        if proof.get('quantityUnitNormalization'):
            add('BOOKED_UNIT_LABEL_NORMALIZATION','The old SHARES label denotes the same wrapper/token unit count as UNITS. Only the projection label is normalized; booked quantity, price, factors and original ledger evidence are unchanged.',
                [fact.get('event_id'),fact.get('trade_id')],bookedUnit=proof.get('bookedQuantityUnit'),projectionUnit=proof.get('normalizedQuantityUnit'))
    if key.get('product_basis')=='OPTION':
        add('OPTION_CONTRACT_PREMIUM','Signed whole contracts multiply the frozen premium multiplier and canonical contract premium, divided by the quote factor once, then convert with reporting FX. Deliverable/listing units and underlying prices are not multiplied again. No model price, exercise or expiry cashflow is inferred.',
            premiumMultiplier=key.get('unit_multiplier'),quoteFactor=key.get('quote_factor'),quantityUnit=key.get('quantity_unit'))
    if key.get('product_basis')=='SWAP':
        add('SWAP_WHOLE_MARK','Signed booked units or nominal multiply the supplied whole-swap mark, divided by the frozen quote factor once, then convert with reporting FX. Contractual notional, underlying price and leverage are not multiplied again. Funding is not modelled; dated RESET income remains separate.',
            quoteFactor=key.get('quote_factor'),unitMultiplier=key.get('unit_multiplier'),quantityUnit=key.get('quantity_unit'))
    if key.get('product_basis')=='ACTIVELY_MANAGED_CERTIFICATE':
        add('AMC_QUOTED_PRICE','AMC value uses signed booked quantity × frozen denomination multiplier × quoted price ÷ booked divisor, with reporting FX. Nominal quantities already include denomination; do not apply it twice. No fund NAV/publication-lag assumption, fee accrual or underlying look-through is inferred.',
            quoteFactor=key.get('quote_factor'),unitMultiplier=key.get('unit_multiplier'))
    if key.get('product_basis')=='STRUCTURED_PRODUCT':
        add('STRUCTURED_NOTE_WHOLE_MARK','Signed quantity × frozen denomination multiplier × whole-note price ÷ quote divisor, translated with reporting FX. Underlying returns and embedded leverage are not multiplied again. CLEAN marks may add assessed interest; DIRTY/NONE marks do not add it separately. Coupon income requires explicit recognition; later payment alone creates no new earnings.',
            quoteFactor=key.get('quote_factor'),unitMultiplier=key.get('unit_multiplier'),quantityUnit=key.get('quantity_unit'))
    if key.get('product_basis')=='BOND' and key.get('quantity_unit')=='NOMINAL':
        add('CLEAN_BOND_NOMINAL','Bond market values use clean quotations per 100 nominal. Booked dirty executions are normalised once using frozen accrued-interest evidence; daily earned interest is separate from the accumulated balance.',
            quoteFactor=key.get('quote_factor'),unitMultiplier=key.get('unit_multiplier'))
    boundary_fields=('openingValue','closingValue','executionValue','components')
    if key.get('product_basis')=='FUTURE':
        add('FUTURES_DAILY_VARIATION','Opening contracts use the prior contract price; signed period executions use booked prices. Apply the frozen monetary multiplier/divisor once and translate local variation at economic-day closing FX. Gross notional is not an asset value; margin cash and contract MTM are separate.',
            monetaryMultiplier=key.get('unit_multiplier'),quoteFactor=key.get('quote_factor'),valueBasis='PRICE_VARIATION_NOT_CONTRACT_MTM')
    elif all(name in identity for name in boundary_fields):
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
        elif item.get('kind')=='ACCRUED_BALANCE_FX':
            add('ACCRUED_INTEREST_OPENING_STOCK_FX','Opening local accrued stock times daily reporting-per-local FX change; coupon receipts and purchased/sold accrued are stock movements, not daily income.',
                instrumentId=item['instrumentId'],convention=item['convention'])
        elif item.get('kind')=='MISSING_DAILY_ACCRUAL_FX':
            add('DAILY_INTEREST_FX_UNAVAILABLE','Daily interest is recorded locally but is not included in reporting-currency P&L because policy FX is unavailable.',
                instrumentId=item['instrumentId'],valueDate=item['valueDate'])
        elif item.get('kind')=='MISSING_DAILY_ACCRUAL':
            add('DAILY_ACCRUAL_NOT_SUPPLIED','Accrual not supplied—not included. Price/FX P&L is calculated; absent daily earned interest is not confirmed zero.',
                instrumentId=item['instrumentId'],valueDate=item['valueDate'])
        elif item.get('kind')=='DAILY_ACCRUAL_NOT_APPLICABLE':
            add('DAILY_ACCRUAL_NOT_APPLICABLE','Coupon accrual is not applicable: all contributing booked terms confirm a zero-coupon bond. Price/FX movement is retained; no separate zero interest amount or discount-accretion accounting entry is invented.',
                instrumentId=item['instrumentId'],valueDate=item['valueDate'],reason=item['reason'],basis=item['basis'])
        elif item.get('kind')=='DAILY_ACCRUAL':
            balance=(item.get('payload') or {}).get('balanceReconciliation')
            text='Only daily earned interest contributes accrual P&L; the accumulated balance is retained separately.'
            if balance=='NOT_PROVIDED' and not any(v.get('kind')=='ACCRUED_BALANCE_FX' for v in evidence.get('economicInputs',[])):
                text='Recorded daily earned interest contributes accrual P&L. Accumulated balances and receivable FX were not assessed; missing is not zero.'
            add('DAILY_EARNED_ACCRUAL',text,[item.get('inputId')],**({'balanceReconciliation':balance} if balance else {}))
    return rules
