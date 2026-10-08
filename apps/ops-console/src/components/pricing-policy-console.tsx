'use client';
import {useRef,useState} from 'react';
import type {FormEvent} from 'react';
import {newPricingRule,previewSubjects,pricingEvidenceLabel,stalenessLimit,type PricingPolicy,type PricingPolicyCreate,type PricingOptions,type PricingPreview,type PricingRule} from '@/lib/pricing-policy';

type PolicyPick={valuationPolicyId:string;policyCode:string;displayName:string};
type Option={id:string;label:string};
function Pick({label,value,options,onChange,required=false}:{label:string;value?:string|null;options:Option[];onChange:(value:string)=>void;required?:boolean}) {
 return <label>{label}<select value={value??''} required={required} onChange={event=>onChange(event.target.value)}><option value="">{required?'Select…':'Any / not specified'}</option>{options.map(option=><option key={option.id} value={option.id}>{option.label} · {option.id.slice(-8)}</option>)}</select></label>;
}
async function jsonRequest<T>(url:string,init?:RequestInit):Promise<T> {
 const response=await fetch(url,init);const body=await response.json();
 if(!response.ok)throw new Error(body?.error?.message??body?.error?.detail??body?.detail??`Request failed (${response.status}).`);
 return body as T;
}

export function PricingPolicyConsole({options,initialPolicies}:{options:PricingOptions;initialPolicies:PolicyPick[]}) {
 const today=new Date().toISOString().slice(0,10);
 const [policies,setPolicies]=useState(initialPolicies),[selected,setSelected]=useState<PricingPolicy|null>(null);
 const [draft,setDraft]=useState<PricingPolicyCreate>({policyCode:'',displayName:'',valuationCutId:'',validFrom:today,rules:[newPricingRule(1)]});
 const [valuationDate,setValuationDate]=useState(today),[information,setInformation]=useState(new Date().toISOString().slice(0,16));
 const [subjects,setSubjects]=useState(''),[preview,setPreview]=useState<PricingPreview|null>(null);
 const [error,setError]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
 const submission=useRef<{canonical:string;key:string}|null>(null);
 function updateRule(index:number,patch:Partial<PricingRule>) {setDraft(current=>({...current,rules:current.rules.map((rule,i)=>i===index?{...rule,...patch}:rule)}));setMessage('');}
 async function selectPolicy(id:string) {
  setError('');setPreview(null);setBusy(true);
  try {const policy=await jsonRequest<PricingPolicy>(`/api/market-data/valuation-policies/${id}`);setSelected(policy);
   setDraft({policyCode:policy.policyCode,displayName:policy.displayName,valuationCutId:policy.valuationCutId,strategyId:policy.strategyId,validFrom:policy.validFrom,validTo:policy.validTo,rules:policy.rules});submission.current=null;setMessage('');
  }catch(caught){setError((caught as Error).message);}finally{setBusy(false);}
 }
 async function save(event:FormEvent<HTMLFormElement>) {
  event.preventDefault();setBusy(true);setError('');setMessage('');
  const canonical=JSON.stringify(draft);
  if(submission.current?.canonical!==canonical)submission.current={canonical,key:crypto.randomUUID()};
  try {const policy=await jsonRequest<PricingPolicy>('/api/market-data/valuation-policies',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':submission.current!.key},body:canonical});
   setSelected(policy);setPreview(null);setPolicies(current=>current.some(p=>p.valuationPolicyId===policy.valuationPolicyId)?current:[policy,...current]);setMessage(`Saved ${policy.policyCode} version ${policy.versionNo}. Existing versions are unchanged.`);
  }catch(caught){setError((caught as Error).message);}finally{setBusy(false);}
 }
 async function runPreview(event:FormEvent<HTMLFormElement>) {
  event.preventDefault();if(!selected)return;setBusy(true);setError('');setPreview(null);
  try {setPreview(await jsonRequest<PricingPreview>('/api/market-data/resolution-preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({subjectReferenceNodeIds:previewSubjects(subjects),valuationPolicyId:selected.valuationPolicyId,valuationCutId:selected.valuationCutId,strategyId:selected.strategyId,valuationDate,marketDataAsOfUtc:`${information}:00Z`,usePurpose:'VALUATION'})}));
  }catch(caught){setError((caught as Error).message);}finally{setBusy(false);}
 }
 return <>
  <section className="history-panel"><h2>Inspect a saved version</h2><p>Exact series → subject → venue + type → venue → type → default. Missing specific rules do not fall through.</p>
   <label>Policy version<select value={selected?.valuationPolicyId??''} disabled={busy} onChange={e=>{if(e.target.value)void selectPolicy(e.target.value);}}><option value="">Select a policy…</option>{policies.map(p=><option key={p.valuationPolicyId} value={p.valuationPolicyId}>{p.policyCode} · {p.displayName} · {p.valuationPolicyId.slice(-8)}</option>)}</select></label>
   <button type="button" disabled={busy} onClick={async()=>{setError('');try{setPolicies(await jsonRequest(`/api/market-data/valuation-policies?valuationDate=${valuationDate}`));}catch(caught){setError((caught as Error).message);}}}>Refresh versions for preview date</button>
   {selected?<p>{selected.policyCode} · version {selected.versionNo} · {selected.strategyId?'Strategy scoped':'Tenant shared'} · {selected.createdByUserAccountId?'Attributed immutable version':'Legacy configuration'}</p>:null}
  </section>
  {!options.canManage?<section className="history-panel"><h2>Read-only configuration</h2><p>Creating a version requires a MARKET_DATA tenant administrator.</p>{selected?<pre>{JSON.stringify(selected.rules,null,2)}</pre>:null}</section>:
   <form className="history-panel pricing-policy-editor" onSubmit={save}><h2>{selected?'Create a revised version':'Create pricing policy'}</h2><p>Save creates an immutable version. Preview uses the saved version, not unsaved edits. This does not grant data rights.</p>
    <fieldset disabled={busy}><legend>Policy identity and scope</legend><div className="pricing-policy-fields">
     <label>Policy code<input required maxLength={100} value={draft.policyCode} onChange={e=>setDraft({...draft,policyCode:e.target.value})}/></label>
     <label>Display name<input required maxLength={250} value={draft.displayName} onChange={e=>setDraft({...draft,displayName:e.target.value})}/></label>
     <Pick label="Default policy cut" required options={options.cuts} value={draft.valuationCutId} onChange={id=>setDraft({...draft,valuationCutId:id})}/>
     <Pick label="Strategy (optional)" options={options.strategies} value={draft.strategyId} onChange={id=>setDraft({...draft,strategyId:id||null})}/>
     <label>Effective from<input required type="date" value={draft.validFrom} onChange={e=>setDraft({...draft,validFrom:e.target.value})}/></label>
     <label>Effective to (optional)<input type="date" value={draft.validTo??''} onChange={e=>setDraft({...draft,validTo:e.target.value||null})}/></label>
    </div></fieldset>
    {draft.rules.map((rule,index)=><fieldset key={index} disabled={busy}><legend>Rule {index+1} · {rule.pricingConvention}</legend><div className="pricing-policy-fields">
     <label>Rule priority<input type="number" required min={1} max={10000} value={rule.ruleSequence} onChange={e=>updateRule(index,{ruleSequence:Number(e.target.value)})}/></label>
     <label>Pricing convention<select value={rule.pricingConvention} onChange={e=>updateRule(index,{pricingConvention:e.target.value as PricingRule['pricingConvention'],fixingCode:null,pricingCutId:null})}><option value="SESSION_CLOSE">Exchange session close</option><option value="NAMED_FIXING">Named fixing</option><option value="EXPLICIT_TIME">Explicit local time</option><option value="NAV_DATE">Fund NAV valuation dates</option><option value="LEGACY">Legacy date-only semantics</option></select></label>
     <label>Series type<input required maxLength={50} value={rule.seriesType} onChange={e=>updateRule(index,{seriesType:e.target.value})}/></label>
     <Pick label="Venue" options={options.venues} value={rule.marketVenueId} onChange={id=>updateRule(index,{marketVenueId:id||null})}/>
     <Pick label="Instrument type" options={options.instrumentTypes} value={rule.instrumentTypeId} onChange={id=>updateRule(index,{instrumentTypeId:id||null})}/>
     <Pick label="Source dataset" options={options.datasets} value={rule.datasetId} onChange={id=>updateRule(index,{datasetId:id||null})}/>
     <Pick label="Calendar override" options={options.calendars} value={rule.marketCalendarId} onChange={id=>updateRule(index,{marketCalendarId:id||null})}/>
     {rule.pricingConvention==='NAMED_FIXING'||rule.pricingConvention==='EXPLICIT_TIME'?<Pick label="Rule pricing cut" required options={options.cuts} value={rule.pricingCutId} onChange={id=>updateRule(index,{pricingCutId:id||null})}/>:null}
     {rule.pricingConvention==='NAMED_FIXING'?<label>Exact fixing code<input required maxLength={100} value={rule.fixingCode??''} onChange={e=>updateRule(index,{fixingCode:e.target.value})}/></label>:null}
     <label>Value basis (optional exact match)<input maxLength={50} placeholder="e.g. SPLIT_ADJUSTED" value={rule.valueBasis??''} onChange={e=>updateRule(index,{valueBasis:e.target.value||null})}/></label>
     <label>Pricing date rule<select value={rule.pricingDateRule??'SAME_DAY'} onChange={e=>updateRule(index,{pricingDateRule:e.target.value as PricingRule['pricingDateRule'],lagBusinessDays:0})}><option value="SAME_DAY">Same session</option><option value="PRIOR_AVAILABLE">Prior available (bounded tolerance)</option><option value="FIXED_LAG">Fixed session lag</option></select></label>
     {rule.pricingDateRule==='FIXED_LAG'?<label>Lag (trading sessions)<input required type="number" min={0} max={366} value={rule.lagBusinessDays??0} onChange={e=>updateRule(index,{lagBusinessDays:Number(e.target.value)})}/></label>:null}
     <label>Maximum staleness (sessions)<input type="number" min={0} max={366} placeholder="No fixed limit" value={rule.maxStalenessBusinessDays??''} onChange={e=>{try{updateRule(index,{maxStalenessBusinessDays:stalenessLimit(e.target.value)});}catch(caught){setError((caught as Error).message);}}}/></label>
     <label>Missing data action<select value={rule.missingDataAction??'FAIL'} onChange={e=>updateRule(index,{missingDataAction:e.target.value as PricingRule['missingDataAction']})}><option value="FAIL">Fail</option><option value="WARN">Warn (no fabricated value)</option><option value="MANUAL_OVERRIDE">Request manual override</option></select></label>
    </div><details><summary>Exact subject / series filters</summary><div className="pricing-policy-fields"><label>Subject reference UUID<input value={rule.subjectReferenceNodeId??''} onChange={e=>updateRule(index,{subjectReferenceNodeId:e.target.value||null})}/></label><label>Series UUID<input value={rule.marketDataSeriesId??''} onChange={e=>updateRule(index,{marketDataSeriesId:e.target.value||null})}/></label></div></details>
    {rule.pricingConvention==='SESSION_CLOSE'?<p>Targets the selected listing’s actual close, including early closes. Never guesses a listing for a canonical instrument or certifies a provider bar as an official tape.</p>:rule.pricingConvention==='LEGACY'?<p>Legacy rules retain weekday-based date arithmetic. Composite time and value-basis filters are not supported in this mode.</p>:null}
    <button type="button" disabled={draft.rules.length===1} onClick={()=>setDraft({...draft,rules:draft.rules.filter((_,i)=>i!==index)})}>Remove rule</button></fieldset>)}
    <button type="button" disabled={busy||draft.rules.length>=50} onClick={()=>setDraft({...draft,rules:[...draft.rules,newPricingRule(Math.max(...draft.rules.map(r=>r.ruleSequence))+1)]})}>Add rule</button> <button disabled={busy} type="submit">{busy?'Working…':'Save new immutable version'}</button>
   </form>}
  <form className="history-panel" onSubmit={runPreview}><h2>Read-only preview</h2><p>One information cutoff controls receipt/revisions; each rule has its own pricing target. No snapshot, observation, trade or valuation is written.</p><fieldset disabled={busy}><legend>Saved-version preview context</legend><div className="pricing-policy-fields"><label>Valuation date<input required type="date" value={valuationDate} onChange={e=>{setValuationDate(e.target.value);setPreview(null);}}/></label><label>Information cutoff (UTC)<input required type="datetime-local" value={information} onChange={e=>{setInformation(e.target.value);setPreview(null);}}/></label></div><label>Listing / reference UUIDs (up to 50)<textarea required rows={3} value={subjects} onChange={e=>{setSubjects(e.target.value);setPreview(null);}}/></label><button type="submit" disabled={!selected}>Preview saved version</button></fieldset>
   <p>Yahoo daily bars are not named FX fixings. Selection requires NON_DISPLAY rights; personal DISPLAY access alone is insufficient. Package calendars are labelled non-authoritative.</p>
  </form>
  {error?<p className="error-panel" role="alert">{error}</p>:null}{message?<p role="status">{message}</p>:null}
  {preview?<section className="history-panel" aria-live="polite"><h2>Preview: {preview.status}</h2>{preview.items.map(item=><article key={item.subjectReferenceNodeId}><h3>{item.status} · {item.subjectReferenceNodeId}</h3><p>{item.selectedValue??'No eligible value'} · {item.entitlementDecision} · {item.exceptionCode??item.selectionReason}</p><p>{pricingEvidenceLabel(item.pricingEvidence)}</p><p>Requested {item.pricingDateRequested??'—'} / used {item.pricingDateUsed??'—'} · {item.stalenessStatus}</p><details><summary>Input and target evidence</summary><pre>{JSON.stringify(item,null,2)}</pre></details></article>)}</section>:null}
 </>;
}
