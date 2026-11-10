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
from .position_measures import cash_security,bond,unit_swap,nominal_swap,linear_future,scaled,vanilla_option
from .service import _selection
from .price_inputs import MissingPriceInput
from .fx import resolve_fx
from positions.reconstruction import key_identity
from security_master_schema.cash_products import QUOTED_WRAPPERS


def measure_reason(product,name,status,*,contract_invalid=False,nominal=False):
    """Presentation metadata only; never infer support by parsing error prose."""
    if status in {'AVAILABLE','MULTI_CURRENCY'}:return None
    if status=='LOCAL_ONLY':return 'FX_UNAVAILABLE'
    if product not in {'EQUITY','ETF','ETP','FUND','BOND','FUTURE','FX_FORWARD','SWAP','ACTIVELY_MANAGED_CERTIFICATE','OPTION','STRUCTURED_PRODUCT','DIGITAL_ASSET'}|QUOTED_WRAPPERS:return 'NOT_SUPPORTED_YET'
    if contract_invalid:return 'INVALID_CONTRACT'
    if name=='marketValue' and product in {'FUTURE','FX_FORWARD'}:return 'NOT_SUPPORTED_YET'
    if product in {'OPTION','STRUCTURED_PRODUCT'} and name=='economicExposure':return 'NOT_SUPPORTED_YET'
    if product=='SWAP' and nominal and name=='economicExposure':return 'NOT_SUPPORTED_YET'
    return 'MISSING_INPUT'


