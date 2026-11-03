import Link from 'next/link';
import type {components} from 'api-contracts';
import {parseBookingDecimal,formatBookingDecimal} from '@/lib/booking-decimal';
type Terms=components['schemas']['RateSwapTerms-Input']|components['schemas']['RateSwapTerms-Output'];

function quantity(value:string){
  const parsed=parseBookingDecimal(value),raw=parsed?formatBookingDecimal(parsed.value,parsed.scale):value;
  const [integer,fraction]=raw.split('.');return integer.replace(/\B(?=(\d{3})+(?!\d))/g,',')+(fraction?`.${fraction}`:'');
}
function spread(value:string){const p=parseBookingDecimal(value);return p?`${formatBookingDecimal(p.value*BigInt(10000),p.scale)} bps`:value;}

export function RateSwapTermsFacts({terms,labels={}}:{terms:Terms;labels?:Record<string,string>}){
  const named=(id:string)=>labels[id]??id;
  return <section className="detail-card"><h2>Rate-exchange swap terms</h2><dl className="futures-facts">
    {terms.tenantIdentifier?<><dt>Tenant identifier</dt><dd>{terms.tenantIdentifier}</dd></>:null}
    <dt>Contractual booking basis</dt><dd>{quantity(String(terms.contractualNotional))} {named(terms.notionalCurrencyId)}</dd>
    {terms.quantityUnit==='UNITS'?<><dt>Contractual units / reference notional per unit</dt><dd>{quantity(String(terms.contractualUnits))} / {quantity(String(terms.notionalPerUnit))}</dd></>:null}
    <dt>Effective / maturity dates</dt><dd>{terms.effectiveDate} / {terms.maturityDate}</dd>
  </dl><div className="configuration-grid">{terms.legs.map((leg,index)=><section className="detail-card" key={index}><h3>{leg.direction==='PAY'?'Pay leg':'Receive leg'}</h3><dl className="futures-facts">
    <dt>Floating reference</dt><dd><Link href={`/api/reference-nodes/search?${new URLSearchParams({q:leg.rateReferenceId,node_type:'RATE_INDEX',reference_level:'ECONOMIC'})}`}>{named(leg.rateReferenceId)}</Link></dd>
    <dt>Contractual leg notional</dt><dd>{quantity(String(leg.contractualNotional))} {named(leg.currencyId)}</dd>
    <dt>Spread over reference</dt><dd>{spread(String(leg.spread))}</dd>
    <dt>Day count</dt><dd>{named(leg.dayCountConventionId)}</dd>
    <dt>Reset / payment frequency</dt><dd>{leg.resetFrequency} / {leg.paymentFrequency}</dd>
    <dt>Interest calculation</dt><dd>{leg.interestCalculationMethod}</dd>
    <dt>Observation conventions</dt><dd>{leg.observationDescription}</dd>
    {leg.resetScheduleDescription?<><dt>Reset schedule evidence</dt><dd>{leg.resetScheduleDescription}</dd></>:null}
    {leg.paymentScheduleDescription?<><dt>Payment schedule evidence</dt><dd>{leg.paymentScheduleDescription}</dd></>:null}
  </dl></section>)}</div><dl className="futures-facts"><dt>Principal exchange</dt><dd>{terms.principalExchange}{terms.principalExchangeDescription?` — ${terms.principalExchangeDescription}`:''}</dd>
    <dt>Whole-swap quote</dt><dd>{terms.quantityUnit==='UNITS'?'Per unit':'Per booked nominal'} · {named(terms.quoteCurrencyId)} · divisor {String(terms.quoteFactor)}</dd>
    <dt>Source / confirmation evidence</dt><dd>{terms.sourceReference}</dd></dl>
    <p>This two-leg swap has its own bank price series. Signed booked quantity × whole-swap quote ÷ quote divisor gives its entry reference value. Partial bookings scale the contractual leg notionals. SELL reverses the canonical holder orientation.</p>
    <p>Leg terms are retained evidence. No payments, principal exchanges, curve valuation or extra currency positions are generated.</p></section>;
}
