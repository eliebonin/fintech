'use client';
import type {components} from 'api-contracts';
import {useEffect,useRef,useState,type FormEvent} from 'react';
import {useRouter} from 'next/navigation';
import {createIdempotencyKey,recordFxDeliveryFromBff} from '@/lib/browser-api-client';
import {BffApiError} from '@/lib/api-errors';
import {freezeBookingSubmission,type FrozenBookingSubmission} from '@/lib/booking-submission';
export type FxDeliveryProgress=components['schemas']['DeliveryView'];
type DeliveryRequest=components['schemas']['DeliveryRequest'];

export function FxDeliveryControls({progress,tenantId,canWrite}:{progress:FxDeliveryProgress;tenantId:string;canWrite:boolean}) {
 const router=useRouter();
 const [action,setAction]=useState<'CONFIRM'|'REVERSE'>('CONFIRM'),[leg,setLeg]=useState<'RECEIVE'|'PAY'>('RECEIVE'),[amount,setAmount]=useState('');
 const [target,setTarget]=useState(String(progress.reversibleSequences[0]??'')),[effectiveAt,setEffectiveAt]=useState(''),[evidence,setEvidence]=useState('');
 const [reviewing,setReviewing]=useState(false),[busy,setBusy]=useState(false),[retry,setRetry]=useState(false),[blocked,setBlocked]=useState(false),[finished,setFinished]=useState(false),[error,setError]=useState('');
 const inFlight=useRef(false),envelope=useRef<FrozenBookingSubmission<DeliveryRequest>|null>(null);
 useEffect(()=>{
  const url=window.location.href,state=window.history.state;
  const unresolved=()=>inFlight.current||retry||blocked;
  const warn=(event:BeforeUnloadEvent)=>{if(unresolved()){event.preventDefault();event.returnValue='';}};
  const click=(event:MouseEvent)=>{const link=(event.target as Element)?.closest?.('a[href]') as HTMLAnchorElement|null;if(unresolved()&&link&&link.target!=='_blank'){event.preventDefault();event.stopPropagation();window.alert('Resolve the delivery evidence result before leaving. Retry uncertain results unchanged.');}};
  const back=(event:PopStateEvent)=>{if(unresolved()){event.stopImmediatePropagation();window.history.pushState(state,'',url);window.alert('Resolve the delivery evidence result before leaving.');}};
  window.addEventListener('beforeunload',warn);window.addEventListener('popstate',back,true);document.addEventListener('click',click,true);
  return()=>{window.removeEventListener('beforeunload',warn);window.removeEventListener('popstate',back,true);document.removeEventListener('click',click,true);};
 },[retry,blocked]);
 function review(event:FormEvent){
  event.preventDefault();setError('');
  if(!evidence.trim()||!effectiveAt||action==='CONFIRM'&&!/^\d+(\.\d{1,24})?$/.test(amount)||action==='REVERSE'&&!progress.reversibleSequences.includes(Number(target))){setError('Enter the amount or confirmation target, actual UTC time and source evidence.');return;}
  let at:string;try{at=new Date(`${effectiveAt}Z`).toISOString();}catch{setError('Enter a valid actual UTC time.');return;}
  const common={action,expectedSequenceNo:progress.expectedSequenceNo,effectiveAt:at,evidence:evidence.trim()};
  const payload:DeliveryRequest=action==='CONFIRM'?{...common,leg,amount}:{...common,targetSequenceNo:Number(target)};
  envelope.current=freezeBookingSubmission(payload,createIdempotencyKey(),tenantId);setReviewing(true);
 }
 async function confirm(){
  if(inFlight.current||blocked||finished||!envelope.current)return;
  inFlight.current=true;setBusy(true);setError('');
  try{const frozen=envelope.current;await recordFxDeliveryFromBff(progress.tradeId,frozen.payload,frozen.key,frozen.expectedTenantId);setFinished(true);setRetry(false);router.refresh();}
  catch(caught){setError(caught instanceof Error?caught.message:'Delivery evidence could not be saved.');const uncertain=!(caught instanceof BffApiError)||caught.status>=500||[408,429].includes(caught.status);setRetry(uncertain);if(caught instanceof BffApiError&&[401,403,409].includes(caught.status))setBlocked(true);else if(!uncertain){envelope.current=null;setReviewing(false);}}
  finally{inFlight.current=false;setBusy(false);}
 }
 const currency=leg==='RECEIVE'?progress.receiveCurrency:progress.payCurrency;
 const frozen=envelope.current?.payload;
 return <section className="detail-card"><h2>FX delivery evidence · {progress.status}</h2><p>Contractual settlement date: {progress.settlementDate}. Current recorded evidence, not a cash balance or valuation. Maturity does not prove delivery.</p><div className="detail-fields"><div><small>Receive confirmed / outstanding</small><strong>{`${progress.receiveConfirmed} ${progress.receiveCurrency} / ${progress.receiveOutstanding} ${progress.receiveCurrency}`}</strong></div><div><small>Pay confirmed / outstanding</small><strong>{`${progress.payConfirmed} ${progress.payCurrency} / ${progress.payOutstanding} ${progress.payCurrency}`}</strong></div></div><p>Confirm only final delivery supported by your source. Both legs must be fulfilled for DELIVERED. No cash trade, settlement instruction or balance posting is generated.</p>{error?<p role="alert">{error}</p>:null}{finished?<p role="status">Delivery evidence saved. Original execution retained.</p>:!canWrite?<p>Read-only delivery evidence.</p>:reviewing?<><h3>Review delivery evidence</h3><p>{frozen?.action==='REVERSE'?`Reverse confirmation #${frozen.targetSequenceNo}`:`Confirm ${frozen?.leg} ${frozen?.amount} ${frozen?.leg==='RECEIVE'?progress.receiveCurrency:progress.payCurrency}`}</p><p>Effective UTC: {frozen?.effectiveAt}</p><p>Evidence / reason: {frozen?.evidence}</p><p>Expected history sequence: {frozen?.expectedSequenceNo}. Reversal retains the original confirmation and reopens its obligation.</p><div className="ticket-actions"><button disabled={busy||blocked} onClick={confirm}>{busy?'Saving…':retry?'Retry unchanged evidence':'Confirm delivery evidence'}</button><button disabled={busy||retry||blocked} onClick={()=>{envelope.current=null;setReviewing(false);}}>Back to edit</button></div>{retry?<p role="status">Result uncertain. Retry unchanged with the original key; do not create another confirmation.</p>:null}{blocked?<p role="alert">Recording blocked. Reload this trade and inspect history before another action.</p>:null}</>:<form className="strategy-form" onSubmit={review}><label>Action<select name="action" value={action} onChange={event=>setAction(event.target.value as typeof action)}><option value="CONFIRM">Confirm actual currency delivery</option>{progress.reversibleSequences.length?<option value="REVERSE">Reverse erroneous delivery evidence</option>:null}</select></label>{action==='CONFIRM'?<><label>Currency leg<select name="leg" value={leg} onChange={event=>setLeg(event.target.value as typeof leg)}><option value="RECEIVE">Receive {progress.receiveCurrency}</option><option value="PAY">Pay {progress.payCurrency}</option></select></label><label>Delivered amount ({currency})<input name="amount" inputMode="decimal" required value={amount} onChange={event=>setAmount(event.target.value)}/></label></>:<label>Confirmation to reverse<select name="target" value={target} onChange={event=>setTarget(event.target.value)}>{progress.reversibleSequences.map(sequence=><option key={sequence} value={sequence}>Confirmation #{sequence}</option>)}</select></label>}<label>Actual effective time (UTC)<input name="effectiveAt" type="datetime-local" required value={effectiveAt} onChange={event=>setEffectiveAt(event.target.value)}/></label><label>Source evidence / reversal reason<textarea name="evidence" required maxLength={1000} value={evidence} onChange={event=>setEvidence(event.target.value)}/></label><button>Review delivery evidence</button></form>}</section>;
}

export function DeliveryEventFacts({raw}:{raw:string|null}) {
 try{const value=JSON.parse(raw??'null');if(value?.schemaVersion!==1||value?.kind!=='FX_DELIVERY'||typeof value.request?.evidence!=='string')return null;const request=value.request;return <p>{request.action==='REVERSE'?`Reverse confirmation #${request.targetSequenceNo}`:`Confirm ${request.leg} ${request.amount} (currency inherited from booked obligations)`} · {request.evidence}</p>;}catch{return null;}
}
