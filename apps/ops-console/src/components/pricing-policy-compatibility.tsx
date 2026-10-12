import type {components} from 'api-contracts';
type Report=components['schemas']['PolicyCompatibility'];
type Data=components['schemas']['PolicyDataOptions'];

const labels:Record<string,string>={CLOSE:'Closing price',ADJUSTED_CLOSE:'Adjusted closing price',OFFICIAL_CLOSE:'Designated official closing price',RAW:'Unadjusted',SPLIT_ADJUSTED:'Split-adjusted',VENDOR_ADJUSTED:'Provider-adjusted',TOTAL_RETURN:'Total return',VALUATION:'Valuation',INTERNAL_REPORTING:'Internal reporting',FX_SPOT:'Spot FX rate',NAV:'Net asset value'};
function describe(code:string){return labels[code]??code;}
const closingMethods:Record<string,string>={EXCHANGE_OFFICIAL:'Exchange-official',LAST_TRADE:'Last trade',PROVIDER_DEFINED:'Provider-defined',UNKNOWN:'Unknown closing method'};

export function PolicyCompatibilityReport({report}:{report:Report}){
 return <section className="history-panel" role="status" aria-live="polite"><h3>{report.status==='ACTION_REQUIRED'?'Configuration needs attention':'Configuration has compatible recorded data'}</h3><p>{report.scope}</p>
  {report.rules.map(rule=><article key={`${rule.origin}-${rule.ruleSequence}`}><h4>{rule.origin==='DEFAULT'?'Default':'Explicit rule'} {rule.ruleSequence}</h4>
   <p>{rule.matchingSeriesCount} matching stored series · {rule.eligibleSeriesCount} eligible for valuation use and source priority.</p>
   <p>Known sources in this scope: {rule.sourceLabels.join(', ')||'None'}</p>
   {rule.issues.length?<ul>{rule.issues.map(issue=><li key={issue.code}>{issue.message} <strong>Next action:</strong> {issue.action}</li>)}</ul>:null}
  </article>)}
 </section>;
}

export function PolicySourceProfiles({data}:{data:Data}){
 return <section className="history-panel"><h3>Available source definitions</h3><p>These are the definitions actually stored and visible to this tenant—not a promise of complete date coverage.</p>
  {data.sources.length?data.sources.map(source=><details key={source.datasetId}><summary>{source.provider} · {source.label}</summary>
   <p>Recorded permitted use: {source.purposes.map(describe).join(', ')||'None'}. Automated calculation permission: {source.nonDisplayAllowed?'Recorded':'Not available'}. Coverage may be limited to particular series or packages.</p>
   <ul>{source.priceProfiles.map(profile=><li key={`${profile.seriesType}-${profile.valueBasis}-${profile.closingMethod??'UNKNOWN'}`}>{describe(profile.seriesType)} / {describe(profile.valueBasis)}{profile.seriesType==='CLOSE'?` · ${closingMethods[profile.closingMethod??'UNKNOWN']??profile.closingMethod}`:''} · {profile.seriesCount} stored series, {profile.valuationSeriesCount} with valuation-use coverage. <small>Technical codes: {profile.seriesType} / {profile.valueBasis}</small></li>)}</ul>
  </details>):<p>No currently permitted source datasets are available.</p>}
 </section>;
}

export function PolicyRuleSources({data,seriesType,valueBasis,datasetId,requireOfficialClose=false}:{data:Data;seriesType:string;valueBasis?:string|null;datasetId?:string|null;requireOfficialClose?:boolean}){
 const sources=data.sources.filter(s=>!datasetId||s.datasetId===datasetId);
 const matching=sources.filter(s=>s.priceProfiles.some(p=>p.seriesType===seriesType&&(!valueBasis||p.valueBasis===valueBasis)&&(!requireOfficialClose||p.closingMethod==='EXCHANGE_OFFICIAL')));
 const other=sources.filter(s=>!matching.includes(s));
 return <div><p>Sources recording this price definition: {matching.map(s=>s.label).join(', ')||'None'}.</p>
 {other.length?<p>Sources with no matching recorded definition: {other.map(s=>s.label).join(', ')}.</p>:null}
 <small>Source-wide definitions only. Check compatibility for this rule’s instrument scope, permissions and priority.</small></div>;
}
