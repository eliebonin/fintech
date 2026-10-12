"use client";
import {useEffect,useRef,useState,type FormEvent} from 'react';
import Link from 'next/link';
import type {ReferenceNodeOption} from 'api-contracts';
import type {ActiveValuationPolicy,MarketDataResolutionCreate} from '@/lib/market-data-resolution';
import {previewSubjects,pricingEvidenceLabel,type PricingPolicy,type PricingOptions,type PricingPreview} from '@/lib/pricing-policy';
import {coverageRows,coverageTotals} from '@/lib/market-data-coverage';
import styles from './market-data-workspace.module.css';
async function read<T>(url:string,signal:AbortSignal,init?:RequestInit):Promise<T>{
 const response=await fetch(url,{...init,signal,cache:'no-store'});
 if(!response.ok)throw new Error(response.status===403?'Current permissions do not allow this check.':response.status===409?'The active tenant changed. Reopen coverage for the current tenant.':'The data check service is unavailable or rejected this context. Retry or review the policy.');
 return response.json();
}
export function MarketDataCoverage({tenantId,initialReferences='',initialDate,initialCutoff}:{tenantId:string;initialReferences?:string;initialDate:string;initialCutoff:string}){
 const [references,setReferences]=useState(initialReferences),[date,setDate]=useState(initialDate),[cutoff,setCutoff]=useState(initialCutoff);
 const [policies,setPolicies]=useState<ActiveValuationPolicy[]>([]),[options,setOptions]=useState<PricingOptions|null>(null),[policyId,setPolicyId]=useState(''),[strategy,setStrategy]=useState('');
 const [busy,setBusy]=useState(false),[loading,setLoading]=useState(true),[error,setError]=useState(''),[query,setQuery]=useState(''),[choices,setChoices]=useState<ReferenceNodeOption[]>([]),[searchError,setSearchError]=useState(''),[names,setNames]=useState<Record<string,string>>({});
 const [result,setResult]=useState<{request:MarketDataResolutionCreate;preview:PricingPreview;policyLabel:string}|null>(null),[showAll,setShowAll]=useState(false),[reload,setReload]=useState(0);
 const current=useRef<AbortController|null>(null),generation=useRef(0);
 function invalidate(){generation.current++;current.current?.abort();setResult(null);setError('');setBusy(false);}
 useEffect(()=>{let live=true;const controller=new AbortController();setLoading(true);setPolicies([]);setOptions(null);setPolicyId('');setResult(null);const timeout=setTimeout(()=>{if(live){controller.abort();setError('Policy choices timed out. Retry configuration.');setLoading(false);}},12000);
  Promise.all([read<ActiveValuationPolicy[]>(`/api/market-data/valuation-policies?valuationDate=${encodeURIComponent(date)}`,controller.signal),read<PricingOptions>('/api/market-data/valuation-policy-options',controller.signal)])
   .then(([p,o])=>{if(!controller.signal.aborted){setPolicies(p);setOptions(o);setPolicyId(p[0]?.valuationPolicyId??'');setError('');}})
   .catch(()=>{if(live&&!controller.signal.aborted)setError('Policy choices could not be loaded. Retry configuration.');})
   .finally(()=>{clearTimeout(timeout);if(live)setLoading(false);});
  return()=>{live=false;clearTimeout(timeout);controller.abort();};
 },[date,tenantId,reload]);
 useEffect(()=>{const controller=new AbortController();setChoices([]);setSearchError('');if(query.trim().length<2)return()=>controller.abort();
  const timer=setTimeout(()=>{const timeout=setTimeout(()=>controller.abort(),12000);read<{data:ReferenceNodeOption[]}>(`/api/market-data/references?q=${encodeURIComponent(query)}`,controller.signal)
   .then(value=>{if(!controller.signal.aborted)setChoices(value.data);}).catch(()=>{if(!controller.signal.aborted)setSearchError('Reference search is unavailable. You can enter explicit IDs below.');}).finally(()=>clearTimeout(timeout));},300);
  return()=>{clearTimeout(timer);controller.abort();};
 },[query,tenantId]);
 useEffect(()=>()=>{generation.current++;current.current?.abort();},[]);
 function addReference(item:ReferenceNodeOption){invalidate();setReferences(value=>[...new Set([...value.split(/[\s,]+/).filter(Boolean),item.referenceNodeId])].join('\n'));setNames(value=>({...value,[item.referenceNodeId]:item.canonicalName}));setQuery('');}
 async function submit(event:FormEvent<HTMLFormElement>){
  event.preventDefault();invalidate();const ticket=++generation.current,controller=new AbortController();current.current=controller;setBusy(true);const timeout=setTimeout(()=>controller.abort(),30000);
  try{
   const required=[...new Set(previewSubjects(references).map(id=>id.toLowerCase()))];
   const active=await read<{tenantId:string}>('/api/session/active-tenant',controller.signal);
   if(active.tenantId!==tenantId)throw new Error('The active tenant changed. Reopen coverage.');
   const policy=await read<PricingPolicy>(`/api/market-data/valuation-policies/${encodeURIComponent(policyId)}`,controller.signal);
   const request:MarketDataResolutionCreate={subjectReferenceNodeIds:required,valuationPolicyId:policyId,valuationCutId:policy.valuationCutId,strategyId:policy.strategyId??(strategy||null),valuationDate:date,marketDataAsOfUtc:`${cutoff}:00Z`,usePurpose:'VALUATION'};
   const preview=await read<PricingPreview>('/api/market-data/resolution-preview',controller.signal,{method:'POST',headers:{'Content-Type':'application/json','X-Expected-Tenant-Id':tenantId},body:JSON.stringify(request)});
   const stillActive=await read<{tenantId:string}>('/api/session/active-tenant',controller.signal);
   if(stillActive.tenantId!==tenantId)throw new Error('The active tenant changed. Reopen coverage.');
   if(ticket===generation.current){setResult({request,preview,policyLabel:`${policy.policyCode} · version ${policy.versionNo}`});setShowAll(false);}
  }catch(e){if(ticket===generation.current)setError(controller.signal.aborted?'Coverage check timed out. No result or snapshot was saved.':(e as Error).message);}
  finally{clearTimeout(timeout);if(ticket===generation.current)setBusy(false);}
 }
 const rows=result?coverageRows(result.request.subjectReferenceNodeIds,result.preview.items):[],totals=coverageTotals(rows);
 const visible=showAll?rows:rows.filter(row=>row.state!=='selected');
 return <div className={styles.content}>
  <form className={`history-panel ${styles.panel}`} onSubmit={submit}>
   <h2>Required inputs</h2><p>This check covers only the references listed below. It does not infer every holding in a strategy or certify a complete universe. For listed prices, select the exact venue listing.</p>
   <fieldset disabled={busy}><legend>Scope and pricing context</legend>
    <div className={styles.fields}>
     <label>Valuation date<input type="date" required value={date} onChange={e=>{invalidate();setDate(e.target.value);}}/></label>
     <label>Information cutoff (UTC)<input type="datetime-local" required value={cutoff} onChange={e=>{invalidate();setCutoff(e.target.value);}}/></label>
     <label>Pricing policy<select required disabled={loading} value={policyId} onChange={e=>{invalidate();setPolicyId(e.target.value);}}><option value="">{loading?'Loading policies…':'Choose an active policy'}</option>{policies.map(p=><option key={p.valuationPolicyId} value={p.valuationPolicyId}>{p.policyCode} · {p.displayName}</option>)}</select></label>
     <label>Strategy context (optional)<select value={strategy} onChange={e=>{invalidate();setStrategy(e.target.value);}}><option value="">Use policy scope</option>{options?.strategies.map(s=><option key={s.id} value={s.id}>{s.label}</option>)}</select><small>A strategy-specific policy uses its saved scope. This choice does not load the strategy’s holdings.</small></label>
    </div>
    <label className={styles.scope}>Find a required reference<input type="search" value={query} maxLength={250} onChange={e=>setQuery(e.target.value)} placeholder="Search instrument or listing name…"/><small>Search uses reference data, so an input can be selected even when no price exists.</small></label>
    {searchError?<p role="status">{searchError}</p>:null}
    {choices.length?<ul className="ticket-options">{choices.map(choice=><li key={choice.referenceNodeId}><button type="button" onClick={()=>addReference(choice)}>{choice.canonicalName} · {choice.nodeType}{choice.marketVenueMic?` · ${choice.marketVenueMic}`:''}</button></li>)}</ul>:null}
    <label className={styles.scope}>Required listing/reference IDs — 1 to 50<textarea required value={references} onChange={e=>{invalidate();setReferences(e.target.value);}} placeholder="Select references above, or paste IDs separated by commas or new lines."/></label>
    {Object.keys(names).length?<p className="muted">Selected names: {Object.entries(names).filter(([id])=>references.includes(id)).map(([,name])=>name).join(', ')}</p>:null}
    <button type="submit" disabled={loading||!policyId}>{busy?'Checking inputs…':'Check required inputs'}</button> <button type="button" onClick={()=>{invalidate();setReload(value=>value+1);}}>Reload policy choices</button>
   </fieldset>
   <p className="muted">Read-only: no observation, snapshot, policy or valuation result is saved. Changing the context clears the previous assessment.</p>
  </form>
  {error?<p role="alert" className="error-panel">{error}</p>:null}
  {!result?<section className={styles.panel}><h2>Not checked</h2><p>Choose the inputs and pricing context, then run a check. No readiness is inferred from source access or stored observations.</p></section>:<section aria-live="polite">
   <div className={styles.metrics}><div className={styles.metric}><span>Required inputs</span><strong>{totals.required}</strong><p>Explicit request denominator</p></div><div className={styles.metric}><span>Selected by policy</span><strong>{totals.selected}</strong><p>For this date and cutoff; not a complete valuation certification</p></div><div className={styles.metric}><span>Needs attention / unknown</span><strong>{totals.exceptions} / {totals.unknown}</strong><p>Missing inputs stay in the count</p></div></div>
   <div className={styles.panel}><h2>Coverage results</h2><p>{result.policyLabel} · valuation date {result.request.valuationDate} · information cutoff {result.request.marketDataAsOfUtc}</p><label><input type="checkbox" checked={showAll} onChange={e=>setShowAll(e.target.checked)}/>Show all required inputs</label>{!visible.length?<p>No exceptions reported for these explicit inputs. Show all inputs to inspect the selection evidence.</p>:null}</div>
   {visible.length?<div className={styles.tableScroll}><table className={styles.table}><thead><tr><th>Required reference</th><th>Assessment</th><th>Expected / used date</th><th>Selected input</th><th>Reason and next step</th></tr></thead><tbody>{visible.map(row=><tr key={row.id}>
    <td><strong>{names[row.id]??row.id}</strong><small>{names[row.id]?row.id:''}</small><Link href={`/market-data/explorer?referenceNodeId=${encodeURIComponent(row.id)}&toDate=${result.request.valuationDate}`}>Inspect stored history</Link></td>
    <td><span className={`${styles.status} ${styles[row.state]}`}>{row.state==='selected'?'Selected by policy':row.state==='unknown'?'Unknown / unresolved':row.item?.status??'Needs attention'}</span><small>{row.item?.entitlementDecision??'Not evaluated'}</small></td>
    <td>{row.item?.pricingDateRequested??'Not assessed'} / {row.item?.pricingDateUsed??'No selected date'}<small>{row.item?.stalenessStatus??'Not assessed'}</small></td>
    <td>{row.state==='selected'?String(row.item?.selectedValue):'—'}<small>{row.state==='selected'?row.item?.datasetId:'No usable input certified'}</small></td>
    <td>{row.item?.exceptionCode??row.item?.selectionReason??'No assessment was returned for this required input.'}<p><Link href="/market-data/policies">Review policy</Link> · <Link href="/market-data/sources">Review source access</Link> · <Link href="/market-data/calendars">Review calendars</Link></p>{row.item?<details><summary>Selection evidence</summary><p>{pricingEvidenceLabel(row.item.pricingEvidence)}</p><pre>{JSON.stringify(row.item,null,2)}</pre></details>:null}</td>
   </tr>)}</tbody></table></div>:null}
  </section>}
 </div>;
}
