'use client';
import {useEffect,useRef,useState,type FormEvent} from 'react';
import {mappingFields,fieldLabels,exactQuantity,type Candidate} from './presentation';
import {reportingRequest} from './transport';
export function CandidateInspector({row,canReview,onSaved,onClose}:{row:Candidate;canReview:boolean;onSaved:()=>void;onClose:()=>void}){
 const [saving,setSaving]=useState(false);const [error,setError]=useState('');
 const panel=useRef<HTMLElement>(null);
 useEffect(()=>{panel.current?.focus({preventScroll:true});panel.current?.scrollIntoView({block:'start'});},[row.candidateId,row.revision]);
 async function submit(event:FormEvent<HTMLFormElement>){
  event.preventDefault();const form=event.currentTarget;const values=Object.fromEntries(new FormData(form));
  const mapping=Object.fromEntries(mappingFields.map(key=>[key,values[key]||null]));
  setSaving(true);setError('');try{await reportingRequest(`candidates/${row.candidateId}/review`,{expectedRevision:row.revision,action:values.action,reason:values.reason,mapping});onSaved();}
  catch(error){setError((error as Error).message);}finally{setSaving(false);}
 }
 return <section ref={panel} tabIndex={-1} className="reg-card" aria-label="Report inspection"><div className="reg-heading"><h2>{row.facts.instrumentName}</h2><button type="button" aria-label="Close report inspection" onClick={onClose}>×</button></div>
  <p>{row.facts.instrumentType} · {row.facts.executionTime} · revision {row.revision}</p>
  <dl className="reg-facts"><div><dt>Quantity</dt><dd>{exactQuantity(row.facts.quantity)} {row.facts.quantityUnit}</dd></div><div><dt>Execution price</dt><dd>{exactQuantity(row.facts.executionPrice)} {row.facts.priceCurrency} · {row.facts.priceBasis}</dd></div></dl>
  {row.missingFields.length?<p className="reg-notice">Needs review: {row.missingFields.map(x=>fieldLabels[x]??x.replaceAll('_',' ')).join(', ')}.</p>:null}
  <p>Last decision: {row.reason}</p>{error?<p role="alert" className="error-panel">{error}</p>:null}
  <form onSubmit={submit}><fieldset disabled={!canReview||saving} className="reg-form-grid"><legend>Reporting mapping and assessment</legend>
  {mappingFields.map(key=><label key={key}>{fieldLabels[key]}{key==='capacity'?<select name={key} defaultValue={row.mapping[key]??''}><option value="">Not supplied</option>{['DEAL','MTCH','AOTC'].map(x=><option key={x}>{x}</option>)}</select>:<input name={key} maxLength={key==='instrumentDescription'?250:100} defaultValue={row.mapping[key]??''}/>}</label>)}
  <label>Action<select name="action" defaultValue="UPDATE_MAPPING"><option value="UPDATE_MAPPING">Update mapping / confirm reassessment</option><option value="REPORTABLE">Assess as reportable</option><option value="NOT_REPORTABLE">Assess as not reportable</option><option value="HOLD">Hold from export</option><option value="AUTOMATIC">Return to automatic assessment</option></select></label>
  <label>Reason<textarea name="reason" minLength={3} maxLength={2000} required/></label></fieldset>
  <p className="muted">Supply an ISIN where applicable. An OTC description can support preparation when no ISIN exists; final regulatory identity and field applicability still need validation. These IDs describe regulatory roles, not the person who clicked Book.</p>
  {canReview?<button type="submit" disabled={saving}>{saving?'Saving review…':'Save reviewed revision'}</button>:<p>Read-only: reporting review permission is required to amend this report.</p>}</form>
  <details><summary>Evidence and decision history</summary><p>Trade reference: {row.tradeId}</p><pre className="reg-proof">{JSON.stringify({bookingTerms:row.facts.bookingTerms,history:row.history},null,2)}</pre></details>
 </section>;
}
