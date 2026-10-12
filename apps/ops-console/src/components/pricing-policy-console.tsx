'use client';
import {useEffect,useRef,useState} from 'react';
import type {FormEvent} from 'react';
import {patchPricingRule,newPricingRule,newDefaultPricingRule,newPricingPolicyDraft,withPricingPolicyMode,previewSubjects,pricingEvidenceLabel,stalenessLimit,type PricingPolicy,type PricingPolicyCreate,type PricingOptions,type PricingPreview,type PricingRule,type PricingCompatibility,type PricingDataOptions} from '@/lib/pricing-policy';
import styles from './pricing-policy-console.module.css';
import {PricingPolicyHelp} from './pricing-policy-help';
import {PolicyCompatibilityReport,PolicySourceProfiles,PolicyRuleSources} from './pricing-policy-compatibility';

type PolicyPick={valuationPolicyId:string;policyCode:string;displayName:string};
type Option={id:string;label:string};
const priceFamilies=[{id:'CLOSE',label:'Closing price'},
 {id:'FX_SPOT',label:'FX spot rate'},{id:'NAV',label:'Fund NAV'},{id:'OFFICIAL_NAV',label:'Published official NAV'},{id:'INDICATIVE_NAV',label:'Indicative NAV'},
 {id:'BID',label:'Bid price'},{id:'ASK',label:'Ask price'},{id:'MID',label:'Mid price'},{id:'EVALUATED_PRICE',label:'Evaluated price'}];
const adjustmentChoices=[{id:'RAW',label:'Unadjusted — follows traded units'},{id:'SPLIT_ADJUSTED',label:'Split-adjusted — historical stock-split adjustment'},
 {id:'VENDOR_ADJUSTED',label:'Provider-adjusted — check provider methodology'},{id:'TOTAL_RETURN',label:'Total-return adjusted — includes income assumptions'}];
