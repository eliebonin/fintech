"use client";
import {useEffect,useState} from 'react';
import {formatTradeExactDecimal} from '@/lib/trades';
import {worklistRead,milestoneLabels,type OptionView,type WorklistEvent} from './client';
import styles from './contract-inspection.module.css';
const number=(value:string|null|undefined)=>value==null?'Not recorded':formatTradeExactDecimal(value);
const exerciseLabels:Record<string,string>={AMERICAN:'American',EUROPEAN:'European',BERMUDAN:'Bermudan'};
export function OptionInspection({event,tenantId}:{event:WorklistEvent;tenantId:string}){
 const [view,setView]=useState<OptionView>(),[error,setError]=useState(''),[reload,setReload]=useState(0);
 useEffect(()=>{const controller=new AbortController();setView(undefined);setError('');
  const query=new URLSearchParams({strategyId:event.strategyId,instrumentId:event.instrumentId,milestoneKind:event.milestoneKind??''});
  worklistRead<OptionView>(tenantId,`worklist/option?${query}`,controller.signal).then(value=>{
   if(controller.signal.aborted)return;
   if(value.eventKey!==event.eventKey||value.strategyId!==event.strategyId||value.instrumentId!==event.instrumentId||value.milestoneKind!==event.milestoneKind||value.sourceFingerprint!==event.sourceFingerprint)throw new Error('Option source changed. Refresh Lifecycle before inspecting this event.');
   setView(value);
  }).catch(caught=>{if(!controller.signal.aborted)setError(caught instanceof Error?caught.message:'Option inspection unavailable.');});return()=>controller.abort();
 },[tenantId,event.eventKey,event.strategyId,event.instrumentId,event.milestoneKind,event.sourceFingerprint,reload]);
 if(error)return <section role="alert" className={styles.card}><p>{error}</p><button type="button" onClick={()=>setReload(n=>n+1)}>Retry option inspection</button></section>;
 if(!view)return <p role="status">Loading option terms and current position…</p>;
 return <div className={styles.content}><div><button type="button" onClick={()=>setReload(n=>n+1)}>Refresh inspection</button></div>
 <p className={styles.note}>Expiry review only. A scheduled date does not confirm exercise, assignment or lapse. Closing bookings, cash payments and underlying delivery remain separate.</p>
 <section className={styles.card} aria-label="Option contract"><h3>Option contract</h3><dl className={styles.grid}>
 <div><dt>Underlying</dt><dd>{view.underlyingName??'Not available'}</dd></div><div><dt>Option type</dt><dd>{view.optionType==='CALL'?'Call':view.optionType==='PUT'?'Put':'Not recorded'}</dd></div>
 <div><dt>Strike</dt><dd>{number(view.strike)} {view.strikeCurrency??''}</dd></div><div><dt>Exercise style</dt><dd>{exerciseLabels[view.exerciseStyle??'']??view.exerciseStyle??'Not recorded'}</dd></div>
 <div><dt>Settlement method</dt><dd>{view.settlementMethod==='PHYSICAL'?'Physical delivery':view.settlementMethod==='CASH'?'Cash settlement':view.settlementMethod??'Not recorded'}</dd></div><div><dt>Cash settlement currency</dt><dd>{view.settlementCurrency??(view.settlementMethod==='PHYSICAL'?'Physical delivery terms apply':'Not recorded')}</dd></div>
 <div><dt>Premium multiplier</dt><dd>{number(view.premiumMultiplier)} · {view.premiumCurrency??'currency not recorded'}</dd></div><div><dt>Reference deliverable units per contract</dt><dd>{number(view.deliverableUnits)}</dd></div></dl>
 <p className={styles.note}>Premium conversion and deliverable units describe different contract facts. They are not an exercise instruction, cash amount or delta exposure.</p>
 {view.exerciseStyle==='AMERICAN'?<p className={styles.note}>American-style exercise or assignment may occur before expiry. Review broker notices and instructions separately.</p>:null}</section>
 <section className={styles.card} aria-label="Option position"><h3>Current signed contracts</h3>{view.positionAssessed?view.quantities.map((q,i)=><p key={i}><strong>{number(q.netQuantity)}</strong> contracts · {q.currency} premium currency <span className={styles.note}>· gross {number(q.grossQuantity)} across {q.entries} allocation {q.entries===1?'bucket':'buckets'}</span></p>):<p>Not assessed. Missing position evidence is not zero.</p>}<p className={styles.note}>Negative quantities are short positions. Net zero can retain opposing allocations. Assessed at {view.evaluatedAt}.</p></section>
 <section className={styles.card} aria-label="Option deadlines"><h3>Sourced dates and deadlines</h3><dl className={styles.grid}>{view.milestones.map(row=><div key={row.kind}><dt>{milestoneLabels[row.kind]??row.kind}</dt><dd>{row.atUtc??row.date??'Not recorded'}{row.atUtc?<small>UTC · exact last-trading cutoff</small>:null}</dd></div>)}
 <div><dt>Broker exercise-instruction cutoff</dt><dd>Not recorded</dd></div><div><dt>AM/PM settlement fixing</dt><dd>Not recorded</dd></div></dl><p className={styles.note}>Expiry, last trading, fixing and payment are distinct. No cutoff, fixing convention or settlement lag has been inferred.</p></section>
 {view.reasons.length?<details className={styles.card}><summary>Review notes and coverage</summary><ul>{view.reasons.map((reason,i)=><li key={i}>{reason}</li>)}</ul></details>:null}
 <details className={styles.card}><summary>Approved source evidence and identities</summary><p>Option terms: v{view.termsVersion??'unavailable'} · {view.optionTermsId??'not recorded'}</p><p>Definition: {view.definitionId??'Not recorded'}</p><p>Approved: {view.sourceApprovedAt??'Not recorded'}</p><p>Source fingerprint: {view.sourceFingerprint}</p><p>Event: {view.eventKey}</p><p>Strategy: {view.strategyId}</p><p>Instrument: {view.instrumentId}</p>{view.underlyingId?<p>Underlying: {view.underlyingId}</p>:null}</details></div>;
}
