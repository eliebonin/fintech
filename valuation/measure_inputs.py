"""Governed, on-demand position measures. Not a staged NAV/P&L calculation.

Each measure can be unavailable independently. No source fallback, inferred
interim reset, accrued-stock guessing or currency relabelling is performed.
"""
from dataclasses import asdict
from decimal import Decimal as D
from uuid import UUID
from sqlalchemy import select
from security_master_schema import models as m
from market_data.display_access import assert_dataset_display
from .economics import canonical_payload,evidence_hash
from .position_measures import cash_security,bond,unit_swap,nominal_swap,linear_future,scaled
from .service import _selection
from .fx import resolve_fx
from positions.reconstruction import key_identity


def measure_reason(product,name,status,*,contract_invalid=False,nominal=False):
    """Presentation metadata only; never infer support by parsing error prose."""
    if status in {'AVAILABLE','MULTI_CURRENCY'}:return None
    if status=='LOCAL_ONLY':return 'FX_UNAVAILABLE'
    if product not in {'EQUITY','ETF','ETP','FUND','BOND','FUTURE','FX_FORWARD','SWAP'}:return 'NOT_SUPPORTED_YET'
    if contract_invalid:return 'INVALID_CONTRACT'
    if name=='marketValue' and product in {'FUTURE','FX_FORWARD'}:return 'NOT_SUPPORTED_YET'
    if product=='SWAP' and nominal and name=='economicExposure':return 'NOT_SUPPORTED_YET'
    return 'MISSING_INPUT'


