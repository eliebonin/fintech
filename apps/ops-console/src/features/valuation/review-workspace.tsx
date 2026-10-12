'use client';
import {useEffect,useRef,useState,type FormEvent} from 'react';
import {InputEvidence} from './input-evidence';
import {valuationError} from '@/lib/daily-valuation-request';

type Item={attribution_id:string;version:number;subject_id?:string|null;market_pnl:string;gross_pnl?:string;net_pnl?:string;components:Record<string,string>;evidence:unknown};
type Batch={batch_id:string;status:string;staged_by:string;summary:{marketPnl:string;grossPnl?:string;netPnl?:string;scope:string};items:Item[]};
type Request={request_id:string;status:string;requested_by:string;component:string;amount:string;reason:string;source_reference:string;review_comment?:string};
async function api<T>(path:string,init?:RequestInit){
 const response=await fetch(`/api/valuation/${path}`,{...init,cache:'no-store'});const data=await response.json();
 if(!response.ok)throw valuationError(response,data);return data as T;
}

/** Immutable candidate IDs scope every action. No optimistic financial edits. */
export function ReviewWorkspace({batch,actorId,canRequest,canReview,onApproved}:{batch:Batch;actorId:string;canRequest:boolean;canReview:boolean;onApproved:(attemptId:string)=>void}){
 const [requests,setRequests]=useState<Request[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const [frozen,setFrozen]=useState<{key:string;body:Record<string,string>}|null>(null);
 const live=useRef(false);
 useEffect(()=>{live.current=true;return()=>{live.current=false;};},[]);
 const writable=canRequest&&batch.status==='STAGED';
 const reviewable=canReview&&batch.status==='STAGED';
 useEffect(()=>{let live=true;setRequests([]);setError('');setFrozen(null);
  api<{items:Request[]}>(`batches/${batch.batch_id}/amendments`).then(r=>{if(live)setRequests(r.items);}).catch(e=>{if(live)setError((e as Error).message);});
  return()=>{live=false;};},[batch.batch_id]);
 async function refresh(){const rows=await api<{items:Request[]}>(`batches/${batch.batch_id}/amendments`);if(live.current)setRequests(rows.items);}
 async function submit(event:FormEvent<HTMLFormElement>){
  event.preventDefault();const form=event.currentTarget;const body=Object.fromEntries(new FormData(form)) as Record<string,string>;
  const ticket=frozen??{key:crypto.randomUUID(),body};setFrozen(ticket);setBusy(true);setError('');
  try{await api(`batches/${batch.batch_id}/amendments`,{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':ticket.key},body:JSON.stringify(ticket.body)});if(!live.current)return;setFrozen(null);form.reset();await refresh();}
  catch(e){if(live.current)setError((e as Error).message);}finally{if(live.current)setBusy(false);}
 }
 async function decide(event:FormEvent<HTMLFormElement>,id:string,decision:'approve'|'reject'){
  event.preventDefault();const comment=String(new FormData(event.currentTarget).get('comment'));setBusy(true);setError('');
  try{const result=await api<{status:string;batch?:{attempt_id:string}}>(`amendments/${id}/${decision}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({comment})});
   if(!live.current)return;if(result.batch)onApproved(result.batch.attempt_id);else await refresh();}
  catch(e){if(live.current)setError((e as Error).message);}finally{if(live.current)setBusy(false);}
 }
 return <section aria-label="Economic P&L review"><h3>Economic components</h3><p>Scope: {batch.summary.scope}. Recorded inputs only—not complete fund NAV or proof that every unbooked income/cost has been captured.</p>
  <dl><dt>Market P&amp;L</dt><dd>{batch.summary.marketPnl}</dd><dt>Gross P&amp;L</dt><dd>{batch.summary.grossPnl??batch.summary.marketPnl}</dd><dt>Net P&amp;L</dt><dd>{batch.summary.netPnl??batch.summary.marketPnl}</dd></dl>
  {batch.items.map(item=><details key={item.attribution_id}><summary>Components · {item.subject_id??item.attribution_id} · v{item.version}</summary>
   <table><thead><tr><th>Component</th><th>Reporting amount</th></tr></thead><tbody>{Object.entries(item.components).map(([name,amount])=><tr key={name}><th>{name}</th><td>{amount}</td></tr>)}</tbody></table><InputEvidence evidence={item.evidence}/></details>)}
  {error?<p role="alert">{error}</p>:null}
  {writable?<><h4>Request component change</h4><p>Enter a signed delta in the reporting currency. Approval creates a new candidate; market/FX/accrual corrections require source correction and recalculation.</p>
   <form onSubmit={submit}><fieldset disabled={busy||Boolean(frozen)}>
    <label>Position<select name="attributionId" required>{batch.items.map(i=><option key={i.attribution_id} value={i.attribution_id}>{i.subject_id??i.attribution_id} · v{i.version}</option>)}</select></label>
    <label>Component<select name="component" defaultValue="ADJUSTMENT">{['ADJUSTMENT','DIVIDEND','RESET','CASHFLOW','BROKER_FEE','CUSTODY_FEE','MANAGEMENT_FEE','PERFORMANCE_FEE','TAX','OTHER_COST'].map(name=><option key={name}>{name}</option>)}</select></label>
    <label>Signed amount<input name="amount" required inputMode="decimal" pattern="-?[0-9]+(\.[0-9]{1,12})?"/></label>
    <label>Reason<textarea name="reason" required maxLength={2000}/></label><label>Source reference<input name="sourceReference" required maxLength={500}/></label></fieldset>
    <button disabled={busy||batch.items.length===0}>{frozen?'Retry unchanged request':'Submit change request'}</button>
    {frozen?<button type="button" disabled={busy} onClick={()=>setFrozen(null)}>Start a different request</button>:null}</form>
   <details><summary>Correct source inputs</summary><p>Correct daily accrued-interest inputs in the input register, or correct the original booked trade/flow. Then calculate and stage a replacement. Do not amend PRICE, FX or ACCRUAL manually.</p><a href="#valuation-input-register">Open daily input register</a></details></>:<p>Component requests require calculation permission and a staged result. Published financial versions cannot be edited; corrections require a new staged calculation.</p>}
  <h4>Amendment history</h4><button disabled={busy} onClick={()=>refresh().catch(e=>setError((e as Error).message))}>Refresh requests</button>
  {requests.length===0?<p>No requests loaded. Publication rechecks pending requests on the server.</p>:<ul>{requests.map(r=><li key={r.request_id}>{r.status} · {r.component} {r.amount} · {r.reason} · {r.source_reference}{r.review_comment?` · ${r.review_comment}`:''}
   {reviewable&&r.status==='PENDING'?(r.requested_by===actorId?<p>An independent reviewer must decide this request.</p>:<form onSubmit={event=>decide(event,r.request_id,(event.nativeEvent as SubmitEvent).submitter?.getAttribute('value')==='reject'?'reject':'approve')}><label>Review explanation<textarea name="comment" required maxLength={2000}/></label><button disabled={busy} value="approve">Approve and stage replacement</button><button disabled={busy} value="reject">Reject request</button></form>):null}</li>)}</ul>}
 </section>;
}
