import {InstrumentLabel} from './instrument-label';
import Link from 'next/link';
import {instrumentDisplayHref} from '@/lib/instrument-display';
import type {InstrumentDisplays} from '@/lib/instrument-display';
import {formatTradeExactDecimal} from '@/lib/trades';
import {MeasureDetails} from './strategy-measure-details';
import {MeasureRowDisclosure} from './measure-row-disclosure';
import {MeasureCurrencyDisplay,MeasureAmount} from './measure-currency-display';

export type ScalarMeasure={localAmount:string|null;currency:string|null;strategyAmount:string|null;strategyCurrency:string|null;status:string;reasonCode?:string};
export type MonetaryMeasure=ScalarMeasure&{representation?:'CONTRACTUAL_CURRENCY_LEGS';legs?:Array<ScalarMeasure&{role:'BASE'|'QUOTE'}>};
export type MeasureRow={subjectId?:string;positionId:string;instrumentId:string;name:string;instrumentType?:string;instrumentTypeLabel?:string;quantity:string;quantityUnit:string;
 contractDate?:string|null;contractDateLabel?:string|null;attentionMessage?:string|null;measures:Record<string,MonetaryMeasure>;
 evidence:{issues?:Record<string,string>;route?:string}&Record<string,unknown>;evidenceHash:string};
export type MeasureData={instrumentDisplays?:InstrumentDisplays;status:string;asOf:string;informationCutoff:string;total:number;limit:number;offset:number;reportingCurrency?:string;items:MeasureRow[]};
export type MeasurePolicy={id:string;label:string;strategyId?:string|null};
type Display='local'|'strategy'|'both';

function rowStatus(row:MeasureRow){
 const measures=Object.values(row.measures);
 if(measures.some(m=>m.reasonCode==='INVALID_CONTRACT'))return {label:'Review required',tone:'warning'};
 if(measures.some(m=>m.status==='LOCAL_ONLY'||m.legs?.some(l=>l.status==='LOCAL_ONLY')))return {label:'Local amount only',tone:'warning'};
 if(measures.some(m=>m.status==='UNAVAILABLE'&&m.reasonCode!=='NOT_SUPPORTED_YET'))return {label:'Missing input',tone:'warning'};
 if(measures.every(m=>m.reasonCode==='NOT_SUPPORTED_YET'))return {label:'Not supported yet',tone:'partial'};
 if(measures.some(m=>m.reasonCode==='NOT_SUPPORTED_YET'))return {label:'Partial',tone:'partial'};
 return {label:'Available',tone:'available'};
}