def preview_measures(c,request,projection,descriptions,rows):
    from .measure_contracts import MeasureBookings,option_terms,note_terms,swap_terms
    currencies=dict(c.execute(select(m.currency.c.currency_id,m.currency.c.currency_code)).all())
    buckets={key_identity(b.key):b for b in projection.buckets}
    cache={};fx_cache={};results=[];bond_stocks=None;note_stocks=None
    contracts=MeasureBookings(c,request,[buckets[row['positionId']] for row in rows],descriptions)
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
        except MissingPriceInput as missing:
            # Daily P&L retains these as population gaps. A read-only measure
            # preview instead marks this one input unavailable; permissions and
            # other unexpected exceptions must keep their existing behavior.
            error=ValueError(f'Required price is unavailable under the selected policy ({missing.selection.exception_code or missing.selection.status})')
            cache[key]=error
            raise error from missing
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
        selections={};issues={};amounts={};legs=[];route=None;native=key.currency_id;exposure_currency=native;reference_currency=native;measure_bases={};unsupported=set()
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
            if product in {'OPTION','STRUCTURED_PRODUCT','FUTURE','SWAP'}:contracts.validate(bucket)
            if product in {'EQUITY','ETF','ETP','FUND','DIGITAL_ASSET'}|QUOTED_WRAPPERS:
                subject=key.subject_id
                if product=='FUND':
                    parents={p.get('instrumentId') or (p.get('valuationConventions') or {}).get('instrumentId') for p in proofs}
                    if len(parents)!=1 or None in parents:raise ValueError('Unique frozen canonical fund NAV identity required')
                    subject=UUID(next(iter(parents)))
                    if key.unit_multiplier!=1 or key.quote_factor!=1:raise ValueError('Fund listing-to-NAV normalization is not supported')
                price,_=selected(subject,product,native,'securityPrice')
                amounts=cash_security(bucket.closing_quantity,price,key.unit_multiplier,key.quote_factor)
                route='SECURITY_PRICE'
            elif product=='ACTIVELY_MANAGED_CERTIFICATE':
                from security_master_schema.amc_quotation import matching_quotation
                conventions=[t.get('convention') or {} for t in terms]
                basis=matching_quotation(conventions,key.quantity_unit,key.unit_multiplier,key.quote_factor)
                price,_=selected(key.subject_id,product,native,'amcPrice',(('AMC_PRICE_BASIS',basis),))
                amounts=cash_security(bucket.closing_quantity,price,key.unit_multiplier,key.quote_factor)
                route='AMC_'+basis
                selections['amcQuotation']=dict(priceBasis=basis,quantityUnit=key.quantity_unit,
                    multiplier=key.unit_multiplier,quoteDivisor=key.quote_factor,
                    reportingConvention='FUNDED_SECURITY_MARKET_VALUE_PROXY_NO_LOOKTHROUGH')
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
                        from .bond_measure_balances import load_measure_stocks,position_stock
                        same_instrument=[b for b in projection.buckets if b.closing_quantity and descriptions[b.trade_ids[0]]['instrumentId']==row['instrumentId']]
                        if bond_stocks is None:bond_stocks=load_measure_stocks(c,request)
                        coupon_types={t.get('couponType') or (t.get('convention') or {}).get('couponType')
                            or (p.get('valuationConventions') or {}).get('couponType') for t,p in zip(terms,proofs)}
                        balance,stock_proof=position_stock(bond_stocks,row['instrumentId'],native,face,
                            compatible_positions=len(same_instrument),zero_coupon=coupon_types=={'ZERO'})
                        selections['accruedBalance']=stock_proof
                    except ValueError as exc:issues['accruedBalance']=str(exc)
                amounts=bond(face,dirty=dirty,clean=clean,accrued=balance,quote_factor=key.quote_factor);route=amounts.pop('route')
                if dirty is not None:issues.pop('dirtyPrice',None)
            elif product=='FX_FORWARD':
                from .forward_measures import contractual_legs
                contract=contractual_legs(c,request,bucket,population=forward_bookings)
                native=contract['baseCurrencyId']
                reference_currency=native
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
                from security_master_schema.future_economics import require_linear_future
                require_linear_future(cv)
                if (key.quantity_unit!='CONTRACTS' or native!=cv.price_currency_id
                    or key.unit_multiplier!=cv.monetary_multiplier or key.quote_factor!=cv.quote_factor):
                    raise ValueError('Frozen futures quantity/currency/monetary multiplier/quote divisor mismatch')
                day=request.closing_cutoff.date()
                if any(day<v.effective_from for v in conventions):raise ValueError('Futures convention is not effective on the requested date')
                if day>cv.final_settlement_date:
                    raise ValueError('Open futures exposure after final settlement requires Ops lifecycle closure; no automatic zero is assumed')
                price,_=selected(key.subject_id,'FUTURE',native,'futuresPrice',(
                    ('CONTRACT_INSTRUMENT_ID',parent),('FUTURE_PRICE_BASIS',cv.price_basis)))
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
            elif product=='OPTION':
                t,reference_currency=option_terms(bucket,terms,currencies,request.closing_cutoff.date())
                canonical=UUID(t['instrumentId'])
                def number(value):
                    result=format(D(value),'f')
                    return result.rstrip('0').rstrip('.') if '.' in result else result
                premium,_=selected(canonical,'OPTION',native,'optionPremium',(('OPTION_PRICE_BASIS','PREMIUM_POINTS'),
                    ('PREMIUM_MULTIPLIER',number(key.unit_multiplier)),('QUOTE_FACTOR',number(key.quote_factor)),('QUANTITY_UNIT','CONTRACTS')))
                amounts=vanilla_option(bucket.closing_quantity,premium,key.unit_multiplier,key.quote_factor,D(t['strike']),D(t['deliverableUnits']))
                measure_bases=dict(referenceNotional='STRIKE_NOTIONAL',marketValue='OPTION_PREMIUM_VALUE')
                unsupported.add('economicExposure');issues['economicExposure']='Option risk exposure requires governed delta and underlying units; premium and strike notional are not delta exposure.'
                selections['optionContract']={k:t[k] for k in ('optionType','strike','strikeCurrency','deliverableUnits','premiumMultiplier','quoteFactor','expiryDate','underlyingId')}
                route='OPTION_PREMIUM_VALUE'
            elif product=='STRUCTURED_PRODUCT':
                cv=note_terms(bucket,terms,request.closing_cutoff.date())
                from .structured_note_inputs import validate_note_divisor
                price_basis=cv['priceBasis'];accrual=cv['accrual'];dirty=None;clean=None;balance=None
                def note_price(accrual_basis,role):
                    value,_=selected(key.subject_id,product,native,role,(('STRUCTURED_PRICE_BASIS',price_basis),('STRUCTURED_ACCRUAL_BASIS',accrual_basis)))
                    if value is not None:
                        try:validate_note_divisor(selections[role]['dimensions'].get('QUOTE_FACTOR',[]),key.quote_factor)
                        except ValueError as exc:issues[role]=str(exc);return None
                    return value
                face=scaled(bucket.closing_quantity,key.unit_multiplier)
                if accrual=='NONE':
                    whole=note_price('NONE','notePrice')
                    market=cash_security(bucket.closing_quantity,whole,key.unit_multiplier,key.quote_factor)['marketValue']
                    route='NOTE_WHOLE_VALUE'
                else:
                    dirty=note_price('DIRTY','noteDirtyPrice')
                    if dirty is None:
                        clean=note_price('CLEAN','noteCleanPrice')
                        try:
                            from .note_measure_balances import load_note_measure_stocks,assessed_note_stock
                            matching=[b for b in projection.buckets if b.closing_quantity and descriptions[b.trade_ids[0]]['instrumentId']==row['instrumentId']]
                            if note_stocks is None:note_stocks=load_note_measure_stocks(c,request)
                            stock_nominal=face
                            if price_basis=='UNIT_PRICE':
                                if cv.get('denomination') is None:raise ValueError('CLEAN unit-price note stock requires an explicit nominal mapping')
                                stock_nominal=scaled(bucket.closing_quantity,D(cv['denomination']))
                            balance,proof=assessed_note_stock(note_stocks,row['instrumentId'],native,stock_nominal,compatible_positions=len(matching))
                            selections['accruedBalance']=proof
                        except ValueError as exc:issues['accruedBalance']=str(exc)
                    quoted=bond(face,dirty=dirty,clean=clean,accrued=balance,quote_factor=key.quote_factor)
                    market=quoted['marketValue'];route='NOTE_'+quoted['route']
                    if dirty is not None:issues.pop('noteDirtyPrice',None)
                reference=face if price_basis=='PCT_OF_PAR' else market
                amounts=dict(referenceNotional=reference,economicExposure=None,marketValue=market)
                measure_bases=dict(referenceNotional='CONTRACTUAL_FACE' if price_basis=='PCT_OF_PAR' else 'FUNDED_MARKET_VALUE_PROXY',marketValue='FUNDED_NOTE_VALUE')
                unsupported.add('economicExposure');issues['economicExposure']='Structured-note underlying risk exposure requires governed payoff sensitivities/look-through; funded value is not delta exposure.'
                selections['noteConvention']=cv
            elif product=='SWAP':
                g=swap_terms(bucket,terms,request.closing_cutoff.date())
                is_unit=key.quantity_unit=='UNITS'
                expected='WHOLE_SWAP_MTM_PER_UNIT' if is_unit else 'WHOLE_SWAP_MTM_PER_NOTIONAL'
                swap_price,_=selected(key.subject_id,'SWAP',native,'swapMark',(('SWAP_PRICE_BASIS',expected),))
                if swap_price is not None:
                    factors=selections['swapMark']['dimensions'].get('QUOTE_FACTOR',[])
                    if len(factors)!=1 or D(factors[0])!=key.quote_factor:
                        swap_price=None;issues['swapMark']='Whole-swap mark quote divisor differs from booked convention'
                    units=selections['swapMark']['dimensions'].get('QUANTITY_UNIT')
                    if units is not None and units!=[key.quantity_unit]:
                        swap_price=None;issues['swapMark']='Whole-swap mark quantity basis differs from booked convention'
                amounts=nominal_swap(g.booked_reference_notional(bucket.closing_quantity),None,key.quote_factor)
                amounts['marketValue']=None if swap_price is None else scaled(bucket.closing_quantity,swap_price,quote_factor=key.quote_factor)
                measure_bases=dict(referenceNotional='CONTRACTUAL_REFERENCE',marketValue='WHOLE_SWAP_VALUE')
                facts=terms[0]['swapDetails'].get('sourceFacts',{})
                index=facts.get('performanceIndex')
                interim=any(getattr(g,field,None) not in (None,'AT_MATURITY') for field in ('performance_reset_frequency','funding_reset_frequency','funding_payment_frequency'))
                if is_unit and index and hasattr(g,'performance_reference_id') and not interim:
                    if str(index['index_node_id'])!=str(g.performance_reference_id):raise ValueError('Frozen performance index differs from the swap contract')
                    underlying_currency=UUID(index['base_currency_id']) if index.get('base_currency_id') else None
                    if underlying_currency is not None:
                        underlying,_=selected(g.performance_reference_id,'INDEX',underlying_currency,'underlyingPrice')
                        exposure_currency=underlying_currency
                        amounts['economicExposure']=unit_swap(bucket.closing_quantity,g.notional_per_unit,g.leverage,underlying,None,key.quote_factor,orientation=g.performance_direction)['economicExposure']
                    else:issues['economicExposure']='Frozen underlying currency is missing'
                else:
                    unsupported.add('economicExposure')
                    issues['economicExposure']='Underlying/reset or rate-risk exposure is not modelled; contractual notional and whole-swap market value remain separate.'
                selections['swapTerms']=dict(terms=g.model_dump(mode='json',by_alias=True),termsFingerprint=terms[0].get('termsFingerprint'),underlyingUnitConvention='Native canonical index units only; no inferred reset or risk sensitivity')
                route='WHOLE_SWAP_MARK'
            else:raise ValueError('Measures are not implemented for '+product)
        except (ValueError,KeyError,TypeError,ArithmeticError) as exc:
            issues['contract']=str(exc);amounts={};legs=[]
        measures={}
        for name in ('referenceNotional','economicExposure','marketValue'):
            amount=amounts.get(name);currency=exposure_currency if name=='economicExposure' else reference_currency if name=='referenceNotional' else native
            conversion=None;base=None
            if amount is not None:
                try:base,conversion=converted(amount,currency)
                except ValueError as exc:issues[name+'Fx']=str(exc)
            measures[name]=dict(localAmount=amount,currency=currencies.get(currency),strategyAmount=base,
                strategyCurrency=currencies.get(request.reporting_currency_id),status='AVAILABLE' if amount is not None and base is not None else 'LOCAL_ONLY' if amount is not None else 'UNAVAILABLE')
            if name in measure_bases:measures[name]['basis']=measure_bases[name]
            if conversion:selections[name+'Fx']=conversion
        if legs:
            measures['economicExposure'].update(localAmount=None,currency=None,strategyAmount=None,
                status='MULTI_CURRENCY',representation='CONTRACTUAL_CURRENCY_LEGS',legs=legs)
            measures['marketValue']['currency']=currencies.get(key.currency_id)
        for name,measure in measures.items():
            reason=measure_reason(product,name,measure['status'],contract_invalid='contract' in issues,nominal=key.quantity_unit=='NOMINAL')
            if name in unsupported and measure['status']=='UNAVAILABLE' and 'contract' not in issues:reason='NOT_SUPPORTED_YET'
            if reason:measure['reasonCode']=reason
        evidence=dict(method='position-measures-v1',route=route,positionKey=asdict(key),quantity=bucket.closing_quantity,
            asOf=request.closing_cutoff.date(),informationCutoff=request.information_cutoff,policyId=request.policy_id,
            bookingTradeIds=bucket.trade_ids,projectionHash=projection.input_hash,selections=selections,
            cleanMarketValue=amounts.get('cleanMarketValue'),accruedBalance=amounts.get('accruedBalance'),issues=issues)
        results.append(row|dict(measures=measures,evidence=evidence,evidenceHash=evidence_hash(evidence)))
    return canonical_payload(dict(method='position-measures-v1',status='PREVIEW_NOT_PUBLISHED',asOf=request.closing_cutoff.date(),
        informationCutoff=request.information_cutoff,policyId=request.policy_id,reportingCurrency=currencies.get(request.reporting_currency_id),items=results))
