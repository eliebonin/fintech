'use client';
import {browserFetch as fetch} from '@/lib/browser-fetch';
import {useEffect,useRef,useState,type FormEvent} from 'react';
import {InputEvidence} from './input-evidence';
import {valuationError} from '@/lib/daily-valuation-request';
import {componentLabel,displayAmount} from './presentation';
import {ReferenceName,TechnicalReference} from './technical-reference';
import type {Presentation} from './types';
import {positionContext} from './ops-review-model';

type Item={attribution_id:string;version:number;subject_id?:string|null;cash_account_id?:string|null;market_pnl:string;gross_pnl?:string;net_pnl?:string;components:Record<string,string>;evidence:unknown};
type Batch={batch_id:string;status:string;staged_by:string;summary:{marketPnl:string;grossPnl?:string;netPnl?:string;scope:string};items:Item[]};
type Request={request_id:string;status:string;requested_by:string;component:string;amount:string;reason:string;source_reference:string;review_comment?:string};
async function api<T>(path:string,init?:RequestInit){
 const response=await fetch(`/api/valuation/${path}`,{...init,cache:'no-store'});const data=await response.json();
 if(!response.ok)throw valuationError(response,data);return data as T;
}

/** Immutable candidate IDs scope every action. No optimistic financial edits. */
export function ReviewWorkspace({batch,actorId,canRequest,canReview,onApproved,onOpenInputs,onRequestsChanged,compact=false,positionLabels={},presentation}:{batch:Batch;actorId:string;canRequest:boolean;canReview:boolean;onApproved:(attemptId:string)=>void;onOpenInputs?:()=>void;onRequestsChanged?:()=>void;compact?:boolean;positionLabels?:Record<string,string>;presentation?:Presentation}){
 const [requests,setRequests]=useState<Request[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const [frozen,setFrozen]=useState<{key:string;body:Record<string,string>}|null>(null);
 const [filter,setFilter]=useState('ALL'),[loaded,setLoaded]=useState(false);
 const live=useRef(false);
 useEffect(()=>{live.current=true;return()=>{live.current=false;};},[]);
 const writable=canRequest&&batch.status==='STAGED';
 const reviewable=canReview&&batch.status==='STAGED';
 useEffect(()=>{let live=true;setRequests([]);setError('');setFrozen(null);setLoaded(false);
  api<{items:Request[]}>(`batches/${batch.batch_id}/amendments`).then(r=>{if(live){setRequests(r.items);setLoaded(true);}}).catch(e=>{if(live)setError((e as Error).message);});
  return()=>{live=false;};},[batch.batch_id]);
 async function refresh(){const rows=await api<{items:Request[]}>(`batches/${batch.batch_id}/amendments`);if(live.current){setRequests(rows.items);setLoaded(true);}}
 async function submit(event:FormEvent<HTMLFormElement>){
  event.preventDefault();const form=event.currentTarget;const body=Object.fromEntries(new FormData(form)) as Record<string,string>;
  const ticket=frozen??{key:crypto.randomUUID(),body};setFrozen(ticket);setBusy(true);setError('');
  try{await api(`batches/${batch.batch_id}/amendments`,{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':ticket.key},body:JSON.stringify(ticket.body)});if(!live.current)return;setFrozen(null);form.reset();await refresh();onRequestsChanged?.();}
  catch(e){if(live.current)setError((e as Error).message);}finally{if(live.current)setBusy(false);}
 }
 async function decide(event:FormEvent<HTMLFormElement>,id:string,decision:'approve'|'reject'){
  event.preventDefault();const comment=String(new FormData(event.currentTarget).get('comment'));setBusy(true);setError('');
  try{const result=await api<{status:string;batch?:{attempt_id:string}}>(`amendments/${id}/${decision}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({comment})});
   if(!live.current)return;if(result.batch)onApproved(result.batch.attempt_id);else {await refresh();onRequestsChanged?.();}}
  catch(e){if(live.current)setError((e as Error).message);}finally{if(live.current)setBusy(false);}
 }
 return <section className={compact?'pnl-surface pnl-amendments':''} aria-label="Economic P&L review"><div className="pnl-panel-heading"><h3>{compact?'Amendment requests':'Economic components'}</h3><span className="pnl-status">{requests.filter(r=>r.status==='PENDING').length} pending</span></div><p className="pnl-muted">Changes are requests, not direct edits. Approval creates a new immutable candidate.</p>
  {!compact?<><p>Scope: {batch.summary.scope}. Recorded inputs only—not complete fund NAV or proof that every unbooked income/cost has been captured.</p>
  <dl><dt>Market P&amp;L</dt><dd>{batch.summary.marketPnl}</dd><dt>Gross P&amp;L</dt><dd>{batch.summary.grossPnl??batch.summary.marketPnl}</dd><dt>Net P&amp;L</dt><dd>{batch.summary.netPnl??batch.summary.marketPnl}</dd></dl>
  {batch.items.map(item=><details key={item.attribution_id}><summary>Components · {item.subject_id??item.attribution_id} · v{item.version}</summary>
   <table><thead><tr><th>Component</th><th>Reporting amount</th></tr></thead><tbody>{Object.entries(item.components).map(([name,amount])=><tr key={name}><th>{name}</th><td>{amount}</td></tr>)}</tbody></table><InputEvidence evidence={item.evidence}/></details>)}</>:null}
  {error?<p role="alert">{error}</p>:null}
  {writable?<><details className="pnl-request-form" open={Boolean(frozen)}><summary>Request component change</summary><p>Enter a signed delta in the reporting currency. Approval creates a new candidate; market/FX/accrual corrections require source correction and recalculation.</p>
   <form onSubmit={submit}><fieldset disabled={busy||Boolean(frozen)}>
    <label>Attribution<select name="attributionId" required>{batch.items.map((i,index)=><option key={i.attribution_id} value={i.attribution_id}>{i.cash_account_id?presentation?.cashAccounts?.[i.cash_account_id]??'Cash account name unavailable':positionLabels[i.subject_id??'']??'Instrument name unavailable'} · {positionContext(i,presentation)||`Position ${index+1}`} · v{i.version}</option>)}</select></label>
    <label>Component<select name="component" defaultValue="ADJUSTMENT">{['ADJUSTMENT','DIVIDEND','RESET','CASHFLOW','BROKER_FEE','CUSTODY_FEE','MANAGEMENT_FEE','PERFORMANCE_FEE','TAX','OTHER_COST'].map(name=><option key={name} value={name}>{componentLabel(name)}</option>)}</select></label>
    <label>Signed amount<input name="amount" required inputMode="decimal" pattern="-?[0-9]+(\.[0-9]{1,12})?"/></label>
    <label>Reason<textarea name="reason" required maxLength={2000}/></label><label>Source reference<input name="sourceReference" required maxLength={500}/></label></fieldset>
    <button disabled={busy||batch.items.length===0}>{frozen?'Retry unchanged request':'Submit change request'}</button>
    {frozen?<><p role="status">This request is frozen for safe retries. Check request history before starting another.</p><button type="button" disabled={busy} onClick={()=>setFrozen(null)}>Start a different request</button></>:null}</form></details>
   <details><summary>Correct source inputs</summary><p>Correct daily accrued-interest inputs in the input register, or correct the original booked trade/flow. Then calculate and stage a replacement. Do not amend PRICE, FX or ACCRUAL manually.</p><button type="button" onClick={onOpenInputs} disabled={!onOpenInputs}>Open daily input register</button></details></>:<p>Component requests require calculation permission and a staged result. Published financial versions cannot be edited; corrections require a new staged calculation.</p>}
  <h4>Amendment history</h4><button disabled={busy} onClick={()=>refresh().then(()=>onRequestsChanged?.()).catch(e=>setError((e as Error).message))}>Refresh requests</button>
  <div className="pnl-request-filters" aria-label="Filter amendment requests">{['ALL','PENDING','APPLIED','REJECTED','STALE'].map(status=><button key={status} type="button" aria-pressed={filter===status} onClick={()=>setFilter(status)}>{status.toLowerCase()} ({status==='ALL'?requests.length:requests.filter(r=>r.status===status).length})</button>)}</div>
  {!loaded?<p role="status">{error?'Requests could not be loaded. Retry refresh.':'Loading requests…'} Publication rechecks pending requests on the server.</p>:requests.filter(r=>filter==='ALL'||r.status===filter).length===0?<p>No {filter==='ALL'?'':filter.toLowerCase()+' '}requests. Publication rechecks pending requests on the server.</p>:<ul className="pnl-request-list">{requests.filter(r=>filter==='ALL'||r.status===filter).map(r=><li key={r.request_id}><div className="pnl-panel-heading"><span className={`pnl-status pnl-status-${r.status.toLowerCase()}`}>{r.status}</span><strong title={r.amount}>{displayAmount(r.amount)}</strong></div><p>{componentLabel(r.component)} · signed delta</p><p>{r.reason}</p><details><summary>Request evidence</summary><dl><dt>Source reference</dt><dd>{r.source_reference}</dd><dt>Requested by</dt><dd><ReferenceName id={r.requested_by} label={presentation?.users[r.requested_by]} fallback="Requesting user name unavailable"/></dd><dt>Request ID</dt><dd><TechnicalReference id={r.request_id}/></dd>{r.review_comment?<><dt>Decision comment</dt><dd>{r.review_comment}</dd></>:null}</dl></details>
   {reviewable&&r.status==='PENDING'?(r.requested_by===actorId?<p>An independent reviewer must decide this request.</p>:<form onSubmit={event=>decide(event,r.request_id,(event.nativeEvent as SubmitEvent).submitter?.getAttribute('value')==='reject'?'reject':'approve')}><label>Review explanation<textarea name="comment" required maxLength={2000}/></label><button disabled={busy} value="approve">Approve and stage replacement</button><button disabled={busy} value="reject">Reject request</button></form>):null}</li>)}</ul>}
 </section>;
}