export function StrategyMeasures({strategyId,query,policies,data,error,canCalculate=true}:{strategyId:string;query:URLSearchParams;policies:MeasurePolicy[];data?:MeasureData;error?:string;canCalculate?:boolean}){
 const mode=query.get('displayCurrency');const display:Display=mode==='local'||mode==='strategy'?mode:'both';
 const basis=query.get('basis')??'EXECUTED';
 const page=(offset:number)=>{const next=new URLSearchParams(query);next.set('view','measures');next.set('offset',String(offset));if(data)next.set('informationCutoff',data.informationCutoff);return `/strategies/${encodeURIComponent(strategyId)}?${next}`;};
 // Keep the server's full-population type/name ordering; never reorder a partial page.
 const groups:Array<{label:string;rows:MeasureRow[]}>=[];
 for(const row of data?.items??[]){const label=row.instrumentTypeLabel??'Other instruments';let group=groups.at(-1);if(!group||group.label!==label){group={label,rows:[]};groups.push(group);}group.rows.push(row);}
 const selectedPolicy=policies.find(p=>p.id===query.get('policyId'));
 const range=data?.items.length?`${data.offset+1}–${data.offset+data.items.length}`:'0';
 return <MeasureCurrencyDisplay key={`${data?.informationCutoff??'empty'}:${strategyId}:${query.get('policyId')??''}`} initial={display}><section className="strategy-card measure-report">
  <div className="strategy-section-heading"><div><h2>Position values &amp; exposure</h2><p className="muted">What each position represents and is worth on the selected date.</p></div><span className="strategy-chip">Preview only</span></div>
  <p className="measure-scope">Not staged or published · Not P&amp;L, weights or complete strategy NAV. Unavailable amounts are not zero.</p>
  {canCalculate?<form className="strategy-toolbar measure-toolbar" method="get">
   <input type="hidden" name="view" value="measures"/>
   <label>As-of date<input type="date" name="asOf" required defaultValue={query.get('asOf')??''}/></label>
   <label>Pricing policy<select name="policyId" required defaultValue={query.get('policyId')??''}><option value="">Select pricing policy</option>{policies.map(p=><option key={p.id} value={p.id}>{p.label}</option>)}</select></label>
   <button type="submit">Load measures</button>
   <details className="measure-advanced"><summary>Advanced options</summary><label>Date basis<select name="basis" defaultValue={basis}><option value="EXECUTED">Executed holdings</option><option value="VALUATION_RECOGNISED">Valuation-recognised holdings</option></select></label><p>Controls when a booking enters the position. It does not change the price date.</p></details>
  </form>:<p role="status">Loading a preview requires strategy-scoped valuation-calculation, valuation-read, trade-read and market-data access.</p>}
  {error?<p role="alert" className="error-panel">{error}</p>:null}
  {data?<>
   <div className="measure-context"><p><strong>{data.asOf}</strong> · {selectedPolicy?.label??'Selected policy'} · {basis==='EXECUTED'?'Executed holdings':'Valuation-recognised holdings'}{data.reportingCurrency?` · Strategy currency ${data.reportingCurrency}`:''}</p><p className="muted">Showing {range} of {data.total} positions / exceptions · Information known at {data.informationCutoff}</p></div>
   <details className="measure-definitions"><summary>What do the three measures mean?</summary><dl><dt>Reference notional</dt><dd>Contract size or current monetary size, depending on product. It is not necessarily purchase cost.</dd><dt>Exposure</dt><dd>Product-specific monetary exposure; forwards show two contractual currency legs. These are not comparable risk weights.</dd><dt>Market value</dt><dd>The position's current asset/liability value where supported. Futures and FX-forward market value remain deferred.</dd></dl><p>No combined NAV or exposure total is inferred from this report.</p></details>
   <p className="measure-display-note">Amounts shown to 2 decimals · Exact values in Inspect · Quantities are not rounded.</p>
   <div className="table-wrap measure-table-wrap" role="region" aria-label="Position monetary measures" tabIndex={0}><table className="strategy-positions-table measure-table"><caption className="sr-only">Position monetary measures grouped by instrument type, in server alphabetical order</caption><thead><tr><th scope="col">Instrument / listing</th><th scope="col" className="numeric">Quantity</th><th scope="col" className="numeric">Reference notional</th><th scope="col" className="numeric">Exposure / currency legs</th><th scope="col" className="numeric">Market value</th><th scope="col">Status</th><th scope="col"><span className="sr-only">Inspect</span></th></tr></thead>
    {groups.map((group,index)=><tbody key={`${group.label}-${index}`}><tr className="strategy-position-group"><th scope="rowgroup" colSpan={7}>{group.label}</th></tr>{group.rows.map(row=>{const status=rowStatus(row);return <MeasureRowDisclosure key={row.positionId} name={row.name} details={<MeasureDetails row={row} strategyId={strategyId} query={query} informationCutoff={data.informationCutoff}/> }>
     <th scope="row" className="measure-instrument"><InstrumentLabel display={data.instrumentDisplays?.[row.subjectId??row.instrumentId]} fallbackName={data.instrumentDisplays===undefined?row.name:undefined} href={instrumentDisplayHref(data.instrumentDisplays?.[row.subjectId??row.instrumentId],row.subjectId??row.instrumentId,row.instrumentId)}/>{row.contractDate?<small>{row.contractDateLabel??'Maturity'} · {row.contractDate}</small>:null}{row.attentionMessage?<small className="measure-warning">{row.attentionMessage}</small>:null}</th>
     <td className="numeric">{formatTradeExactDecimal(row.quantity)}<small className="strategy-position-unit">{row.quantityUnit}</small></td>
     {['referenceNotional','economicExposure','marketValue'].map(name=><td key={name} className="numeric"><MeasureAmount measure={row.measures[name]}/></td>)}
     <td><span className={`measure-status measure-status-${status.tone}`}>{status.label}</span>{Object.entries(row.evidence.issues??{}).filter(([key])=>key!=='dirtyPrice'||row.measures.marketValue.status==='UNAVAILABLE').map(([key,value])=><small key={key} className="measure-row-note">{value}</small>)}</td>
    </MeasureRowDisclosure>;})}</tbody>)}
   </table></div>
   {!data.items.length?<p className="strategy-empty">{data.total?'No positions on this page. Return to the previous page.':'No open positions or retained exceptions on this date.'}</p>:null}
   <nav className="strategy-paging" aria-label="Measure pages">{data.offset>0?<Link href={page(Math.max(0,data.offset-data.limit))}>Previous</Link>:<span>Previous</span>}<span>{range} of {data.total}</span>{data.offset+data.limit<data.total?<Link href={page(data.offset+data.limit)}>Next</Link>:<span>Next</span>}</nav>
  </>:!error&&canCalculate?<p className="strategy-empty">Select a date and pricing policy, then load the position measures. No trade-price fallback is applied.</p>:null}
 </section></MeasureCurrencyDisplay>;
}
