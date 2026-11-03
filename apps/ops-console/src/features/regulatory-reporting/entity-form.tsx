'use client';
import {useState,type FormEvent} from 'react';
import {reportingRequest} from './transport';
import type {Profile} from './presentation';
export const firmCategories={MIFID_FIRM:'UK MiFID investment firm',CREDIT_INSTITUTION:'UK credit institution',THIRD_COUNTRY_BRANCH:'UK branch of overseas investment firm',SMALL_AIFM_MIFID:'Small authorised UK AIFM with MiFID permissions',COLLECTIVE_MANAGER:'Collective portfolio manager / AIFM / UCITS',OTHER:'Other — assess individually'};
export function EntityForm({profile,onSaved,onCancel}:{profile?:Profile;onSaved:()=>void;onCancel:()=>void}){
 const [saving,setSaving]=useState(false);const [error,setError]=useState('');
 async function submit(event:FormEvent<HTMLFormElement>){
  event.preventDefault();const form=event.currentTarget;const values=Object.fromEntries(new FormData(form));setSaving(true);setError('');
  try{await reportingRequest('profiles'+(profile?'/'+profile.profileId:''),{...values,...(profile?{expectedRevision:profile.revision}:{})});onSaved();}
  catch(error){setError((error as Error).message);}finally{setSaving(false);}
 }
 return <form onSubmit={submit} className="reg-card"><h2>{profile?'Edit reporting entity':'Add reporting entity'}</h2><p>Record the legal firm’s assessed obligation. Its category alone does not establish reportability.</p>
  {error?<p role="alert" className="error-panel">{error}</p>:null}<fieldset disabled={saving} className="reg-form-grid"><legend>Legal entity and scope</legend>
  <label>Legal name<input name="name" required maxLength={250} defaultValue={profile?.name}/></label>
  <label>LEI<input name="lei" required maxLength={20} minLength={20} pattern="[A-Z0-9]{18}[0-9]{2}" defaultValue={profile?.lei}/></label>
  <label>Regulatory category<select name="firmCategory" defaultValue={profile?.firmCategory??'OTHER'}>{Object.entries(firmCategories).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
  <label>Assessed UK MiFIR firm scope<select name="firmScope" defaultValue={profile?.firmScope??'UNASSESSED'}><option value="UNASSESSED">Not assessed</option><option value="IN_SCOPE">In scope</option><option value="OUT_OF_SCOPE">Out of scope</option></select></label>
  <label className="reg-wide">Assessment / change reason<textarea name="reason" minLength={3} required maxLength={2000} defaultValue={profile?.reason}/></label>
  </fieldset><div className="ticket-actions"><button type="submit" disabled={saving}>{saving?'Saving…':'Save entity'}</button><button type="button" disabled={saving} onClick={onCancel}>Cancel</button></div>
 </form>;
}