function PriceChoice({label,value,choices,onChange,id}:{label:string;value?:string|null;choices:Option[];onChange:(value:string|null)=>void;id:string}){
 return <div><label>{label}<select aria-describedby={`${id}-hint`} value={value??''} onChange={e=>onChange(e.target.value||null)}><option value="">No exact requirement (not valuation-ready)</option>{choices.map(c=><option key={c.id} value={c.id}>{c.label}</option>)}{value&&!choices.some(c=>c.id===value)?<option value={value}>Existing custom definition: {value}</option>:null}</select></label>
 <small id={`${id}-hint`}>Select the definition the source actually supplies. The technical code is retained unchanged.</small>
 <details><summary>Advanced custom definition</summary><label>Exact stored code<input maxLength={50} value={value??''} onChange={e=>onChange(e.target.value||null)}/></label></details></div>;
}
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
 const [draft,setDraft]=useState<PricingPolicyCreate>(()=>newPricingPolicyDraft(today));
 const [valuationDate,setValuationDate]=useState(today),[information,setInformation]=useState(new Date().toISOString().slice(0,16));
 const [subjects,setSubjects]=useState(''),[preview,setPreview]=useState<PricingPreview|null>(null);
 const [error,setError]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
 const submission=useRef<{canonical:string;key:string}|null>(null);
 const [dataOptions,setDataOptions]=useState<PricingDataOptions|null>(null),[dataError,setDataError]=useState('');
 const [compatibility,setCompatibility]=useState<{canonical:string;report:PricingCompatibility}|null>(null);
 const [acknowledgedCanonical,setAcknowledgedCanonical]=useState<string|null>(null);
 useEffect(()=>{let live=true;jsonRequest<PricingDataOptions>('/api/market-data/policy-data-options').then(data=>{if(live)setDataOptions(data);}).catch(()=>{if(live)setDataError('Source definitions could not be loaded. Compatibility has not been established.');});return()=>{live=false;};},[]);
 const canonicalDraft=JSON.stringify(draft);
 const currentReport=compatibility?.canonical===canonicalDraft?compatibility.report:null;
 const explicitRules=draft.rules??[],defaultRules=draft.defaultRules??[];
 const allRules=[...explicitRules,...defaultRules];
 function updateRule(index:number,patch:Partial<PricingRule>) {
  if(patch.seriesType==='OFFICIAL_CLOSE')patch={...patch,seriesType:'CLOSE',requireOfficialClose:true};
  else if(patch.seriesType!==undefined&&patch.seriesType!=='CLOSE')patch={...patch,requireOfficialClose:false};
  setDraft(current=>{
  const rules=current.rules??[],defaults=current.defaultRules??[];
  return index<rules.length?{...current,rules:rules.map((rule,i)=>i===index?patchPricingRule(rule,patch):rule)}:
   {...current,defaultRules:defaults.map((rule,i)=>i===index-rules.length?patchPricingRule(rule,patch):rule)};
 });setMessage('');}
 function nextSequence(){return Math.max(0,...allRules.map(r=>r.ruleSequence))+1;}
 async function selectPolicy(id:string) {
  setError('');setPreview(null);setBusy(true);
  try {const policy=await jsonRequest<PricingPolicy>(`/api/market-data/valuation-policies/${id}`);setSelected(policy);
   setDraft({policyCode:policy.policyCode,displayName:policy.displayName,valuationCutId:policy.valuationCutId,strategyId:policy.strategyId,validFrom:policy.validFrom,validTo:policy.validTo,selectionMode:policy.selectionMode,rules:policy.rules,defaultRules:policy.defaultRules});submission.current=null;setMessage('');
  }catch(caught){setError((caught as Error).message);}finally{setBusy(false);}
 }
 async function save(event:FormEvent<HTMLFormElement>) {
  event.preventDefault();setBusy(true);setError('');setMessage('');
  const canonical=JSON.stringify(draft);
  try{
   const report=currentReport??await jsonRequest<PricingCompatibility>('/api/market-data/policy-compatibility',{method:'POST',headers:{'Content-Type':'application/json'},body:canonical});
   setCompatibility({canonical,report});
   if(report.status==='ACTION_REQUIRED'&&acknowledgedCanonical!==canonical){setMessage('Review the compatibility notices. Nothing has been saved. You may explicitly retain a future-data configuration below.');setBusy(false);return;}
  }catch(caught){setError((caught as Error).message);setBusy(false);return;}
  if(submission.current?.canonical!==canonical)submission.current={canonical,key:crypto.randomUUID()};
  try {const policy=await jsonRequest<PricingPolicy>('/api/market-data/valuation-policies',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':submission.current!.key},body:canonical});
   setSelected(policy);setPreview(null);setPolicies(current=>current.some(p=>p.valuationPolicyId===policy.valuationPolicyId)?current:[policy,...current]);setMessage(`Saved ${policy.policyCode} version ${policy.versionNo}. Existing versions are unchanged.`);
  }catch(caught){setError((caught as Error).message);}finally{setBusy(false);}
 }
 async function checkCompatibility(){
  setBusy(true);setError('');setMessage('');
  try{const canonical=JSON.stringify(draft);const report=await jsonRequest<PricingCompatibility>('/api/market-data/policy-compatibility',{method:'POST',headers:{'Content-Type':'application/json'},body:canonical});setCompatibility({canonical,report});}
  catch(caught){setError((caught as Error).message);}finally{setBusy(false);}
 }
 async function runPreview(event:FormEvent<HTMLFormElement>) {
  event.preventDefault();if(!selected)return;setBusy(true);setError('');setPreview(null);
  try {setPreview(await jsonRequest<PricingPreview>('/api/market-data/resolution-preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({subjectReferenceNodeIds:previewSubjects(subjects),valuationPolicyId:selected.valuationPolicyId,valuationCutId:selected.valuationCutId,strategyId:selected.strategyId,valuationDate,marketDataAsOfUtc:`${information}:00Z`,usePurpose:'VALUATION'})}));
  }catch(caught){setError((caught as Error).message);}finally{setBusy(false);}
 }
 return <>
  <details className={`history-panel ${styles.reference}`}><summary>Help with pricing choices</summary><PricingPolicyHelp/></details>
  {dataOptions?<details className={`history-panel ${styles.reference}`}><summary>Available source definitions and permissions</summary><PolicySourceProfiles data={dataOptions}/></details>:dataError?<p role="status">{dataError}</p>:<p role="status">Loading recorded source definitions…</p>}
  <section className="history-panel"><h2>Inspect a saved version</h2><p>Explicit rules first: exact series → subject → venue + type → venue → type → broad rule. Flexible defaults apply only when no matching explicit rule exists. Missing eligible data never falls through to another rule.</p>
   <label>Policy version<select value={selected?.valuationPolicyId??''} disabled={busy} onChange={e=>{if(e.target.value)void selectPolicy(e.target.value);}}><option value="">Select a policy…</option>{policies.map(p=><option key={p.valuationPolicyId} value={p.valuationPolicyId}>{p.policyCode} · {p.displayName} · {p.valuationPolicyId.slice(-8)}</option>)}</select></label>
   <button type="button" disabled={busy} onClick={async()=>{setError('');try{setPolicies(await jsonRequest(`/api/market-data/valuation-policies?valuationDate=${valuationDate}`));}catch(caught){setError((caught as Error).message);}}}>Refresh versions for preview date</button>
   {selected?<p>{selected.policyCode} · version {selected.versionNo} · {selected.selectionMode} · {selected.strategyId?'Strategy scoped':'Tenant shared'} · {selected.createdByUserAccountId?'Attributed immutable version':'Legacy configuration'}</p>:null}
  </section>
  {!options.canManage?<section className="history-panel"><h2>Read-only configuration</h2><p>Creating a version requires a MARKET_DATA tenant administrator.</p>{selected?<pre>{JSON.stringify({selectionMode:selected.selectionMode,rules:selected.rules,defaultRules:selected.defaultRules},null,2)}</pre>:null}</section>:
   <form className={`history-panel pricing-policy-editor ${styles.editor}`} onSubmit={save}><h2>{selected?'Create a revised version':'Create pricing policy'}</h2><p>Save creates an immutable version. Preview uses the saved version, not unsaved edits. This does not grant data rights.</p>
    <fieldset disabled={busy}><legend>Policy identity and scope</legend><div className="pricing-policy-fields">
     <label>Policy code<input required maxLength={100} value={draft.policyCode} onChange={e=>setDraft({...draft,policyCode:e.target.value})}/></label>
     <label>Display name<input required maxLength={250} value={draft.displayName} onChange={e=>setDraft({...draft,displayName:e.target.value})}/></label>
     <label>Policy behaviour<select value={draft.selectionMode??'STRICT'} onChange={e=>setDraft(withPricingPolicyMode(draft,e.target.value as 'STRICT'|'FLEXIBLE'))}><option value="STRICT">Strict — explicit rules only</option><option value="FLEXIBLE">Flexible — Latest available EoD + overrides</option></select></label>
     <div><Pick label="Policy valuation context" required options={options.cuts} value={draft.valuationCutId} onChange={id=>setDraft({...draft,valuationCutId:id})}/><small>Identifies the policy context; it does not impose one closing time on every instrument. Exchange calendars or explicit rule pricing cuts determine the actual targets.</small></div>
     <Pick label="Strategy (optional)" options={options.strategies} value={draft.strategyId} onChange={id=>setDraft({...draft,strategyId:id||null})}/>
     <label>Effective from<input required type="date" value={draft.validFrom} onChange={e=>setDraft({...draft,validFrom:e.target.value})}/></label>
     <label>Effective to (optional)<input type="date" value={draft.validTo??''} onChange={e=>setDraft({...draft,validTo:e.target.value||null})}/></label>
    </div></fieldset>
    {draft.selectionMode==='FLEXIBLE'?<section aria-label="Latest available EoD default"><h3>Latest available EoD</h3><p>The initial default selects the eligible closing price for each listing’s expected exchange session. You do not enter a common closing hour: UK equities normally close at 16:30 London; French and US equities use their own exchange calendars, including early closes.</p><p>Explicit rules override defaults, for example FX at London 16:00. Missing expected-session prices fail unless you explicitly permit prior-session prices with a finite freshness allowance. Eligible source priorities, permissions and as-traded price checks still apply. Funds, FX and other subjects need their own suitable rules; this is not a last-intraday-print fallback.</p><p>The default rules below are the actual saved configuration and can be customised. Check compatibility before saving. No source rights are added.</p></section>:null}
    {allRules.map((rule,index)=><fieldset key={index} disabled={busy} className={styles.rule}>
     <legend>{index<explicitRules.length?'Explicit rule':'Flexible default'} {rule.ruleSequence}</legend>
     <p className={styles.ruleSummary}>{options.venues.find(item=>item.id===rule.marketVenueId)?.label??'Any venue'} · {options.instrumentTypes.find(item=>item.id===rule.instrumentTypeId)?.label??'Any instrument type'} · {priceFamilies.find(item=>item.id===rule.seriesType)?.label??rule.seriesType} · {({SESSION_CLOSE:'Exchange session close',NAMED_FIXING:'Named fixing',EXPLICIT_TIME:'Explicit local time',NAV_DATE:'Fund NAV dates',LEGACY:'Legacy date-only'})[rule.pricingConvention]}</p>
     <section className={styles.group} aria-labelledby={`scope-heading-${index}`}>
      <h3 id={`scope-heading-${index}`}>1. Applies to</h3>
      <p>Choose the instruments this rule covers. Blank filters apply broadly; more specific explicit rules take precedence.</p>
      <div className={`pricing-policy-fields ${styles.fields}`}><label>Rule priority<input type="number" required min={1} max={10000} value={rule.ruleSequence} onChange={e=>updateRule(index,{ruleSequence:Number(e.target.value)})}/></label>
<Pick label="Venue" options={options.venues} value={rule.marketVenueId} onChange={id=>updateRule(index,{marketVenueId:id||null})}/>
<Pick label="Instrument type" options={options.instrumentTypes} value={rule.instrumentTypeId} onChange={id=>updateRule(index,{instrumentTypeId:id||null})}/></div>
     </section>
     <section className={styles.group} aria-labelledby={`price-heading-${index}`}>
      <h3 id={`price-heading-${index}`}>2. Price and timing</h3>
      <div className={`pricing-policy-fields ${styles.fields}`}><PriceChoice label="What price or rate?" id={`family-${index}`} choices={priceFamilies} value={rule.seriesType} onChange={value=>updateRule(index,{seriesType:value??''})}/>
<label>When is the price taken?<select value={rule.pricingConvention} aria-describedby={`timing-${index}`} onChange={e=>updateRule(index,{pricingConvention:e.target.value as PricingRule['pricingConvention'],fixingCode:null,pricingCutId:null})}><option value="SESSION_CLOSE">Exchange session close</option><option value="NAMED_FIXING">Named fixing</option><option value="EXPLICIT_TIME">Explicit local time</option><option value="NAV_DATE">Fund NAV valuation dates</option><option value="LEGACY">Legacy date-only semantics</option></select><small id={`timing-${index}`}>Timing is separate from provider certification and price adjustments.</small></label>
{rule.pricingConvention==='NAMED_FIXING'||rule.pricingConvention==='EXPLICIT_TIME'?<Pick label="Rule pricing cut" required options={options.cuts} value={rule.pricingCutId} onChange={id=>updateRule(index,{pricingCutId:id||null})}/>:null}
{rule.pricingConvention==='NAMED_FIXING'?<label>Exact fixing code<input required maxLength={100} value={rule.fixingCode??''} onChange={e=>updateRule(index,{fixingCode:e.target.value})}/></label>:null}</div>
      <div className={styles.checks}>{rule.seriesType==='CLOSE'?<label><input type="checkbox" checked={rule.requireOfficialClose??false} onChange={e=>updateRule(index,{requireOfficialClose:e.target.checked})}/>Require exchange-official close<small>Leave unchecked to accept any recorded closing method. Unknown is not certified official. This does not change adjustments, timing or permissions.</small></label>:null}
{rule.seriesType==='CLOSE'&&rule.pricingConvention!=='LEGACY'?<><label><input type="checkbox" checked={rule.priceRequirement==='AS_TRADED'} onChange={e=>updateRule(index,{priceRequirement:e.target.checked?'AS_TRADED':null,allowSplitConversion:false,valueBasis:null})}/>As-traded valuation price<small>Match booked units. Original provider prices remain unchanged.</small></label><label><input type="checkbox" disabled={rule.priceRequirement!=='AS_TRADED'} checked={rule.allowSplitConversion??false} onChange={e=>updateRule(index,{allowSplitConversion:e.target.checked})}/>Allow verified conversion from split-adjusted data<small>Missing adjustment proof blocks valuation; this is not corporate-action position replay.</small></label></>:null}
{rule.seriesType==='FX_SPOT'&&['EXPLICIT_TIME','NAMED_FIXING'].includes(rule.pricingConvention)?<label><input type="checkbox" checked={rule.allowInverseFx??false} onChange={e=>updateRule(index,{allowInverseFx:e.target.checked})}/>Permit reciprocal FX conversion<small>Direct pairs remain preferred. Never silently triangulates through a third currency.</small></label>:null}</div>
      {rule.pricingConvention==='SESSION_CLOSE'?<p>Targets the selected listing’s actual close, including early closes. Never guesses a listing for a canonical instrument or certifies a provider bar as an official tape.</p>:rule.pricingConvention==='LEGACY'?<p>Legacy rules retain weekday-based date arithmetic. Composite time and value-basis filters are not supported in this mode.</p>:null}
     </section>
     <section className={styles.group} aria-labelledby={`freshness-heading-${index}`}>
      <h3 id={`freshness-heading-${index}`}>3. Freshness and missing data</h3>
      <div className={`pricing-policy-fields ${styles.fields}`}><label>Which pricing date?<select value={rule.pricingDateRule??'SAME_DAY'} onChange={e=>updateRule(index,{pricingDateRule:e.target.value as PricingRule['pricingDateRule'],lagBusinessDays:0})}><option value="SAME_DAY">Expected session for this date</option><option value="PRIOR_AVAILABLE">Latest available expected session — with explicit limit</option><option value="FIXED_LAG">A specified number of sessions earlier</option></select></label>
{rule.pricingDateRule==='FIXED_LAG'?<label>Lag (trading sessions)<input required type="number" min={0} max={366} value={rule.lagBusinessDays??0} onChange={e=>updateRule(index,{lagBusinessDays:Number(e.target.value)})}/></label>:null}
<label>Maximum staleness (sessions)<input required={index>=explicitRules.length} type="number" min={0} max={366} placeholder={index>=explicitRules.length?'Finite allowance required':'No fixed limit (not valuation-ready)'} value={rule.maxStalenessBusinessDays??''} onChange={e=>{try{updateRule(index,{maxStalenessBusinessDays:stalenessLimit(e.target.value)});}catch(caught){setError((caught as Error).message);}}}/></label>
<label>Missing data action<select value={rule.missingDataAction??'FAIL'} onChange={e=>updateRule(index,{missingDataAction:e.target.value as PricingRule['missingDataAction']})}><option value="FAIL">Fail</option><option value="WARN">Warn (no fabricated value)</option><option value="MANUAL_OVERRIDE">Request manual override</option></select></label></div>
     </section>
     <details className={styles.advanced}>
      <summary>Advanced settings <span>{[rule.datasetId?'Dataset override':null,rule.marketCalendarId?'Calendar override':null,rule.subjectType?'Subject type':null,rule.subjectReferenceNodeId?'Exact subject':null,rule.marketDataSeriesId?'Exact series':null,rule.valueBasis?`Adjustment: ${rule.valueBasis}`:null].filter(Boolean).join(' · ')||'Optional source and exact-match filters'}</span></summary>
      <p>These settings further restrict this rule. Existing values remain active when this section is closed.</p>
      <div className={`pricing-policy-fields ${styles.fields}`}><Pick label="Source dataset (blank follows eligible source priority)" options={options.datasets} value={rule.datasetId} onChange={id=>updateRule(index,{datasetId:id||null})}/>
<Pick label="Calendar override" options={options.calendars} value={rule.marketCalendarId} onChange={id=>updateRule(index,{marketCalendarId:id||null})}/>
<label>Subject type (optional)<input maxLength={50} placeholder="LISTING, FX_PAIR, INSTRUMENT…" value={rule.subjectType??''} onChange={e=>updateRule(index,{subjectType:e.target.value||null})}/></label></div>
      <details><summary>Advanced source adjustment filter</summary><PriceChoice label="Price adjustments" id={`adjustment-${index}`} choices={adjustmentChoices} value={rule.valueBasis} onChange={value=>updateRule(index,{valueBasis:value})}/></details>
      <details><summary>Exact subject / series filters</summary><div className="pricing-policy-fields"><label>Subject reference UUID<input value={rule.subjectReferenceNodeId??''} onChange={e=>updateRule(index,{subjectReferenceNodeId:e.target.value||null})}/></label><label>Series UUID<input value={rule.marketDataSeriesId??''} onChange={e=>updateRule(index,{marketDataSeriesId:e.target.value||null})}/></label></div></details>
      {dataOptions?<PolicyRuleSources data={dataOptions} seriesType={rule.seriesType} requireOfficialClose={rule.requireOfficialClose} valueBasis={rule.valueBasis} datasetId={rule.datasetId}/>:null}
     </details>
     <div className={styles.ruleActions}><button type="button" disabled={index<explicitRules.length?draft.selectionMode!=='FLEXIBLE'&&explicitRules.length===1:defaultRules.length===1} onClick={()=>setDraft(index<explicitRules.length?{...draft,rules:explicitRules.filter((_,i)=>i!==index)}:{...draft,defaultRules:defaultRules.filter((_,i)=>i!==index-explicitRules.length)})}>Remove rule</button></div>
    </fieldset>)}
    <button type="button" disabled={busy||allRules.length>=50} onClick={()=>setDraft({...draft,rules:[...explicitRules,newPricingRule(nextSequence())]})}>Add explicit rule</button> {draft.selectionMode==='FLEXIBLE'?<button type="button" disabled={busy||allRules.length>=50} onClick={()=>setDraft({...draft,defaultRules:[...defaultRules,newDefaultPricingRule(nextSequence())]})}>Add default rule</button>:null}
    <button type="button" disabled={busy} onClick={()=>void checkCompatibility()}>Check data compatibility</button>
    {currentReport?<PolicyCompatibilityReport report={currentReport}/>:null}
    {currentReport?.status==='ACTION_REQUIRED'?<label><input type="checkbox" disabled={busy} checked={acknowledgedCanonical===canonicalDraft} onChange={e=>setAcknowledgedCanonical(e.target.checked?canonicalDraft:null)}/>Save a future-data configuration despite these notices. This does not make it valuation-ready.</label>:null}
    <button disabled={busy} type="submit">{busy?'Working…':'Save new immutable version'}</button>
   </form>}
  <form className="history-panel" onSubmit={runPreview}><h2>Read-only preview</h2><p>One information cutoff controls receipt/revisions; each rule has its own pricing target. No snapshot, observation, trade or valuation is written.</p><fieldset disabled={busy}><legend>Saved-version preview context</legend><div className="pricing-policy-fields"><label>Valuation date<input required type="date" value={valuationDate} onChange={e=>{setValuationDate(e.target.value);setPreview(null);}}/></label><label>Information cutoff (UTC)<input required type="datetime-local" value={information} onChange={e=>{setInformation(e.target.value);setPreview(null);}}/></label></div><label>Listing / reference UUIDs (up to 50)<textarea required rows={3} value={subjects} onChange={e=>{setSubjects(e.target.value);setPreview(null);}}/></label><button type="submit" disabled={!selected}>Preview saved version</button></fieldset>
   <p>Yahoo daily bars are not named FX fixings. Selection requires NON_DISPLAY rights; personal DISPLAY access alone is insufficient. Package calendars are labelled non-authoritative.</p>
  </form>
  {error?<p className="error-panel" role="alert">{error}</p>:null}{message?<p role="status">{message}</p>:null}
  {preview?<section className="history-panel" aria-live="polite"><h2>Preview: {preview.status}</h2>{preview.items.map(item=><article key={item.subjectReferenceNodeId}><h3>{item.status} · {item.subjectReferenceNodeId}</h3><p>{item.selectedValue??'No eligible value'} · {item.entitlementDecision} · {item.exceptionCode??item.selectionReason}</p><p>{pricingEvidenceLabel(item.pricingEvidence)}</p><p>Requested {item.pricingDateRequested??'—'} / used {item.pricingDateUsed??'—'} · {item.stalenessStatus}</p><details><summary>Input and target evidence</summary><pre>{JSON.stringify(item,null,2)}</pre></details></article>)}</section>:null}
 </>;
}
