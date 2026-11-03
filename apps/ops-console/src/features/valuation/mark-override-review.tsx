'use client';
import {useEffect,useRef,useState,type FormEvent} from 'react';
import type {components} from 'api-contracts';
import {browserFetch} from '@/lib/browser-fetch';
import {valuationError} from '@/lib/daily-valuation-request';
import {useRetainedNavigation} from '@/lib/use-retained-navigation';
import type {Batch} from './types';
import {TechnicalReference} from './technical-reference';

type Review=components['schemas']['MarkOverrideReviewView'];
type Gap=components['schemas']['MarkGapView'];
type Create=components['schemas']['MarkOverrideCreate'];
type Ticket={path:string;key:string;body:Create|{comment:string}};
async function api<T>(path:string,init?:RequestInit):Promise<T>{
 const response=await browserFetch(`/api/valuation/${path}`,{...init,cache:'no-store'});
 const body=await response.json();if(!response.ok)throw valuationError(response,body);return body as T;
}

function RequestForm({gap,batch,busy,submit}:{gap:Gap;batch:Batch;busy:boolean;submit:(form:HTMLFormElement,gap:Gap)=>void}){
 const [series,setSeries]=useState(gap.options[0]?.seriesId??'');
 const selected=gap.options.find(row=>row.seriesId===series);
 return <form onSubmit={event=>{event.preventDefault();submit(event.currentTarget,gap);}}><fieldset disabled={busy}>
  <legend>Missing {gap.role!=='PRICE'?'FX rate':'price / rate'} · {gap.valueDate}</legend>
  <label>Quotation and source<select name="seriesId" value={series} onChange={event=>setSeries(event.target.value)} required>{gap.options.map(option=><option key={option.seriesId} value={option.seriesId}>{option.label}</option>)}</select></label>
  <label>Exact mark{selected?.currency?` · ${selected.currency}`:''}<input name="value" required inputMode="decimal" pattern="-?[0-9]+(\.[0-9]{1,12})?"/></label>
  {selected?.dirtyBond?<><label>Quoted accrued interest per 100<input name="quotedAccrualPer100" required inputMode="decimal" pattern="-?[0-9]+(\.[0-9]{1,12})?"/></label><label>Quote settlement date<input name="quoteSettlementDate" type="date" required min={gap.valueDate}/></label></>:null}
  <label>Reason<textarea name="reason" required maxLength={2000}/></label><label>Source / supporting reference<input name="sourceReference" required maxLength={1000}/></label>
  <label className="pnl-mark-confirm"><input name="confirmQuoteBasis" type="checkbox" required/><span>I checked the currency, units and quote convention against the booked position.</span></label>
 </fieldset><button disabled={busy}>Request independent mark review</button><TechnicalReference id={batch.batch_id} label="Candidate ID"/></form>;
}

