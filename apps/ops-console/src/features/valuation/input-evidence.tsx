type Input={kind?:string;valueDate?:string;inputId?:string;payload?:{currencyId?:string;reportingCurrencyId?:string;sourceReference?:string;amounts?:Record<string,string>}};
import type {Presentation} from './types';
import {ReferenceName} from './technical-reference';
/** Exact server-returned amounts only; no client-side interest calculation. */
export function InputEvidence({evidence,metadata}:{evidence:unknown;metadata?:Presentation}){
 if(!evidence||typeof evidence!=='object')return null;
 const inputs=(evidence as {economicInputs?:Input[]}).economicInputs??[];
 const marks=(evidence as {selections?:{pricing_evidence?:{manualOverride?:{requestId:string;value:string;valueDate:string;sourceReference:string;reason:string}}}[]}).selections??[];
 const reviewed=[...new Map(marks.flatMap(selection=>selection.pricing_evidence?.manualOverride?[selection.pricing_evidence.manualOverride]:[]).map(mark=>[mark.requestId,mark])).values()];
 return <>{reviewed.map(mark=><article key={mark.requestId}><h5>Reviewed manual mark · {mark.valueDate}</h5><p>Exact quote: {mark.value}. Source: {mark.sourceReference}</p><p>{mark.reason}</p><p className="pnl-muted">Tenant-reviewed input; original provider observations are unchanged.</p></article>)}{inputs.filter(i=>i.kind==='MISSING_DAILY_ACCRUAL').map((input,index)=><p key={`missing-${index}`} className="pnl-notice">{input.valueDate}: Accrual not supplied—not included. Missing is not confirmed zero.</p>)}{inputs.filter(i=>i.kind==='DAILY_ACCRUAL').map((input,index)=><article key={input.inputId??index}><h5>Daily accrued interest · {input.valueDate}</h5>
  <p>{input.payload?.sourceReference}</p><dl className="pnl-fact-grid"><div><dt>Local currency</dt><dd><ReferenceName id={input.payload?.currencyId} label={metadata?.currencies[input.payload?.currencyId??'']} fallback="Currency name unavailable"/></dd></div><div><dt>Reporting currency</dt><dd><ReferenceName id={input.payload?.reportingCurrencyId} label={metadata?.currencies[input.payload?.reportingCurrencyId??'']} fallback="Currency name unavailable"/></dd></div></dl>
  <dl><dt>Daily earned · local / reporting</dt><dd>{input.payload?.amounts?.dailyLocal} / {input.payload?.amounts?.dailyBase}</dd>
   <dt>Accumulated balance · local / reporting</dt><dd>{input.payload?.amounts?.balanceLocal} / {input.payload?.amounts?.balanceBase}</dd>
   <dt>FX on opening accrued receivable (CARRY)</dt><dd>{input.payload?.amounts?.receivableFx}</dd></dl></article>)}</>;
}
