"use client";
import {useEffect,useState,type FormEvent} from 'react';
import styles from './lifecycle-allocation-policy.module.css';
import {configurationRequest,type ConfiguredProperty} from '@/lib/trade-configuration-client';
type Behavior='ALLOCATION'|'INHERIT'|'INPUT';
type Policy={revision:number;fields:{definitionId:string;behavior:Behavior}[]};
export function AllocationPolicyFields({fields,rules,disabled,onChange}:{fields:ConfiguredProperty[];rules:Record<string,Behavior>;disabled:boolean;onChange:(id:string,behavior:Behavior)=>void}){
 return <div className={styles.tableWrap}><table className={styles.table}>
  <caption className="configuration-sr-only">Custom-field lifecycle allocation behavior</caption>
  <thead><tr><th scope="col">Custom field</th><th scope="col">Lifecycle behavior</th></tr></thead>
  <tbody>{fields.map(f=><tr key={f.definitionId}>
   <th scope="row"><span>{f.label}</span><small>{f.status==='RETIRED'?'Retired · ':''}{f.required?'Required':'Optional'}</small></th>
   <td><select aria-label={`Lifecycle behavior for ${f.label}`} value={rules[f.definitionId]??'INPUT'} disabled={disabled} onChange={e=>onChange(f.definitionId,e.target.value as Behavior)}>
    <option value="INPUT">New booking input</option><option value="INHERIT">Inherit when sources agree</option><option value="ALLOCATION">Preserve position allocation</option>
   </select></td>
  </tr>)}</tbody>
 </table></div>;
}
export function LifecycleAllocationPolicy({tenantId,fields,disabled=false}:{tenantId:string;fields:ConfiguredProperty[];disabled?:boolean}){
 const [policy,setPolicy]=useState<Policy|null>(null),[rules,setRules]=useState<Record<string,Behavior>>({}),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[search,setSearch]=useState(''),[offset,setOffset]=useState(0),[dirty,setDirty]=useState(false);
 useEffect(()=>{let live=true;configurationRequest<Policy>(tenantId,'lifecycle-allocations').then(p=>{if(live){setPolicy(p);setRules(Object.fromEntries(p.fields.map(f=>[f.definitionId,f.behavior])));}}).catch(e=>{if(live)setError(e instanceof Error?e.message:'Allocation settings unavailable');});return()=>{live=false;};},[tenantId]);
 const visible=fields.filter(f=>(f.status==='ACTIVE'||!!rules[f.definitionId])&&(f.label+' '+f.code).toLowerCase().includes(search.toLowerCase()));
 async function save(e:FormEvent<HTMLFormElement>){e.preventDefault();if(!policy||busy)return;const form=e.currentTarget,reason=String(new FormData(form).get('reason')??'');setBusy(true);setError('');setNotice('');try{const retained=await configurationRequest<Policy>(tenantId,'lifecycle-allocations',{expectedRevision:policy.revision,fields:Object.entries(rules).filter(([id,behavior])=>behavior!=='INPUT'&&fields.some(f=>f.definitionId===id)).map(([definitionId,behavior])=>({definitionId,behavior})),reason,confirmImpact:true});setPolicy(retained);setDirty(false);form.reset();setNotice('Allocation rules saved. Prepared lifecycle entries must be revalidated. Existing trades remain unchanged.');}catch(e){setError(e instanceof Error?e.message:'Allocation change was not confirmed');}finally{setBusy(false);}}
 return <details className={`configuration-editor ${styles.panel}`}>
  <summary><strong>Lifecycle allocation rules</strong><span className={styles.summaryHint}>Preserve classifications when closing positions</span></summary>
  <div className={styles.content}>
   <p>Choose which custom fields distinguish allocations. Each allocation is closed separately at bond or deliverable FX-forward maturity. The ordinary position report stays economically aggregated.</p>
   <dl className={styles.guide}>
    <div><dt>Preserve position allocation</dt><dd>Close each classified quantity separately and inherit its values read-only.</dd></div>
    <div><dt>Inherit when sources agree</dt><dd>Prefill matching metadata without dividing the position.</dd></div>
    <div><dt>New booking input</dt><dd>Ask Ops for applicable values on the closing entry.</dd></div>
   </dl>
   {error?<p role="alert" className="configuration-error">{error}</p>:null}
   {notice?<p role="status" className="configuration-notice">{notice}</p>:null}
   {!policy?<p>{error?'Allocation policy unavailable. Reload the page to try again.':'Loading allocation policy…'}</p>:<form onSubmit={save}>
    <fieldset className={`configuration-controls ${styles.controls}`} disabled={disabled||busy}>
     <legend className="configuration-sr-only">Edit lifecycle allocation rules</legend>
     <div className={styles.toolbar}>
      <label>Find a custom field<input type="search" value={search} placeholder="Search by label or code" onChange={e=>{setSearch(e.target.value);setOffset(0);}}/></label>
      <p className={styles.revision}>Policy revision {policy.revision}<small>No fields are inferred from their names.</small></p>
     </div>
     <AllocationPolicyFields fields={visible.slice(offset,offset+25)} rules={rules} disabled={disabled||busy} onChange={(id,behavior)=>{setRules(current=>({...current,[id]:behavior}));setDirty(true);setNotice('');}}/>
     {!visible.length?<p>No matching active custom fields.</p>:null}
     {visible.length>25?<nav aria-label="Allocation field pagination" className="configuration-pagination"><span>{offset+1}–{Math.min(offset+25,visible.length)} of {visible.length}</span><div><button type="button" disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-25))}>Previous</button><button type="button" disabled={offset+25>=visible.length} onClick={()=>setOffset(offset+25)}>Next</button></div></nav>:null}
     <div className={styles.audit}>
      <label>Change reason<textarea name="reason" required maxLength={2000} rows={3} aria-describedby="allocation-reason-help"/></label><small id="allocation-reason-help" className={styles.auditHelp}>Recorded with this policy revision in the audit history.</small>
      <label className={`configuration-check ${styles.acknowledgement}`}><input type="checkbox" required/><span>I understand that changing allocation rules may require reconciling historical classifications. No trades will be relabelled automatically.</span></label>
      <div className="configuration-form-actions"><button className="configuration-primary" disabled={!dirty||busy}>{busy?'Saving…':'Save allocation rules'}</button></div>
     </div>
    </fieldset>
   </form>}
  </div>
 </details>;
}
