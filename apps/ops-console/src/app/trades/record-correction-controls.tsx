'use client';
import {useEffect,useRef,useState,type FormEvent} from 'react';
import {useRouter} from 'next/navigation';
import {cancelBookingRecordFromBff,createIdempotencyKey} from '@/lib/browser-api-client';
import {BffApiError} from '@/lib/api-errors';
import {freezeBookingSubmission,type FrozenBookingSubmission} from '@/lib/booking-submission';
import {bookingCorrectionEligibility,type BookingCorrection} from '@/lib/trade-correction-model';
import {formatTradeDateTime,formatTradeExactDecimal,type TradeDetailPayload} from '@/lib/trades';
import type {TradeBookingContext} from '@/lib/browser-api-client';
import {TradeTicket,type TicketStrategy} from './new/trade-ticket';
import {FxForwardTicket} from './new/fx-forward-ticket';
import {OptionTicket} from './new/option-ticket';
import {ProductTicket} from './new/product-ticket';

function OriginalSummary({original}:{original:TradeDetailPayload['data']}) {
 const trade=original.trade;
 return <div><h3>Original booking</h3><p>{trade.subjectName} · {trade.strategyName} · {formatTradeExactDecimal(trade.quantity)} {trade.quantityUnit} at {formatTradeExactDecimal(trade.executionPrice)}</p><p>{formatTradeDateTime(trade.tradeDatetimeUtc)} · {trade.tradeId}</p><a href={`/trades/${encodeURIComponent(trade.tradeId)}`} target="_blank" rel="noreferrer">Inspect original facts and annotations</a></div>;
}

export function CorrectionBookingGate({original,strategies,context}:{original:TradeDetailPayload['data'];strategies:TicketStrategy[];context:TradeBookingContext}) {
 const eligibility=bookingCorrectionEligibility(original);
 const [reason,setReason]=useState(''),[confirmed,setConfirmed]=useState<BookingCorrection>(),[error,setError]=useState('');
 const [clientReady,setClientReady]=useState(false);
 // Before hydration a native GET submit would discard the correction query.
 useEffect(()=>{setClientReady(true);},[]);
 if(!eligibility.eligible)return <section className="error-panel" role="alert">This booking cannot be replaced through the alpha correction workflow. Reload its detail.</section>;
 function start(event:FormEvent){event.preventDefault();const trimmed=reason.trim();if(!trimmed){setError('Enter a reason for replacing this booking.');return;}setConfirmed({tradeId:original.trade.tradeId,expectedSequenceNo:eligibility.sequenceNo,reason:trimmed});}
 // Construct interactive tickets in the client module graph. Server-supplied
 // children are rendered slots, not element factories safe to clone with props.
 const product=eligibility.product;
 const ticket=!confirmed?null:product==='CASH'?<TradeTicket strategies={strategies} context={context} correction={confirmed}/>:product==='FX_FORWARD'?<FxForwardTicket strategies={strategies} context={context} correction={confirmed}/>:product==='OPTION'?<OptionTicket strategies={strategies} context={context} correction={confirmed}/>:product?<ProductTicket kind={product} strategies={strategies} context={context} correction={confirmed}/>:null;
 return <><section className="detail-card"><h2>Replace erroneous booking</h2><OriginalSummary original={original}/><p>This corrects the recorded execution; it does not terminate, settle or reverse the contract. The original remains active unless the complete replacement succeeds.</p><p>Re-enter all desired execution details, parties, properties, tags and references. Optional annotations are not copied implicitly. The strategy and product category stay the same.</p>{confirmed?<p role="status">Confirmed correction reason: {confirmed.reason}</p>:<form className="strategy-form" onSubmit={start}><label>Correction reason<textarea required disabled={!clientReady} maxLength={1000} value={reason} onChange={event=>{setReason(event.target.value);setError('');}}/></label>{error?<p role="alert">{error}</p>:null}<button disabled={!clientReady}>Continue to replacement ticket</button><a href={`/trades/${original.trade.tradeId}`}>Leave original unchanged</a></form>}</section>{ticket}</>;
}

