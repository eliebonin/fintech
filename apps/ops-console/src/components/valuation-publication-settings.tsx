'use client';
import {useEffect,useState,type FormEvent} from 'react';
import {accessRequest} from '@/lib/access-administration';
type Policy={enabled:boolean;active:boolean;validUntil:string|null;revision:number;reason:string};
/** Tenant governance only; enabling this never grants users operational actions. */
export function ValuationPublicationSettings({tenantId,userId}:{tenantId:string;userId:string}){
 const [policy,setPolicy]=useState<Policy|null>(null),[error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{let live=true;accessRequest<Policy>('/api/access/valuation-publication-policy').then(value=>{if(live)setPolicy(value);}).catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[tenantId,userId]);
 async function save(event:FormEvent<HTMLFormElement>){
  event.preventDefault();if(!policy)return;const fields=new FormData(event.currentTarget);setBusy(true);setError('');setNotice('');
  const enabled=fields.get('enabled')==='on',day=String(fields.get('validUntil')??'');
  try{const value=await accessRequest<Policy>('/api/access/valuation-publication-policy',{method:'PUT',headers:{'X-Expected-Tenant-Id':tenantId,'X-Expected-User-Id':userId},body:JSON.stringify({enabled,validUntil:enabled&&day?`${day}T23:59:59.999Z`:null,expectedRevision:policy.revision,reason:String(fields.get('reason')??''),confirmChange:fields.get('confirmChange')==='on'})});setPolicy(value);setNotice('Policy saved. Group grants are still required; no user permissions were added.');}
  catch(e){setError((e as Error).message);}finally{setBusy(false);}
 }
 return <section className="access-editor" aria-label="Valuation publication governance"><h2>Valuation self-publication</h2><p>Independent review remains the default. Enable an explicit exception for small teams or temporary cover, then grant Self-publish valuations and Review valuations to the appropriate group and strategies.</p>
  {error?<p role="alert">{error}</p>:null}{notice?<p role="status">{notice}</p>:null}
  {policy?<><p>Current policy: <strong>{policy.active?'Self-publication permitted':policy.enabled?'Temporary cover expired':'Independent review required'}</strong> · revision {policy.revision}</p>
   <form key={`${tenantId}:${userId}:${policy.revision}`} onSubmit={save}><fieldset disabled={busy}><legend>Tenant opt-in — no automatic group grants</legend>
    <label><input type="checkbox" name="enabled" defaultChecked={policy.enabled}/> Permit authorised self-publication</label>
    <label>Allow until (UTC date, inclusive; optional)<input type="date" name="validUntil" defaultValue={policy.validUntil?.slice(0,10)}/></label><p>Leave blank for standing permission. An expiry applies to this tenant opt-in, not to one individual's membership.</p>
    <label>Reason for policy change<textarea name="reason" required maxLength={2000}/></label>
    <label><input type="checkbox" name="confirmChange" required/> I confirm this governance change. It does not waive financial checks or amendment independence.</label>
   </fieldset><button className="access-primary" disabled={busy}>{busy?'Saving…':'Save publication policy'}</button></form></>:<p>Loading publication policy…</p>}
 </section>;
}
