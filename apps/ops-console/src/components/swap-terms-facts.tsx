import Link from 'next/link';
import type {components} from 'api-contracts';
type Terms=components['schemas']['GenericSwapTerms-Input']|components['schemas']['GenericSwapTerms-Output'];
export function SwapTermsFacts({terms,labels={}}:{terms:Terms;labels?:Record<string,string>}) {
  const named=(id:string)=>labels[id]??id;
  const reference=(id:string,type:string)=><Link href={`/api/reference-nodes/search?${new URLSearchParams({q:id,node_type:type,reference_level:'ECONOMIC'})}`}>{named(id)}</Link>;
  return <section className="detail-card"><h2>Performance swap terms</h2><dl className="futures-facts">
    {terms.tenantIdentifier?<><dt>Tenant identifier</dt><dd>{terms.tenantIdentifier}</dd></>:null}
    <dt>Performance reference</dt><dd>{reference(terms.performanceReferenceId,'INSTRUMENT,INDEX')}</dd>
    <dt>Contractual notional</dt><dd>{String(terms.contractualNotional)} {named(terms.notionalCurrencyId)}</dd>
    <dt>Effective / maturity dates</dt><dd>{terms.effectiveDate} / {terms.maturityDate}</dd>
    <dt>Performance direction</dt><dd>{terms.performanceDirection} from the contract holder perspective</dd>
    <dt>Return basis / governed profile</dt><dd>{terms.returnBasis} / {named(terms.returnProfileId)}</dd>
    <dt>Leverage</dt><dd>{String(terms.leverage)}×</dd>
    <dt>Financing treatment</dt><dd>{terms.financingTreatment}</dd>
    <dt>Performance reset frequency</dt><dd>{terms.performanceResetFrequency}</dd>
    {terms.performanceScheduleDescription?<><dt>Performance schedule evidence</dt><dd>{terms.performanceScheduleDescription}</dd></>:null}
    <dt>Funding reference</dt><dd>{terms.fundingReferenceId?reference(terms.fundingReferenceId,'RATE_INDEX'):'No separate funding leg'}</dd>
    {terms.fundingReferenceId?<>
      <dt>Funding direction</dt><dd>{terms.performanceDirection==='RECEIVE'?'PAY':'RECEIVE'} from the contract holder perspective</dd>
      <dt>Funding spread (decimal rate)</dt><dd>{String(terms.fundingSpread)}</dd>
      <dt>Funding notional basis</dt><dd>{terms.fundingNotionalBasis}</dd>
      <dt>Day-count convention</dt><dd>{terms.dayCountConventionId?named(terms.dayCountConventionId):'—'}</dd>
      <dt>Interest calculation method</dt><dd>{terms.interestCalculationMethod}</dd>
      {terms.fundingObservationDescription?<><dt>Observation conventions</dt><dd>{terms.fundingObservationDescription}</dd></>:null}
      <dt>Funding reset / payment frequencies</dt><dd>{terms.fundingResetFrequency} / {terms.fundingPaymentFrequency}</dd>
      {terms.fundingResetScheduleDescription?<><dt>Funding reset schedule evidence</dt><dd>{terms.fundingResetScheduleDescription}</dd></>:null}
      {terms.fundingPaymentScheduleDescription?<><dt>Funding payment schedule evidence</dt><dd>{terms.fundingPaymentScheduleDescription}</dd></>:null}
      {terms.additionalFundingAcknowledged?<><dt>Additional funding acknowledged</dt><dd>Yes — {terms.additionalFundingEvidence}</dd></>:null}
    </>:null}
    <dt>Reference redemption rule</dt><dd>{terms.redemptionRule==='TERMINATE'?'Terminate economic exposure at reference maturity / autocall':terms.continuationDescription}</dd>
    <dt>Whole-swap quote convention</dt><dd>SWAP_VALUE_PER_NOTIONAL · {named(terms.quoteCurrencyId)} · divisor {String(terms.quoteFactor)}</dd>
    <dt>Source / confirmation evidence</dt><dd>{terms.sourceReference}</dd>
  </dl><p>Booked nominal is editable per trade and may differ from contractual notional. The whole-swap quote includes contractual leverage and funding effects: signed booked nominal × execution quote ÷ quote divisor. Leverage is not applied again.</p><p>Frequency and redemption terms record the contract. No event schedules, cashflows, termination processing or valuation are generated. Final payment may follow exposure termination.</p></section>;
}