export function RecordCorrectionActions({detail,tenantId}:{detail:TradeDetailPayload['data'];tenantId:string}) {
 const eligibility=bookingCorrectionEligibility(detail),router=useRouter();
 const [open,setOpen]=useState(false),[reason,setReason]=useState(''),[reviewing,setReviewing]=useState(false),[busy,setBusy]=useState(false),[retry,setRetry]=useState(false),[blocked,setBlocked]=useState(false),[error,setError]=useState(''),[finished,setFinished]=useState(false);
 const inFlight=useRef(false),envelope=useRef<FrozenBookingSubmission<{expectedSequenceNo:number;reason:string}>|null>(null);
 useEffect(()=>{
   const detailUrl=window.location.href,detailState=window.history.state;
   const unresolved=()=>inFlight.current||retry||blocked;
   const warn=(event:BeforeUnloadEvent)=>{if(unresolved()){event.preventDefault();event.returnValue='';}};
   const click=(event:MouseEvent)=>{const link=(event.target as Element)?.closest?.('a[href]') as HTMLAnchorElement|null;if(unresolved()&&link&&link.target!=='_blank'){event.preventDefault();event.stopPropagation();window.alert('Resolve the record-cancellation result before leaving. Retry an uncertain result unchanged.');}};
   const back=(event:PopStateEvent)=>{if(unresolved()){event.stopImmediatePropagation();window.history.pushState(detailState,'',detailUrl);window.alert('Resolve the record-cancellation result before leaving. Retry an uncertain result unchanged.');}};
   window.addEventListener('beforeunload',warn);window.addEventListener('popstate',back,true);document.addEventListener('click',click,true);
   return()=>{window.removeEventListener('beforeunload',warn);window.removeEventListener('popstate',back,true);document.removeEventListener('click',click,true);};
 },[retry,blocked]);
 if(!eligibility.eligible)return null;
 function review(event:FormEvent){event.preventDefault();const trimmed=reason.trim();if(!trimmed){setError('Enter why this booking record is erroneous.');return;}envelope.current=freezeBookingSubmission({expectedSequenceNo:eligibility.sequenceNo,reason:trimmed},createIdempotencyKey(),tenantId);setError('');setReviewing(true);}
 async function confirm(){
   if(inFlight.current||blocked||finished||!envelope.current)return;
   inFlight.current=true;setBusy(true);setError('');
   try{const frozen=envelope.current;await cancelBookingRecordFromBff(detail.trade.tradeId,frozen.payload,frozen.key,frozen.expectedTenantId);setFinished(true);setRetry(false);router.refresh();}
   catch(caught){setError(caught instanceof Error?caught.message:'Record cancellation failed.');const uncertain=!(caught instanceof BffApiError)||caught.status>=500||[408,429].includes(caught.status);setRetry(uncertain);if(caught instanceof BffApiError&&[401,403,409].includes(caught.status))setBlocked(true);else if(!uncertain){envelope.current=null;setReviewing(false);}}
   finally{inFlight.current=false;setBusy(false);}
 }
 const replacement=new URLSearchParams({corrects:detail.trade.tradeId,...(eligibility.product==='CASH'?{}:{product:eligibility.product!})});
 return <section className="detail-card"><h2>Record corrections</h2><p>For booking errors only. Cancellation does not terminate a contract, confirm delivery or generate an opposite trade/cash movement.</p>{error?<p role="alert" className="strategy-error">{error}</p>:null}{finished?<p role="status">Booking record cancelled. Original facts and evidence are retained.</p>:!open?<div className="ticket-actions"><a href={`/trades/new?${replacement}`}>Replace erroneous booking</a><button onClick={()=>setOpen(true)}>Cancel erroneous booking</button></div>:reviewing?<><OriginalSummary original={detail}/><p>Cancellation reason: {envelope.current?.payload.reason}</p><div className="ticket-actions"><button disabled={busy||blocked} onClick={confirm}>{busy?'Cancelling…':retry?'Retry unchanged cancellation':'Confirm record cancellation'}</button><button disabled={busy||retry||blocked} onClick={()=>{setReviewing(false);envelope.current=null;}}>Back to reason</button></div>{retry?<p role="status">Result uncertain. Retry unchanged with the original key; do not submit another cancellation.</p>:null}{blocked?<p role="alert">Cancellation blocked. Reload this trade detail and check history before another action.</p>:null}</>:<form className="strategy-form" onSubmit={review}><label>Cancellation reason<textarea required maxLength={1000} value={reason} onChange={event=>{setReason(event.target.value);setError('');}}/></label><button>Review record cancellation</button><button type="button" onClick={()=>setOpen(false)}>Leave unchanged</button></form>}</section>;
}
