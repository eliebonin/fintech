'use client';
import {useRef,useState,type FormEvent} from 'react';
import {displayAmount} from './presentation';

/** A prominent entry to the existing reviewed publication, never one-click approval. */
export function PublicationAction({status,stagedBy,actorId,canReview,busy,onPublish,requiresSelfReview=false,canSelfPublish=false,unavailableReason,sourceHealthStatus,context,pendingAmendments,requiredInputsComplete=true}:{status:string;stagedBy:string;actorId:string;canReview:boolean;busy:boolean;requiresSelfReview?:boolean;canSelfPublish?:boolean;unavailableReason?:string;sourceHealthStatus?:string;pendingAmendments?:number;requiredInputsComplete?:boolean;context?:{strategy:string;period:string;policy:string;currency:string;total:string;warnings:string[]};onPublish:(event:FormEvent<HTMLFormElement>,selfReview?:boolean)=>unknown}){
 const [open,setOpen]=useState(false);
 const trigger=useRef<HTMLButtonElement>(null);
 if(status!=='STAGED')return null;
 if(!canReview)return <p className="pnl-muted">Publication requires valuation review permission.</p>;
 const selfReview=requiresSelfReview||stagedBy===actorId;
 const outdated=Boolean(sourceHealthStatus&&sourceHealthStatus!=='CURRENT');
 const blocked=!requiredInputsComplete||outdated||Boolean(pendingAmendments)||(selfReview&&!canSelfPublish);
 return <section className="pnl-publication-action" aria-label="Valuation publication">
  <div className="pnl-publication-heading"><div><strong>Publish this valuation</strong><p className="pnl-muted">Staged only — not yet published. {selfReview&&canSelfPublish?'An authorised self-review exception is available.':'Publication requires independent review.'}</p></div>
   <button ref={trigger} type="button" className="pnl-publish-primary" disabled={busy||blocked} aria-expanded={open} onClick={()=>setOpen(true)}>{selfReview&&canSelfPublish?'Publish without independent review':'Publish valuation'}</button>
  </div>
  {!requiredInputsComplete?<p>Supply missing required price marks or reviewed manual marks, then recalculate before publication. An acknowledgement cannot publish an incomplete report.</p>:outdated?<p>Recalculate this result before publication: ledger source evidence changed or is unverified.</p>:pendingAmendments?<p>Resolve {pendingAmendments} pending amendment requests before publication.</p>:blocked?<p>An independent reviewer must review and publish this batch. {unavailableReason??'You staged this batch; self-publication is not authorised.'}</p>:null}
  {open&&!blocked?<form aria-label="Confirm valuation publication" onSubmit={event=>onPublish(event,selfReview)}>
   {context?<div className="pnl-confirmation-summary"><h3>Confirm the result you are publishing</h3><dl><dt>Strategy</dt><dd>{context.strategy}</dd><dt>Valuation period</dt><dd>{context.period}</dd><dt>Pricing policy</dt><dd>{context.policy}</dd><dt>Total recorded P&amp;L</dt><dd>{displayAmount(context.total)} {context.currency}</dd><dt>Review mode</dt><dd>{selfReview?'Self-reviewed exception':'Independent review'}</dd></dl>{context.warnings.length?<div className="pnl-review-warning"><strong>Review warnings</strong><ul>{context.warnings.map(warning=><li key={warning}>{warning}</li>)}</ul></div>:null}</div>:null}
   <p>Confirm that you have reviewed this result, its inputs and amendment decisions. The server rechecks permissions, source revisions, pending amendments and real-operator authority.</p>
   {selfReview?<label><input type="checkbox" name="confirmSelfPublication" required disabled={busy}/> I acknowledge that this result will be published as Self-reviewed, without independent review.</label>:null}
   <label>{selfReview?'Reason for self-publication':'Review decision'}<textarea name="comment" required maxLength={2000} disabled={busy} placeholder="Record why this valuation is ready to publish."/></label>
   <div className="pnl-report-actions"><button className="pnl-publish-primary" type="submit" disabled={busy}>{busy?'Publishing…':'Confirm publication'}</button><button type="button" disabled={busy} onClick={()=>{setOpen(false);trigger.current?.focus();}}>Cancel</button></div>
  </form>:null}
 </section>;
}
