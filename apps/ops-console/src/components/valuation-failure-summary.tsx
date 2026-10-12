type FailureEvent={event_code:string;details:unknown};

const explanations:Record<string,{title:string;meaning:string;action:string;href:string;link:string}>={
 NO_VALID_ENTITLEMENT:{title:'Valuation permission is missing',
  meaning:'The selected market data has no valid recorded permission for this tenant to use it in valuation. This is a permission check, not proof that prices are missing.',
  action:'Review the permitted uses, automated-calculation permissions and tenant coverage for the data source. Only authorize valuation where the supporting evidence permits it.',
  href:'/market-data/sources',link:'Review data sources and permissions'},
 NO_MATCHING_POLICY_RULE:{title:'The pricing policy does not cover this instrument',
  meaning:'No applicable rule was found in the selected policy version. The available prices have not yet passed price selection.',
  action:'Check the selected policy version and its instrument, listing and exchange coverage.',
  href:'/market-data/policies',link:'Review pricing policies'},
 NO_ELIGIBLE_OBSERVATION:{title:'No price meets the policy requirements',
  meaning:'A rule applies, but no eligible price satisfies the selection checks. Prices may exist but differ in date, adjustment basis, closing designation or permitted use.',
  action:'Compare the requirements below with the available data, then review the policy and source permissions. Do not relabel prices merely to bypass the check.',
  href:'/market-data/policies',link:'Review pricing policies'},
};

/** Explain recorded failures only; never infer a financial result or grant rights. */
export function ValuationFailureSummary({events}:{events:FailureEvent[]}){
 const failure=[...events].reverse().find(event=>event.event_code==='FAILED');
 if(!failure)return null;
 const data=failure.details&&typeof failure.details==='object'?failure.details as Record<string,unknown>:{};
 const reason=typeof data.reason==='string'?data.reason:'';
 const code=reason.match(/^Input selection blocked: ([A-Z_]+)(?:\.|$)/)?.[1];
 const explanation=code?explanations[code]:undefined;
 // Legacy run evidence stores context in a message. Parse only its known shape;
 // otherwise preserve the explanation intact rather than guess at the cause.
 const context=reason.match(/^Input selection blocked: [A-Z_]+\. (.+?) \(([0-9a-f-]{36})\) on (\d{4}-\d{2}-\d{2}): (.*)$/i);
 const diagnostic=context?.[4];
 const requirements=diagnostic?.match(/^requires (.*?)(?:;|$)/)?.[1];
 const available=diagnostic?.match(/; available (.*?)(?:;|$)/)?.[1];
 return <section className="error-panel" aria-label="Valuation failure explanation" role="status">
  <h3>{explanation?.title??'Valuation could not be calculated'}</h3>
  {explanation?<p>{explanation.meaning}</p>:null}
  {context?<dl><dt>Affected instrument</dt><dd>{context[1]}</dd><dt>Price date</dt><dd>{context[3]}</dd>
   {requirements?<><dt>Policy requires</dt><dd>{requirements}</dd></>:null}
   {available?<><dt>Available price types</dt><dd>{available}</dd></>:null}</dl>:null}
  <p>{explanation?.action??'Review the recorded reason and technical details before starting another calculation.'}</p>
  {explanation?<p><a href={explanation.href}>{explanation.link}</a>{code==='NO_ELIGIBLE_OBSERVATION'?<> · <a href="/market-data/sources">Review data sources and permissions</a></>:null}</p>:null}
  <details><summary>Recorded reason</summary><p>{reason||'No explanatory reason was recorded. Inspect the operational log.'}</p></details>
 </section>;
}
