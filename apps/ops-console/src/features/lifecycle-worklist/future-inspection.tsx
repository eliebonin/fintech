"use client";
import {useEffect,useState} from 'react';
import {formatTradeExactDecimal} from '@/lib/trades';
import {worklistRead,milestoneLabels,type FutureView,type WorklistEvent} from './client';
import styles from './contract-inspection.module.css';
export function FutureInspection({event,tenantId}:{event:WorklistEvent;tenantId:string}){
 const [view,setView]=useState<FutureView>(),[error,setError]=useState(''),[reload,setReload]=useState(0);
 useEffect(()=>{const controller=new AbortController();setView(undefined);setError('');
  const query=new URLSearchParams({strategyId:event.strategyId,instrumentId:event.instrumentId,milestoneKind:event.milestoneKind??''});
  worklistRead<FutureView>(tenantId,`worklist/future?${query}`,controller.signal).then(value=>{
   if(controller.signal.aborted)return;
   if(value.eventKey!==event.eventKey||value.strategyId!==event.strategyId||value.instrumentId!==event.instrumentId||value.milestoneKind!==event.milestoneKind||value.sourceFingerprint!==event.sourceFingerprint)throw new Error('Futures source changed. Refresh Lifecycle before inspecting this event.');
   setView(value);
  }).catch(caught=>{if(!controller.signal.aborted)setError(caught instanceof Error?caught.message:'Futures inspection unavailable.');});return()=>controller.abort();
 },[tenantId,event.eventKey,event.strategyId,event.instrumentId,event.milestoneKind,event.sourceFingerprint,reload]);
 if(error)return <section role="alert" className={styles.card}><p>{error}</p><button type="button" onClick={()=>setReload(n=>n+1)}>Retry futures inspection</button></section>;
 if(!view)return <p role="status">Loading futures contract and current position…</p>;
 return <div className={styles.content}><div><button type="button" onClick={()=>setReload(n=>n+1)}>Refresh inspection</button></div>
 <p className={styles.note}>Notifications only. A passed date does not close contracts or confirm settlement. Rolls, variation margin, cash movements and delivery remain separate.</p>
 <section className={styles.card} aria-label="Futures contract"><h3>Contract and current position</h3><dl className={styles.grid}>
 <div><dt>Family</dt><dd>{view.familyName??'Not recorded'}</dd></div><div><dt>Contract month</dt><dd>{view.contractMonth??'Not recorded'}</dd></div>
 <div><dt>Settlement method</dt><dd>{view.settlementMethod==='PHYSICAL'?'Physical delivery':view.settlementMethod==='CASH'?'Cash settlement':'Not assessed'}</dd></div><div><dt>Approved convention</dt><dd>{view.conventionVersion?`v${view.conventionVersion}`:'Not recorded'}</dd></div>
 <div><dt>Price multiplier per contract</dt><dd>{view.monetaryMultiplier==null?'Not assessed':formatTradeExactDecimal(view.monetaryMultiplier)}</dd></div><div><dt>Quote divisor</dt><dd>{view.quoteFactor??'Not assessed'}</dd></div></dl>
 <h4>Current signed contracts</h4>{view.positionAssessed?view.quantities.map((q,i)=><p key={i}><strong>{formatTradeExactDecimal(q.netQuantity)}</strong> contracts · {q.currency} quote currency <span className={styles.note}>· gross {formatTradeExactDecimal(q.grossQuantity)} across {q.entries} allocation {q.entries===1?'bucket':'buckets'}</span></p>):<p>Not assessed. Missing position evidence is not zero.</p>}
 <p className={styles.note}>Negative quantities are short positions. Net zero can retain separate opposing allocations. Assessed at {view.evaluatedAt}.</p></section>
 <section className={styles.card} aria-label="Futures milestones"><h3>Sourced contract dates</h3><dl className={styles.grid}>{view.milestones.map(row=><div key={row.kind}><dt>{milestoneLabels[row.kind]??row.kind}</dt><dd>{row.atUtc??row.date}{row.atUtc?<small>UTC · exact trading cutoff</small>:null}</dd></div>)}
 <div><dt>First-notice date</dt><dd>{view.firstNoticeDate??'Not recorded'}<small>Confirm exchange and broker notice deadlines separately.</small></dd></div></dl><p className={styles.note}>Expiry, last trading, notice and delivery are distinct. Dates are sourced rather than calculated from the contract month. No payment or delivery status is inferred.</p></section>
 {view.reasons.length?<details className={styles.card}><summary>Review notes and coverage</summary><ul>{view.reasons.map((reason,i)=><li key={i}>{reason}</li>)}</ul></details>:null}
 <details className={styles.card}><summary>Source evidence and identities</summary><p>Source: {view.sourceReference??'Not recorded'}</p><p>Approved: {view.sourceApprovedAt??'Not recorded'}</p><p>Convention: {view.conventionId??'Not recorded'}</p><p>Fingerprint: {view.sourceFingerprint}</p><p>Event: {view.eventKey}</p><p>Strategy: {view.strategyId}</p><p>Instrument: {view.instrumentId}</p></details></div>;
}