/** Input review only: decisions never silently recalculate or publish financials. */
export function MarkOverrideReview({batch,active=true}:{batch:Batch;active?:boolean}){
 const [data,setData]=useState<Review|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');
 const [frozen,setFrozen]=useState<Ticket|null>(null);const live=useRef(false),retained=useRef<Ticket|null>(null);
 useRetainedNavigation(retained);
 useEffect(()=>{live.current=true;return()=>{live.current=false;};},[]);
 useEffect(()=>{if(!active)return;const controller=new AbortController();
  api<Review>(`batches/${batch.batch_id}/mark-overrides`,{signal:controller.signal}).then(value=>{if(!controller.signal.aborted)setData(value);}).catch(e=>{if(!controller.signal.aborted)setError((e as Error).message);});
  return()=>controller.abort();
 },[active,batch.batch_id]);
 async function refresh(){const value=await api<Review>(`batches/${batch.batch_id}/mark-overrides`);if(live.current)setData(value);}
 async function send(ticket:Ticket){
  retained.current=ticket;setFrozen(ticket);setBusy(true);setError('');setNotice('');
  try{await api(ticket.path,{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':ticket.key},body:JSON.stringify(ticket.body)});
   if(!live.current)return;retained.current=null;setFrozen(null);setNotice('Decision/request retained. Approved marks apply only after a new calculation; use Prepare corrected-input recalculation below.');await refresh();
  }catch(e){if(live.current)setError((e as Error).message);}finally{if(live.current)setBusy(false);}
 }
 function request(form:HTMLFormElement,gap:Gap){
  const fields=new FormData(form);const body:Create={baseBatchId:batch.batch_id,inputKey:gap.inputKey,seriesId:String(fields.get('seriesId')),value:String(fields.get('value')),reason:String(fields.get('reason')),sourceReference:String(fields.get('sourceReference')),confirmQuoteBasis:true};
  if(fields.has('quotedAccrualPer100')){body.quotedAccrualPer100=String(fields.get('quotedAccrualPer100'));body.quoteSettlementDate=String(fields.get('quoteSettlementDate'));}
  void send({path:'mark-overrides',key:crypto.randomUUID(),body});
 }
 function decision(event:FormEvent<HTMLFormElement>,requestId:string){
  event.preventDefault();const fields=new FormData(event.currentTarget);const action=(event.nativeEvent as SubmitEvent).submitter?.getAttribute('value');
  if(action!=='approve'&&action!=='reject'&&action!=='withdraw')return;
  void send({path:`mark-overrides/${requestId}/${action}`,key:crypto.randomUUID(),body:{comment:String(fields.get('comment'))}});
 }
 const label=(id:string)=>batch.presentation?.references[id]??'Instrument name unavailable';
 return <section className="pnl-surface pnl-mark-review" aria-label="Missing marks and independent review"><h3>Missing marks &amp; independent review</h3>
  <p className="pnl-muted">Correct the source data where possible. A reviewed manual mark fills only the exact missing date and quotation; it never edits a provider observation. Missing required marks block publication.</p>
  {error?<p role="alert">{error}</p>:null}{notice?<p role="status">{notice}</p>:null}
  {frozen?<div className="pnl-notice"><p>The submitted request is retained unchanged. Check review history before starting another request.</p><button disabled={busy} onClick={()=>void send(frozen)}>Retry unchanged mark request</button><button disabled={busy} onClick={()=>{void refresh().then(()=>{retained.current=null;setFrozen(null);}).catch(e=>setError((e as Error).message));}}>Check history and start another request</button></div>:null}
  {!data?<p role="status">{error?'Review data could not be loaded.':'Open Review to load mark requests.'}</p>:<>
   <button disabled={busy} onClick={()=>void refresh().catch(e=>setError((e as Error).message))}>Refresh mark review</button>
   {data.gaps.map(gap=><details key={gap.inputKey}><summary>{label(gap.subjectId)} · {gap.valueDate} · {gap.role!=='PRICE'?'FX rate':'Price / rate'}</summary>
    {gap.notice?<p>{gap.notice}</p>:null}
    {data.canRequest&&gap.options.length>0&&batch.status==='STAGED'?<RequestForm gap={gap} batch={batch} busy={busy||Boolean(frozen)} submit={request}/>:<p>{gap.options.length?'Requesting a mark requires calculation permission and a staged candidate.':'No compatible, currently entitled quotation is available. Correct policy/source coverage and recalculate.'}</p>}
   </details>)}
   {!data.gaps.length?<p>No missing required marks on this candidate.</p>:null}
   <h4>Mark request history</h4>{data.requests.length?<ul className="pnl-request-list">{data.requests.map(row=><li key={row.requestId}><strong>{label(row.subjectId)} · {row.valueDate}</strong><p>{row.value} {row.currency} · {row.status.toLowerCase()}</p><p>{row.reason}</p><details><summary>Source and review evidence</summary><p>{row.sourceReference}</p>{row.reviewComment?<p>{row.reviewComment}</p>:null}<TechnicalReference id={row.requestedBy} label="Requesting user ID"/><TechnicalReference id={row.reviewedBy} label="Reviewing user ID"/><TechnicalReference id={row.requestId} label="Mark request ID"/></details>
    {row.canReview||row.canWithdraw?<form onSubmit={event=>decision(event,row.requestId)}><fieldset disabled={busy||Boolean(frozen)}><label>Review explanation<textarea name="comment" required maxLength={2000}/></label>{row.canReview?<><button value="approve">Approve mark</button><button value="reject">Reject mark</button></>:null}{row.canWithdraw?<button value="withdraw">Withdraw approved mark</button>:null}</fieldset></form>:row.status==='PENDING'?<p>An independent user and real operator with review permission must decide this request.</p>:null}
   </li>)}</ul>:<p>No manual mark requests recorded.</p>}
  </>}
 </section>;
}
