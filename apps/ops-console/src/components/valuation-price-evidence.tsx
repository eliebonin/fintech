import {pricingEvidenceLabel} from '@/lib/pricing-policy';
import {ReferenceName,TechnicalReference} from '@/features/valuation/technical-reference';
import type {Presentation} from '@/features/valuation/types';

type Selection={input_role?:string;conversion?:{method?:string;rate?:string};valuation_date:string;selected_value:string|null;pricing_date_requested:string|null;pricing_date_used:string|null;
 dataset_id:string|null;policy_rule_id:string|null;staleness_status:string;staleness_business_days:number|null;pricing_evidence:Record<string,unknown>|null};
type Execution={event_id:string;effective_at:string;booking:{trade_id:string;price:string;quantity:string;quote_factor:string;unit_multiplier:string}};
type Evidence={identity?:{openingCutoff?:string;closingCutoff?:string};selections?:Selection[];executionInputs?:Execution[];appliedRules?:{code:string;version:number;explanation:string;evidenceRefs:string[]}[]};

/** Read frozen evidence only: no recomputation or monetary allocation in UI. */
export function ValuationPriceEvidence({evidence,metadata,kind='position'}:{evidence:unknown;metadata?:Presentation;kind?:'position'|'cash'}) {
 if(!evidence||typeof evidence!=='object')return null;
 const data=evidence as Evidence;
 const selections=Array.isArray(data.selections)?data.selections:[];
 const executions=Array.isArray(data.executionInputs)?data.executionInputs:[];
 const rules=Array.isArray(data.appliedRules)?data.appliedRules:[];
 if(!selections.length&&!executions.length&&!rules.length)return null;
 return <section><h4>{kind==='cash'?'Cash FX inputs used':'Price inputs used'}</h4><p>{kind==='cash'?'Rates express reporting-currency units per native cash unit. Requested and actual market dates, sources and conversion evidence are retained below.':'Market marks are shared by the position. Period executions use their booked price; no artificial prior-day price is created for a new trade.'}</p>
  {rules.length?<details aria-label="Applied valuation rules"><summary>Applied rules · {rules.length}</summary><ul>{rules.map((rule,index)=><li key={`${rule.code}-${index}`}><p>{rule.explanation}</p><small>{rule.code} · v{rule.version}</small><details><summary>Evidence references</summary>{rule.evidenceRefs.length?rule.evidenceRefs.join(' · '):'Recorded calculation convention'}</details></li>)}</ul></details>:null}
  {selections.length?<div className="pnl-table-scroll"><table className="pnl-table pnl-input-comparison"><caption>Frozen prices and FX · exact values</caption><thead><tr><th scope="col">Input / valuation date</th><th scope="col">Value used</th><th scope="col">Market dates</th><th scope="col">Source / rule</th></tr></thead><tbody>{selections.map((s,index)=>{
   const basis=s.pricing_evidence?.priceBasis as Record<string,unknown>|undefined;
   const fxRole=s.input_role==='FX'||s.input_role==='CASH_FX';
   const role=fxRole?'FX conversion':s.input_role==='FX_MATURITY_SUGGESTION'?'Maturity spot suggestion — not the booked closing rate':s.input_role==='FORWARD_RATE'?
    (s.valuation_date===data.identity?.closingCutoff?.slice(0,10)?'Closing contract rate':'Opening contract rate'):s.valuation_date===data.identity?.closingCutoff?.slice(0,10)?'Closing market mark':
    s.valuation_date===data.identity?.openingCutoff?.slice(0,10)?'Opening market mark':'Market mark';
   return <tr key={`${s.policy_rule_id}-${index}`}><th scope="row">{role}<small className="pnl-position-caption">{s.valuation_date}</small></th><td>
    <strong>{String(basis?.valuationValue??(fxRole?s.conversion?.rate??s.selected_value:s.selected_value)??'Not recorded')}</strong>
    <details><summary>Source and conversion proof</summary><dl><dt>{fxRole?'Source FX rate':'Source price'}</dt><dd>{s.selected_value??'No eligible price'}{basis?` · ${String(basis.sourceBasis)}`:''}</dd>
    {fxRole?<><dt>Applied FX conversion</dt><dd>{s.conversion?.rate??'Not recorded'} · {s.conversion?.method??'Not recorded'}</dd></>:null}
    {basis?<><dt>Valuation price</dt><dd>{String(basis.valuationValue)} · {String(basis.valuationBasis)}</dd><dt>Conversion proof</dt><dd>Factor {String(basis.factor)} · anchor {String(basis.anchorDate??'native raw')} · {String(basis.conversionVersion??'')}</dd></>:null}</dl></details></td>
    <td><span>Requested market date: {s.pricing_date_requested??'Not recorded'}</span><br/><strong>Actual market date: {s.pricing_date_used??'Not recorded'}</strong><small className="pnl-position-caption">Freshness: {s.staleness_status??'Not recorded'} · {s.staleness_business_days??'—'} sessions</small></td>
    <td><ReferenceName id={s.dataset_id} label={metadata?.datasets[s.dataset_id??'']} fallback="Dataset name unavailable"/><ReferenceName id={s.policy_rule_id} label={metadata?.rules[s.policy_rule_id??'']} fallback="Rule description unavailable"/><details><summary>Selection details</summary><p>{pricingEvidenceLabel(s.pricing_evidence)}</p></details></td></tr>;
  })}</tbody></table></div>:<p>No boundary price/FX selections recorded. Period executions and applied rules, when present, explain the result.</p>}
  {executions.length?<details><summary>Booked execution price</summary><ul>{executions.map(e=><li key={e.event_id}><a href={`/trades/${encodeURIComponent(e.booking.trade_id)}`}>{e.effective_at.slice(0,10)} · {e.booking.quantity.startsWith('-')?'Sell / decrease':'Buy / increase'}</a> · price {e.booking.price} · signed quantity {e.booking.quantity} · recognition {e.effective_at} · unit multiplier {e.booking.unit_multiplier} / quote factor {e.booking.quote_factor}<TechnicalReference id={e.booking.trade_id} label="Trade ID"/></li>)}</ul></details>:null}
 </section>;
}
