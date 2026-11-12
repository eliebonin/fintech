"use client";
import {useEffect,useState} from 'react';
import {formatTradeExactDecimal} from '@/lib/trades';
import {worklistRead,milestoneLabels,type StructuredView,type WorklistEvent} from './client';
import styles from './contract-inspection.module.css';
import local from './structured-inspection.module.css';
const number=(value:string|null|undefined)=>value==null?'Not recorded':formatTradeExactDecimal(value);
const readable=(value:string)=>value.toLowerCase().replaceAll('_',' ');
const compare:Record<string,string>={GE:'≥',GT:'>',LE:'≤',LT:'<',BETWEEN:'Between',OUTSIDE:'Outside'};
const actionLabels:Record<string,string>={REDEEM_PARENT:'Parent redemption',TERMINATE_PARENT:'Parent termination',PAY_COMPONENT:'Component payment',PAY_CONSOLATION:'Consolation payment',CANCEL_FUTURE_COMPONENTS:'Cancel future components',ACTIVATE_CAPITAL_PROTECTION:'Activate capital protection'};
export function StructuredInspection({event,tenantId}:{event:WorklistEvent;tenantId:string}){
 const [view,setView]=useState<StructuredView>(),[error,setError]=useState(''),[reload,setReload]=useState(0);
 useEffect(()=>{const controller=new AbortController();setView(undefined);setError('');
  const query=new URLSearchParams({strategyId:event.strategyId,instrumentId:event.instrumentId,eventKey:event.eventKey});
  worklistRead<StructuredView>(tenantId,`worklist/structured?${query}`,controller.signal).then(value=>{
   if(controller.signal.aborted)return;
   if(value.eventKey!==event.eventKey||value.strategyId!==event.strategyId||value.instrumentId!==event.instrumentId||value.sourceFingerprint!==event.sourceFingerprint)throw new Error('Schedule source changed. Refresh Lifecycle before inspecting this notice.');
   setView(value);
  }).catch(caught=>{if(!controller.signal.aborted)setError(caught instanceof Error?caught.message:'Schedule information unavailable.');});return()=>controller.abort();
 },[tenantId,event.eventKey,event.strategyId,event.instrumentId,event.sourceFingerprint,reload]);
 if(error)return <section role="alert" className={styles.card}><p>{error}</p><button type="button" onClick={()=>setReload(n=>n+1)}>Retry schedule inspection</button></section>;
 if(!view)return <p role="status">Loading scheduled information and position context…</p>;
 const swap=view.instrumentType==='SWAP';
 return <div className={styles.content}><div><button type="button" onClick={()=>setReload(n=>n+1)}>Refresh inspection</button></div>
 <p className={styles.note}><strong>Information only · Outcome not assessed.</strong> A scheduled or passed date does not confirm a coupon, autocall, payment or termination.</p>
 <section className={styles.card} aria-label="Scheduled information"><h3>{milestoneLabels[view.noticeKind]??'Scheduled information'}</h3><dl className={styles.grid}>
 <div><dt>Observation / contract date</dt><dd>{view.eventDate??'Information unavailable'}</dd></div><div><dt>Related payment date · conditional</dt><dd>{view.conditionalPaymentDate??'Not recorded'}</dd></div>
 <div><dt>Observed structured contract</dt><dd>{view.observedInstrumentName??'Not available'}</dd></div><div><dt>Issuer</dt><dd>{view.issuer??'Not recorded'}</dd></div>
 <div><dt>Source currency</dt><dd>{view.currency??'Not recorded'}</dd></div><div><dt>First eligible autocall date</dt><dd>{view.firstAutocallDate??'Not recorded'}</dd></div></dl>
 <p className={styles.note}>{view.autocallEligibility==='BEFORE_FIRST_DATE'?'This observation precedes the first eligible autocall date.':view.autocallEligibility==='ELIGIBLE_DATE'?'This date is on or after the first eligible autocall date; conditions have not been checked.':view.autocallEligibility==='NOT_ASSESSED'?'Autocall eligibility is not assessed from the available source.':'This notice does not establish an autocall test.'} A related payment date is contractual information, not evidence of an amount being payable.</p></section>
 <section className={styles.card} aria-label="Held position context"><h3>{swap?'Held swap':'Held position'}</h3><p><strong>{view.instrumentName}</strong>{view.relation?` · ${view.relation}`:''}</p><p>Position context date: {view.positionDate}. Past dates use known holdings at that date; future dates use current holdings.</p>
 {view.positionAssessed?view.quantities.map((q,i)=><p key={i}><strong>{number(q.netQuantity)}</strong> {readable(q.unit)} · quote/price currency {q.currency} <span className={styles.note}>· gross {number(q.grossQuantity)} across {q.entries} allocation {q.entries===1?'bucket':'buckets'}</span></p>):<p>Position not assessed. Missing evidence is not zero.</p>}
 {swap?<p className={styles.note}>These quantities belong to the held swap, not the observed structured contract. No swap termination, underlying position or payment is inferred.</p>:null}</section>
 <section className={styles.card} aria-label="Source conditions"><h3>Conditions from current approved terms</h3><p className={styles.note}>Source thresholds are shown in their stored basis. No fixing, percentage conversion, barrier test or outcome is calculated.</p>
 {view.conditions.length?view.conditions.map((group,index)=><details className={local.condition} key={index} open={index===0}><summary>Condition {index+1} · {readable(group.combination)} · {readable(group.scope)}</summary><p>Source status: {readable(group.sourceStatus)} · aggregation: {readable(group.aggregation)}</p>
 {group.barriers.length?<div className={local.table}><table><thead><tr><th>Underlying</th><th>Comparison</th><th>Threshold · as stored</th><th>Source basis / measure</th></tr></thead><tbody>{group.barriers.map((barrier,i)=><tr key={i}><td>{barrier.underlyingName??'Not recorded'}</td><td>{compare[barrier.comparison]??readable(barrier.comparison)}</td><td>{number(barrier.lowerLevel)}{barrier.upperLevel!=null?` to ${number(barrier.upperLevel)}`:''}{barrier.lowerInclusive!=null?<small>Lower {barrier.lowerInclusive?'inclusive':'exclusive'}{barrier.upperLevel!=null?`; upper ${barrier.upperInclusive?'inclusive':'exclusive'}`:''}</small>:null}</td><td>{readable(barrier.basis)}{barrier.measure?<small>{readable(barrier.measure)}</small>:null}</td></tr>)}</tbody></table></div>:<p>No atomic barrier rows are attached to this condition.</p>}
 {group.actions.length?<><h4>Contractual actions if conditions are met</h4><ul>{group.actions.map((action,i)=>{const [code,target]=action.split(' · ');return <li key={i}>{actionLabels[code]??readable(code)}{target?` · target ${readable(target)}`:''}</li>;})}</ul></>:null}
 <details><summary>Condition source code</summary><p>{group.groupCode}</p></details></details>):<p>No condition group is attached to this date in the available source. This does not establish a financial outcome.</p>}</section>
 <details className={styles.card}><summary>Coverage and source notes</summary><ul>{view.reasons.map((reason,i)=><li key={i}>{reason}</li>)}</ul><p>Only sourced dates are shown; schedule completeness is not certified. Continuous barriers do not become invented daily observations.</p></details>
 <details className={styles.card}><summary>Source evidence and identities</summary><p>Basis: current approved terms · definition v{view.definitionVersion??'unavailable'} · structured terms v{view.termsVersion??'unavailable'}</p><p>Source schedule state: {view.sourceEventStatus??'Not recorded'}</p><p>Schedule event: {view.scheduleEventId??'Not recorded'}</p><p>Observed contract: {view.observedInstrumentId??'Not available'}</p><p>Fingerprint: {view.sourceFingerprint}</p><p>Event: {view.eventKey}</p><p>Strategy: {view.strategyId}</p><p>Held instrument: {view.instrumentId}</p></details></div>;
}
