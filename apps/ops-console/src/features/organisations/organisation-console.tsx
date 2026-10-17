'use client';
import Link from 'next/link';
import {useEffect,useRef,useState} from 'react';
import {BffApiError} from '@/lib/api-errors';
import {submitRetained,type RetainedIntent} from '@/lib/retained-mutation';
import {useRetainedNavigation} from '@/lib/use-retained-navigation';
import {organisationRequest,saveBody,roles,isOrganisationDetail,type OrganisationDetail,type OrganisationPage,type OrganisationRole} from './organisation-client';

type Pending={path:string;body:Record<string,unknown>};
export function OrganisationConsole({tenantId}:{tenantId:string}){
 const [page,setPage]=useState<OrganisationPage|null>(null),[loading,setLoading]=useState(true),[busy,setBusy]=useState(false);
 const [error,setError]=useState(''),[notice,setNotice]=useState(''),[stale,setStale]=useState(false);
 const [query,setQuery]=useState(''),[filter,setFilter]=useState(''),[view,setView]=useState<'mine'|'add'>('mine');
 const [applied,setApplied]=useState({query:'',filter:'',view:'mine' as 'mine'|'add'});
 const [detail,setDetail]=useState<OrganisationDetail|null>(null),[activation,setActivation]=useState<OrganisationRole|null>(null);
 const [uncertain,setUncertain]=useState(false);
 const intent=useRef<RetainedIntent|null>(null),pending=useRef<Pending|null>(null),working=useRef(false);
 const heading=useRef<HTMLHeadingElement>(null),alert=useRef<HTMLDivElement>(null),sequence=useRef(0);
 useRetainedNavigation(intent);
 const locked=busy||uncertain||stale;
 async function load(offset=0,search=applied.query,role=applied.filter,section=applied.view){
  const stamp=++sequence.current;setLoading(true);setError('');
  try{
   const params=new URLSearchParams({q:search,offset:String(offset),limit:'25'});
   if(role&&section==='mine')params.set('role',role);
   const data=await organisationRequest<OrganisationPage>(tenantId,`${section==='add'?'organisations/candidates':'organisations'}?${params}`);
   if(stamp===sequence.current){setPage(data);setApplied({query:search,filter:role,view:section});setStale(false);}
  }catch(e){if(stamp===sequence.current){setPage(null);setError((e as Error).message);}}
  finally{if(stamp===sequence.current)setLoading(false);}
 }
 useEffect(()=>{void load();return()=>{sequence.current++;};},[tenantId]);
 useEffect(()=>{if(detail||activation)heading.current?.focus();},[detail?.organisationId,activation]);
 useEffect(()=>{if(error)alert.current?.focus();},[error]);
 async function open(identifier:string){
  if(working.current)return;working.current=true;setBusy(true);setError('');setNotice('');
  try{setDetail(await organisationRequest<OrganisationDetail>(tenantId,`organisations/${identifier}`));}
  catch(e){setError((e as Error).message);}finally{setBusy(false);working.current=false;}
 }
 async function send(command:Pending){
  if(working.current)return;working.current=true;setBusy(true);setError('');setNotice('');pending.current=command;
  try{
   const saved=await submitRetained(command,intent,async(data,key)=>organisationRequest<OrganisationDetail|OrganisationPage['policies']>(
    tenantId,data.path,{...data.body,idempotencyKey:key}));
   pending.current=null;setUncertain(false);setStale(true);
   setNotice('Saved. Changes apply to new selections; historical records are unchanged.');
   setActivation(null);
   if(isOrganisationDetail(saved))setDetail(saved);else setDetail(null);
   // Commit is already confirmed. A failed refresh must never suggest resubmission.
   await load(page?.offset??0);
  }catch(e){
   if(e instanceof BffApiError&&e.status===409&&e.code==='organisation.conflict'){
    intent.current=null;pending.current=null;setStale(true);setUncertain(false);
   }else if(!intent.current){pending.current=null;setUncertain(false);}
   else setUncertain(true);
   setError(e instanceof Error?e.message:'The outcome could not be confirmed.');
  }finally{working.current=false;setBusy(false);}
 }
 async function reload(){
  if(working.current)return;working.current=true;setBusy(true);
  try{
   if(detail)setDetail(await organisationRequest<OrganisationDetail>(tenantId,`organisations/${detail.organisationId}`));
   await load(page?.offset??0);
  }catch(e){setError((e as Error).message);}finally{working.current=false;setBusy(false);}
 }
 function switchView(next:'mine'|'add'){
  setView(next);setQuery('');setFilter('');setDetail(null);setActivation(null);setNotice('');void load(0,'','',next);
 }
 return <main className="mvp-page organisation-page">
  <header className="mvp-header"><div><Link href="/tenant-profile">← Tenant profile</Link><p className="eyebrow">TENANT REFERENCE SETTINGS</p>
   <h1>Organisations</h1><p className="muted">Manage counterparties and executing brokers without duplicating their legal identity.</p></div></header>
  <p className="access-hint">Available to this tenant does not mean credit or KYC approval. Legal details are shared; your labels, codes and notes are private.</p>
  {error?<div role="alert" tabIndex={-1} ref={alert} className="error-panel"><strong>There is a problem</strong><p>{error}</p>
   <button type="button" disabled={busy} onClick={()=>void reload()}>Reload current state</button></div>:null}
  {notice?<p role="status" className="configuration-notice">{notice}</p>:null}
  {uncertain?<section className="organisation-warning" aria-label="Unconfirmed change"><h2>Outcome not confirmed</h2>
   <p>Your exact request and retry key are retained. Editing is locked; retry the unchanged request to confirm the outcome.</p>
   <button disabled={busy} onClick={()=>pending.current&&void send(pending.current)}>Retry unchanged request</button></section>:null}
  <section className="organisation-policies" aria-label="Trading role eligibility">
   {(Object.keys(roles) as OrganisationRole[]).map(role=><article key={role} className="tenant-profile-card"><h2>{roles[role]}</h2>
    {!page?<p>{loading?'Loading role configuration…':'Role configuration unavailable.'}</p>:page.policies[role].mode==='LEGACY'?<>
     <span className="access-status">Not restricted by a tenant list</span><p>Existing shared eligibility still applies. Adding notes does not change this.</p>
     <button type="button" disabled={locked||loading} onClick={()=>{setDetail(null);setActivation(role);}}>Set up {roles[role].toLowerCase()} list</button>
    </>:<><span className="access-status">Tenant-curated · v{page.policies[role].versionNo}</span><p>Only selected active organisations can be used for this role. An empty list allows none.</p></>}
   </article>)}
  </section>
  {activation?<section className="tenant-profile-card organisation-editor" aria-labelledby="organisation-editor-title">
   <h2 id="organisation-editor-title" ref={heading} tabIndex={-1}>Set up {roles[activation].toLowerCase()} list</h2>
   <p>This changes future booking eligibility. Only the initial organisation below will be enabled; you can add others afterwards.</p>
   <form onSubmit={e=>{e.preventDefault();const data=new FormData(e.currentTarget);void send({path:`organisation-roles/${activation}`,body:{
    expectedVersion:0,ids:detail?[detail.organisationId]:[],reason:String(data.get('reason'))}});}}>
    <fieldset disabled={locked}><p className="organisation-warning">{detail?`Initial selection: ${detail.legalName}`:'No initial organisation selected: this will create an empty list and block new selection for this role.'}</p>
     <label>Reason for list activation<textarea name="reason" required maxLength={2000}/></label>
     <label className="organisation-check"><input type="checkbox" required/>I understand this restricts future selections.</label>
     <div className="organisation-actions"><button>Activate curated list</button><button type="button" onClick={()=>setActivation(null)}>Cancel</button></div>
    </fieldset></form>
   <p>To start with one organisation instead, cancel and find it using Add organisation, then activate this role from its detail.</p>
  </section>:detail?<section className="tenant-profile-card organisation-editor" aria-labelledby="organisation-editor-title">
   <h2 id="organisation-editor-title" ref={heading} tabIndex={-1}>{detail.displayName}</h2><p>{detail.legalName} · {detail.status}</p>
   <p>LEI: {detail.leis.join(', ')||'Not recorded'}</p>
   <form key={`${detail.organisationId}:${detail.versionNo}:${JSON.stringify(detail.policies)}`} onSubmit={e=>{
    e.preventDefault();void send({path:`organisations/${detail.organisationId}`,body:saveBody(detail,new FormData(e.currentTarget))});}}>
    <fieldset disabled={locked}><div className="organisation-fields"><label>Tenant label<input name="label" maxLength={250} defaultValue={detail.label??''} placeholder={detail.displayName}/></label>
     <label>Internal code<input name="internalCode" maxLength={100} defaultValue={detail.internalCode??''}/></label></div>
     <label>Private notes<textarea name="notes" maxLength={2000} defaultValue={detail.notes??''}/></label>
     <fieldset><legend>Permitted trading roles</legend>{(Object.keys(roles) as OrganisationRole[]).map(role=>detail.policies[role].mode==='CURATED'
      ?<label key={role} className="organisation-check"><input name={role} type="checkbox" defaultChecked={detail.roles[role]} disabled={detail.status!=='ACTIVE'&&!detail.roles[role]}/>{roles[role]}</label>
      :<div key={role}><p>{roles[role]}: shared eligibility, not a curated list.</p><button type="button" onClick={()=>setActivation(role)}>Set up {roles[role].toLowerCase()} list with this organisation</button></div>)}</fieldset>
     <label>Reason for change<textarea name="reason" required maxLength={2000}/></label>
     <div className="organisation-actions"><button>{busy?'Saving…':'Save organisation'}</button><button type="button" onClick={()=>setDetail(null)}>Close editor</button></div>
    </fieldset></form>
   <details><summary>Recent organisation changes</summary><p>Latest 20 profile commands. Full role-list publications remain in Trade configuration → Audit history.</p>
    {detail.history.length?<ol>{detail.history.map(event=><li key={event.eventId}><time>{event.recordedAtUtc}</time> · {event.reason}<details><summary>Role changes and actor</summary><pre>{JSON.stringify({actor:event.actorId,changes:event.changes},null,2)}</pre></details></li>)}</ol>:<p>No profile changes loaded. Reload current state after saving to inspect the recorded change.</p>}</details>
  </section>:null}
  <section className="tenant-profile-card" aria-label="Organisation register">
   <div className="organisation-actions"><button disabled={locked} aria-pressed={view==='mine'} onClick={()=>switchView('mine')}>My organisations</button>
    <button disabled={locked} aria-pressed={view==='add'} onClick={()=>switchView('add')}>Add organisation</button></div>
   <h2>{view==='mine'?'Tenant organisation register':'Find an existing organisation'}</h2>
   {view==='add'?<p>Search the existing platform records. The full GLEIF directory is a later phase. Select a record to add private settings or permitted roles.</p>:null}
   <form className="organisation-search" onSubmit={e=>{e.preventDefault();setDetail(null);setActivation(null);void load(0,query,filter,view);}}><label>Search organisations<input type="search" value={query} maxLength={250} onChange={e=>setQuery(e.target.value)} disabled={locked} placeholder="Name, LEI or internal code"/></label>
    {view==='mine'?<label>Role filter<select disabled={locked} value={filter} onChange={e=>setFilter(e.target.value)}><option value="">All organisations</option>{Object.entries(roles).map(([r,name])=><option key={r} value={r}>{name}</option>)}</select></label>:null}
    <button disabled={locked||loading}>Search</button></form>
   {loading?<p role="status">Loading organisations…</p>:page?<>
    <div className="organisation-table"><table><caption>{view==='mine'?'Tenant-selected organisations':'Existing platform organisations'} · {page.total} matching</caption>
     <thead><tr><th scope="col">Organisation</th><th scope="col">Internal code</th><th scope="col">Selected roles</th><th scope="col">Action</th></tr></thead>
     <tbody>{page.items.map(row=><tr key={row.organisationId}><th scope="row">{row.displayName}<small>{row.legalName} · {row.status}</small>{row.leis.length?<small>LEI {row.leis.join(', ')}</small>:null}</th>
      <td>{row.internalCode??'—'}</td><td>{(Object.keys(roles) as OrganisationRole[]).filter(r=>row.roles[r]).map(r=>roles[r]).join(', ')||'No curated roles'}</td>
      <td><button disabled={locked} onClick={()=>{setActivation(null);void open(row.organisationId);}} aria-label={`Manage ${row.displayName}`}>Manage</button></td></tr>)}</tbody></table></div>
    {!page.items.length?<p>No organisations match. {view==='mine'?'Use Add organisation to choose an existing platform record.':'Try a different name or LEI.'}</p>:null}
    <nav className="organisation-actions" aria-label="Organisation pages"><button disabled={locked||page.offset===0} onClick={()=>void load(Math.max(0,page.offset-25))}>Previous</button>
     <span>{page.total?`${page.offset+1}–${Math.min(page.offset+page.items.length,page.total)} of ${page.total}`:'0 matching'}</span>
     <button disabled={locked||page.offset+page.limit>=page.total} onClick={()=>void load(page.offset+25)}>Next</button></nav>
   </>:<p>Organisation data is unavailable. Reload current state to try again.</p>}
  </section>
  <Link href="/tenant-profile/trade-configuration">Trade fields, trader eligibility and audit history →</Link>
 </main>;
}
