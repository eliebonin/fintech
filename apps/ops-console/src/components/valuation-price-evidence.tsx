import {pricingEvidenceLabel} from '@/lib/pricing-policy';

type Selection={input_role?:string;conversion?:{method?:string;rate?:string};valuation_date:string;selected_value:string|null;pricing_date_requested:string|null;pricing_date_used:string|null;
 dataset_id:string|null;policy_rule_id:string|null;staleness_status:string;staleness_business_days:number|null;pricing_evidence:Record<string,unknown>|null};
type Execution={event_id:string;effective_at:string;booking:{trade_id:string;price:string;quantity:string;quote_factor:string;unit_multiplier:string}};
type Evidence={identity?:{openingCutoff?:string;closingCutoff?:string};selections?:Selection[];executionInputs?:Execution[];appliedRules?:{code:string;version:number;explanation:string;evidenceRefs:string[]}[]};

/** Read frozen evidence only: no recomputation or monetary allocation in UI. */
export function ValuationPriceEvidence({evidence}:{evidence:unknown}) {
 if(!evidence||typeof evidence!=='object')return null;
 const data=evidence as Evidence;
 const selections=Array.isArray(data.selections)?data.selections:[];
 const executions=Array.isArray(data.executionInputs)?data.executionInputs:[];
 const rules=Array.isArray(data.appliedRules)?data.appliedRules:[];
 if(!selections.length&&!executions.length&&!rules.length)return null;
 return <section><h4>Price inputs used</h4><p>Market marks are shared by the position. Period executions use their booked price; no artificial prior-day price is created for a new trade.</p>
  {rules.length?<section aria-label="Applied valuation rules"><h4>Applied rules</h4><ul>{rules.map((rule,index)=><li key={`${rule.code}-${index}`}><p>{rule.explanation}</p><small>{rule.code} · v{rule.version}</small><details><summary>Evidence references</summary>{rule.evidenceRefs.length?rule.evidenceRefs.join(' · '):'Recorded calculation convention'}</details></li>)}</ul></section>:null}
  {selections.map((s,index)=>{
   const basis=s.pricing_evidence?.priceBasis as Record<string,unknown>|undefined;
   const role=s.input_role==='FX'?'FX conversion':s.input_role==='FX_MATURITY_SUGGESTION'?'Maturity spot suggestion — not the booked closing rate':s.input_role==='FORWARD_RATE'?
    (s.valuation_date===data.identity?.closingCutoff?.slice(0,10)?'Closing contract rate':'Opening contract rate'):s.valuation_date===data.identity?.closingCutoff?.slice(0,10)?'Closing market mark':
    s.valuation_date===data.identity?.openingCutoff?.slice(0,10)?'Opening market mark':'Market mark';
   return <article key={`${s.policy_rule_id}-${index}`}><h5>{role} · valuation date {s.valuation_date}</h5><dl>
    <dt>{s.input_role==='FX'?'Source FX rate':'Source price'}</dt><dd>{s.selected_value??'No eligible price'}{basis?` · ${String(basis.sourceBasis)}`:''}</dd>
    {s.input_role==='FX'?<><dt>Applied FX conversion</dt><dd>{s.conversion?.rate} · {s.conversion?.method}</dd></>:null}
    {basis?<><dt>Valuation price</dt><dd>{String(basis.valuationValue)} · {String(basis.valuationBasis)}</dd><dt>Conversion proof</dt><dd>Factor {String(basis.factor)} · anchor {String(basis.anchorDate??'native raw')} · {String(basis.conversionVersion??'')}</dd></>:null}
    <dt>Requested market date</dt><dd>{s.pricing_date_requested??'—'}</dd>
    <dt>Actual market date</dt><dd>{s.pricing_date_used??'—'}</dd><dt>Freshness</dt><dd>{s.staleness_status} · {s.staleness_business_days??'—'} sessions</dd>
    <dt>Source dataset</dt><dd>{s.dataset_id??'—'}</dd><dt>Rule</dt><dd>{s.policy_rule_id??'—'}</dd></dl><p>{pricingEvidenceLabel(s.pricing_evidence)}</p></article>;
  })}
  {executions.length?<><h5>Booked execution price</h5><ul>{executions.map(e=><li key={e.event_id}><a href={`/trades/${encodeURIComponent(e.booking.trade_id)}`}>{e.booking.trade_id}</a> · price {e.booking.price} · signed quantity {e.booking.quantity} · recognition {e.effective_at} · unit multiplier {e.booking.unit_multiplier} / quote factor {e.booking.quote_factor}</li>)}</ul></>:null}
 </section>;
}