def preview_measures(c,request,projection,descriptions,rows):
    currencies=dict(c.execute(select(m.currency.c.currency_id,m.currency.c.currency_code)).all())
    buckets={key_identity(b.key):b for b in projection.buckets}
    cache={};fx_cache={};results=[]
    from .forward_measures import load_contract_bookings
    forward_bookings=load_contract_bookings(c,request,[buckets[row['positionId']] for row in rows
        if buckets[row['positionId']].key.product_basis=='FX_FORWARD'])

    def mark(subject,product,currency,filters=()):
        key=(subject,product,currency,filters)
        if key in cache:
            value=cache[key]
            if isinstance(value,ValueError):raise value
            return value
        try:
            _,selected=_selection(c,request,subject,request.closing_cutoff,product,dimension_filters=filters)
            if currency is not None and selected.currency_id!=currency:raise ValueError('Price currency differs from booked measure currency')
            assert_dataset_display(c,request.tenant_id,{selected.dataset_id},series_contexts=[(selected.dataset_id,selected.market_data_series_id)])
            series=c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==selected.market_data_series_id)).mappings().one()
            dims={}
            for code,val in c.execute(select(m.market_data_series_dimension.c.dimension_code,m.market_data_series_dimension.c.dimension_value).where(m.market_data_series_dimension.c.market_data_series_id==selected.market_data_series_id)):
                dims.setdefault(code,set()).add(val)
            if any(dims.get(code)!={value} for code,value in filters):
                raise ValueError('Ambiguous market-data price semantics')
            value=selected.valuation_value if selected.valuation_value is not None else selected.selected_value
            cache[key]=(value,selected.currency_id,dict(currencyCode=currencies.get(selected.currency_id),selection=asdict(selected),dimensions={k:sorted(v) for k,v in dims.items()},series=dict(series)))
            return cache[key]
        except ValueError as exc:cache[key]=exc;raise

    def converted(amount,currency):
        if amount is None:return None,None
        if currency not in fx_cache:
            conversion=resolve_fx(c,request,currency,request.reporting_currency_id,request.closing_cutoff.date())
            if conversion.selection:
                s=conversion.selection
                assert_dataset_display(c,request.tenant_id,{s.dataset_id},series_contexts=[(s.dataset_id,s.market_data_series_id)])
            fx_cache[currency]=conversion
        conversion=fx_cache[currency]
        return scaled(amount,conversion.rate),conversion.evidence|dict(sourceCurrencyCode=currencies.get(currency),targetCurrencyCode=currencies.get(request.reporting_currency_id))

    for row in rows:
        bucket=buckets[row['positionId']];key=bucket.key;product=key.product_basis
        proofs=[descriptions[t].get('bookingEvidence',{}) for t in bucket.trade_ids]
        terms=[p.get('economics',{}).get('terms',{}) for p in proofs]
        selections={};issues={};amounts={};legs=[];route=None;native=key.currency_id;exposure_currency=native
        def selected(subject,kind,currency,role,filters=()):
            try:
                value,ccy,evidence=mark(subject,kind,currency,filters)
                # Freshness permission cannot make an old-unit RAW mark
                # compatible with quantities already changed by reviewed replay.
                from .corporate_actions import assert_native_mark_units
                assert_native_mark_units(projection.split_events,subject,request.closing_cutoff,
                    evidence['selection']['pricing_date_used'])
                selections[role]=evidence
                return value,ccy
            except ValueError as exc:
                issues[role]=str(exc)
                return None,currency
        try:
            if product in ('EQUITY','ETF','ETP','FUND'):
                subject=key.subject_id
                if product=='FUND':
                    parents={p.get('instrumentId') or (p.get('valuationConventions') or {}).get('instrumentId') for p in proofs}
                    if len(parents)!=1 or None in parents:raise ValueError('Unique frozen canonical fund NAV identity required')
                    subject=UUID(next(iter(parents)))
                    if key.unit_multiplier!=1 or key.quote_factor!=1:raise ValueError('Fund listing-to-NAV normalization is not supported')
                price,_=selected(subject,product,native,'securityPrice')
                amounts=cash_security(bucket.closing_quantity,price,key.unit_multiplier,key.quote_factor)
                route='SECURITY_PRICE'
            elif product=='BOND':
                conventions=[t.get('convention') or {} for t in terms]
                if key.quantity_unit=='UNITS':
                    denominations={cv.get('denomination') for cv in conventions}
                    if len(denominations)!=1 or None in denominations:raise ValueError('Unit bonds need one frozen denomination')
                    face=scaled(bucket.closing_quantity,D(next(iter(denominations))),key.unit_multiplier)
                elif key.quantity_unit=='NOMINAL':face=scaled(bucket.closing_quantity,key.unit_multiplier)
                else:raise ValueError('Unsupported bond quantity basis')
                if key.quote_factor!=100:raise ValueError('Bond marks require an explicit per-100 quotation')
                dirty,_=selected(key.subject_id,'BOND',native,'dirtyPrice',(('BOND_PRICE_TYPE','DIRTY'),))
                clean=None;balance=None
                if dirty is None:
                    clean,_=selected(key.subject_id,'BOND',native,'cleanPrice',(('BOND_PRICE_TYPE','CLEAN'),))
                    try:
                        from .accruals import read_accruals,accrual_amounts
                        same_instrument=[b for b in projection.buckets if b.closing_quantity and descriptions[b.trade_ids[0]]['instrumentId']==row['instrumentId']]
                        if len(same_instrument)!=1:raise ValueError('Position-level accrued balance cannot be duplicated across listings/currencies')
                        day=request.closing_cutoff.date()
                        entries=[a for a in read_accruals(c,request.tenant_id,request.strategy_id,day,day,request.information_cutoff) if str(a['instrument_id'])==row['instrumentId']]
                        if len(entries)!=1:raise ValueError('Assessed accrued-interest balance is missing')
                        entry=entries[0];payload=entry['payload']
                        if entry['currency_id']!=native:raise ValueError('Accrued balance currency differs from bond quote currency')
                        if payload.get('eligibleNominal') is None or D(payload['eligibleNominal'])!=face:raise ValueError('Accrued balance needs assessed nominal matching this position')
                        if not payload.get('inputs'):raise ValueError('Daily earnings are not an accrued-interest balance')
                        validated=accrual_amounts({k:D(v) for k,v in payload['inputs'].items()})
                        balance=validated['balanceLocal']
                        selections['accruedBalance']=dict(inputId=str(entry['input_id']),revision=entry['revision'],valueDate=str(day),amount=str(balance),eligibleNominal=str(face),sourceReference=payload.get('sourceReference'))
                    except ValueError as exc:issues['accruedBalance']=str(exc)
                amounts=bond(face,dirty=dirty,clean=clean,accrued=balance,quote_factor=key.quote_factor);route=amounts.pop('route')
                if dirty is not None:issues.pop('dirtyPrice',None)
            elif product=='FX_FORWARD':
                from .forward_measures import contractual_legs
                contract=contractual_legs(c,request,bucket,population=forward_bookings)
                native=contract['baseCurrencyId']
                amounts=dict(referenceNotional=contract['baseAmount'])
                for role,field in (('BASE','base'),('QUOTE','quote')):
                    currency=contract[field+'CurrencyId'];amount=contract[field+'Amount']
                    base=None;conversion=None
                    try:base,conversion=converted(amount,currency)
                    except ValueError as exc:issues[field+'LegFx']=str(exc)
                    if conversion:selections[field+'LegFx']=conversion
                    legs.append(dict(role=role,localAmount=amount,currency=currencies.get(currency),strategyAmount=base,
                        strategyCurrency=currencies.get(request.reporting_currency_id),status='AVAILABLE' if base is not None else 'LOCAL_ONLY'))
                selections['forwardContract']=contract['bookings']
                issues['marketValue']='Discounted contract MTM is unavailable: contractual currency legs and undiscounted rate-difference P&L are not discounted market value.'
                if request.closing_cutoff.date()>contract['maturityDate']:
                    issues['lifecycle']='Past maturity with open contractual obligations: Ops lifecycle closure is required; no cash or automatic zero is inferred.'
                route='FX_FORWARD_CONTRACTUAL_LEGS'
            elif product=='FUTURE':
                from security_master_schema.booking_conventions import FutureConvention
                conventions=[FutureConvention.model_validate(t.get('convention') or {}) for t in terms]
                cv=conventions[0]
                economics={evidence_hash(v.model_dump(mode='json',exclude={'source_reference','effective_from'})) for v in conventions}
                parents={t.get('instrumentId') for t in terms}
                if len(economics)!=1 or len(parents)!=1 or None in parents:
                    raise ValueError('One compatible frozen dated futures contract is required')
                parent=next(iter(parents))
                if any(t.get('listingId')!=str(key.subject_id) or t.get('kind')!='FUTURE' for t in terms):
                    raise ValueError('Frozen futures listing identity differs from the position')
                if cv.settlement_method!='CASH' or cv.price_basis!='INDEX_POINTS':
                    raise ValueError('Only linear cash-settled index-futures measures are enabled')
                if (key.quantity_unit!='CONTRACTS' or native!=cv.price_currency_id
                    or key.unit_multiplier!=cv.monetary_multiplier or key.quote_factor!=cv.quote_factor):
                    raise ValueError('Frozen futures quantity/currency/monetary multiplier/quote divisor mismatch')
                day=request.closing_cutoff.date()
                if any(day<v.effective_from for v in conventions):raise ValueError('Futures convention is not effective on the requested date')
                if day>cv.final_settlement_date:
                    raise ValueError('Open futures exposure after final settlement requires Ops lifecycle closure; no automatic zero is assumed')
                price,_=selected(key.subject_id,'FUTURE',native,'futuresPrice',(
                    ('CONTRACT_INSTRUMENT_ID',parent),('FUTURE_PRICE_BASIS','INDEX_POINTS')))
                if price is not None:
                    factors=selections['futuresPrice']['dimensions'].get('QUOTE_FACTOR',[])
                    if len(factors)!=1 or D(factors[0])!=cv.quote_factor:
                        price=None;issues['futuresPrice']='Futures price quote divisor differs from the frozen contract'
                amounts=linear_future(bucket.closing_quantity,price,cv.monetary_multiplier,cv.quote_factor,allow_negative=cv.allow_negative_price)
                selections['futureConvention']=dict(contractId=parent,convention=cv.model_dump(mode='json',by_alias=True),
                    quantityBasis='CANONICAL_CONTRACTS',listingMultiplierApplied=False,referenceDefinition='CURRENT_MARKET_NOTIONAL')
                issues['marketValue']='Contract MTM is unavailable without a clearing/variation-margin settlement boundary and outstanding-value evidence; market notional is not a NAV asset or an assumed zero.'
                if request.closing_cutoff>cv.last_trading_at_utc:
                    issues['lifecycle']='Last trading has passed; only an explicit lifecycle booking closes exposure. No delivery or cash is inferred.'
                route='FUTURE_CURRENT_NOTIONAL'
            elif product=='SWAP':
                generic=[t.get('swapDetails',{}).get('genericTerms') for t in terms]
                if not generic or any(g is None for g in generic) or len({evidence_hash(g) for g in generic})!=1:
                    raise ValueError('One compatible frozen generic swap contract is required')
                g=generic[0]
                from security_master_schema.swap_terms import GenericSwapTerms
                GenericSwapTerms.model_validate(g)
                cv=terms[0].get('convention') or {}
                if (cv.get('kind')!='SWAP' or cv.get('quantityUnit')!=key.quantity_unit
                    or g.get('quantityUnit','NOMINAL')!=key.quantity_unit
                    or cv.get('priceBasis')!=('SWAP_VALUE_PER_UNIT' if key.quantity_unit=='UNITS' else 'SWAP_VALUE_PER_NOTIONAL')):
                    raise ValueError('Frozen swap quantity and quote basis differ')
                if any(g.get(field) not in (None,'AT_MATURITY') for field in ('performanceResetFrequency','fundingResetFrequency','fundingPaymentFrequency')):
                    raise ValueError('Interim-reset/payment swaps are not supported by this measure preview')
                facts=terms[0]['swapDetails'].get('sourceFacts',{})
                if facts.get('performanceIndex'):
                    under_kind='INDEX';under_currency=UUID(facts['performanceIndex']['base_currency_id']) if facts['performanceIndex'].get('base_currency_id') else None
                else:
                    raise ValueError('This slice supports delta-one index swaps; other underlying unit/corporate-action conventions and autocalls are not enabled')
                if str(facts['performanceIndex']['index_node_id'])!=g['performanceReferenceId']:
                    raise ValueError('Frozen performance index differs from the swap contract')
                if key.unit_multiplier!=1 or str(native)!=g['quoteCurrencyId'] or key.quote_factor!=D(g['quoteFactor']):raise ValueError('Frozen whole-swap quote units/currency/factor mismatch')
                is_unit=key.quantity_unit=='UNITS'
                expected='WHOLE_SWAP_MTM_PER_UNIT' if is_unit else 'WHOLE_SWAP_MTM_PER_NOTIONAL'
                swap_price,_=selected(key.subject_id,'SWAP',native,'swapMark',(('SWAP_PRICE_BASIS',expected),))
                if swap_price is not None:
                    factors=selections['swapMark']['dimensions'].get('QUOTE_FACTOR',[])
                    if len(factors)!=1 or D(factors[0])!=key.quote_factor:
                        swap_price=None;issues['swapMark']='Whole-swap mark quote divisor differs from booked convention'
                if is_unit:
                    underlying,_=selected(UUID(g['performanceReferenceId']),under_kind,under_currency,'underlyingPrice')
                    if underlying is not None:
                        exposure_currency=selections['underlyingPrice']['selection']['currency_id']
                    if under_currency is None:raise ValueError('Frozen underlying currency is missing')
                    amounts=unit_swap(bucket.closing_quantity,D(g['notionalPerUnit']),D(g['leverage']),underlying,swap_price,key.quote_factor,orientation=g['performanceDirection'])
                elif key.quantity_unit=='NOMINAL':
                    amounts=nominal_swap(bucket.closing_quantity,swap_price,key.quote_factor)
                    issues['economicExposure']='Nominal swap equivalent units/reset reference price is not recorded'
                else:raise ValueError('Unsupported swap quantity basis')
                selections['swapTerms']=dict(terms=g,termsFingerprint=terms[0].get('termsFingerprint'),underlyingUnitConvention='Native canonical share/index unit; no extra multiplier inferred')
                route='WHOLE_SWAP_MARK'
            else:raise ValueError('Measures are not implemented for '+product)
        except (ValueError,KeyError,TypeError,ArithmeticError) as exc:
            issues['contract']=str(exc);amounts={};legs=[]
        measures={}
        for name in ('referenceNotional','economicExposure','marketValue'):
            amount=amounts.get(name);currency=exposure_currency if name=='economicExposure' else native
            conversion=None;base=None
            if amount is not None:
                try:base,conversion=converted(amount,currency)
                except ValueError as exc:issues[name+'Fx']=str(exc)
            measures[name]=dict(localAmount=amount,currency=currencies.get(currency),strategyAmount=base,
                strategyCurrency=currencies.get(request.reporting_currency_id),status='AVAILABLE' if amount is not None and base is not None else 'LOCAL_ONLY' if amount is not None else 'UNAVAILABLE')
            if conversion:selections[name+'Fx']=conversion
        if legs:
            measures['economicExposure'].update(localAmount=None,currency=None,strategyAmount=None,
                status='MULTI_CURRENCY',representation='CONTRACTUAL_CURRENCY_LEGS',legs=legs)
            measures['marketValue']['currency']=currencies.get(key.currency_id)
        for name,measure in measures.items():
            reason=measure_reason(product,name,measure['status'],contract_invalid='contract' in issues,nominal=key.quantity_unit=='NOMINAL')
            if reason:measure['reasonCode']=reason
        evidence=dict(method='position-measures-v1',route=route,positionKey=asdict(key),quantity=bucket.closing_quantity,
            asOf=request.closing_cutoff.date(),informationCutoff=request.information_cutoff,policyId=request.policy_id,
            bookingTradeIds=bucket.trade_ids,projectionHash=projection.input_hash,selections=selections,
            cleanMarketValue=amounts.get('cleanMarketValue'),accruedBalance=amounts.get('accruedBalance'),issues=issues)
        results.append(row|dict(measures=measures,evidence=evidence,evidenceHash=evidence_hash(evidence)))
    return canonical_payload(dict(method='position-measures-v1',status='PREVIEW_NOT_PUBLISHED',asOf=request.closing_cutoff.date(),
        informationCutoff=request.information_cutoff,policyId=request.policy_id,reportingCurrency=currencies.get(request.reporting_currency_id),items=results))
