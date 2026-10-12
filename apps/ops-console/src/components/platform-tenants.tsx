'use client';
import {useState,type FormEvent} from 'react';
import Link from 'next/link';
import {accessLabel,type Registry,type RegistryTenant} from '@/lib/access-administration';
import {useAccessData} from './access-loader';

export function PlatformTenants({initial}:{initial?:Registry}) {
 const {data,error,busy,reload,command}=useAccessData<Registry>('/api/platform/tenants',initial);
 const [editor,setEditor]=useState<{tenant:RegistryTenant;mode:'profile'|'status'}>();
 const [notice,setNotice]=useState('');
 async function save(tenant:RegistryTenant,body:unknown) {
  setNotice('');
  if(await command(`/api/platform/tenants/${tenant.tenantId}`,body,'PUT')) {
   setEditor(undefined);setNotice('Tenant update saved. Refresh the list if it could not be reloaded.');
  }
 }
 return <main className="mvp-page access-admin-page"><header className="mvp-header"><div><p className="eyebrow">SERVICE OPERATOR · OUTSIDE TENANTS</p><h1>Tenant administration</h1><p className="muted">Manage tenant details, operational status and module subscriptions. Suspension never deletes tenant data.</p></div><Link className="access-secondary" href="/select-context">Switch context</Link></header>
  {error?<div className="error-panel" role="alert">{error} <Link href="/select-context">Select platform context</Link></div>:null}
  <p role="status" className="access-feedback">{busy?'Saving tenant changes…':notice}</p>
  <div className="access-toolbar"><p className="access-hint">{data?data.tenants.length+' tenants':'Loading tenants…'} · Contact details do not grant access or create accounts.</p><button className="access-secondary" disabled={busy||!!editor} onClick={()=>{setNotice('');void reload();}}>Refresh tenants</button></div>
  <section className="access-tenant-cards">{data?.tenants.map(tenant=><article key={tenant.tenantId} className="tenant-profile-card"><p className="eyebrow">{tenant.code}</p><h2>{tenant.name}</h2><p><span className={tenant.status==='ACTIVE'?'access-status':'muted'}>{accessLabel(tenant.status)}</span> · {tenant.users.length} active memberships</p>
   <p className="access-hint">{tenant.contactName??'No operational contact'}{tenant.contactEmail?<><br/>{tenant.contactEmail}</>:null}</p>
   <div className="access-actions"><button className="access-secondary" disabled={busy||!!editor||tenant.profileVersion===undefined||!['ACTIVE','SUSPENDED'].includes(tenant.status)} onClick={()=>setEditor({tenant,mode:'profile'})}>Edit tenant</button>
    {['ACTIVE','SUSPENDED'].includes(tenant.status)?<button className="access-secondary" disabled={busy||!!editor||tenant.profileVersion===undefined} onClick={()=>setEditor({tenant,mode:'status'})}>{tenant.status==='ACTIVE'?'Suspend tenant':'Reactivate tenant'}</button>:null}</div>
   {tenant.profileVersion===undefined?<p className="access-hint">Tenant editing requires the updated API and schema.</p>:null}
   {editor?.tenant.tenantId===tenant.tenantId?<TenantProfileEditor key={editor.tenant.tenantId+editor.mode} tenant={editor.tenant} mode={editor.mode} busy={busy} cancel={()=>setEditor(undefined)} save={body=>save(editor.tenant,body)}/>:null}
   <fieldset disabled={busy||!!editor||tenant.status!=='ACTIVE'}><legend>Module subscriptions</legend>{data.modules.map(module=><label key={module.code} className="access-check"><input type="checkbox" checked={tenant.moduleCodes.includes(module.code)} onChange={async e=>{setNotice('');if(await command(`/api/platform/tenants/${tenant.tenantId}/modules/${module.code}`,{enabled:e.target.checked},'PUT'))setNotice('Module subscription updated.');}}/>{module.name}</label>)}</fieldset>
   {tenant.status!=='ACTIVE'?<p className="access-hint">Subscriptions are retained but tenant access is blocked. Reactivate the tenant before changing modules.</p>:null}
   <details><summary>Active memberships</summary><ul>{tenant.users.map(user=><li key={user.userId}>{user.name} · {accessLabel(user.role)}</li>)}</ul></details>
  </article>)}</section>
  <p className="access-hint">Module access is separate from provider-data licensing. Tenant groups cannot grant a disabled module.</p>
 </main>;
}

export function TenantProfileEditor({tenant,mode,busy,cancel,save}:{tenant:RegistryTenant;mode:'profile'|'status';busy:boolean;cancel:()=>void;save:(body:unknown)=>Promise<void>}) {
 const nextStatus=tenant.status==='ACTIVE'?'SUSPENDED':'ACTIVE';
 async function submit(e:FormEvent<HTMLFormElement>) {
  e.preventDefault();
  const values=new FormData(e.currentTarget);
  await save({
   name:mode==='profile'?values.get('name'):tenant.name,
   contactName:mode==='profile'?values.get('contactName')||null:tenant.contactName??null,
   contactEmail:mode==='profile'?values.get('contactEmail')||null:tenant.contactEmail??null,
   status:mode==='status'?nextStatus:tenant.status,
   expectedVersion:tenant.profileVersion,
   confirmStatusChange:mode==='status',
  });
 }
 return <form className="access-editor" onSubmit={submit}>
  <h3>{mode==='profile'?'Edit tenant details':nextStatus==='SUSPENDED'?'Suspend this tenant?':'Reactivate this tenant?'}</h3>
  <dl><dt>Tenant code · read-only</dt><dd>{tenant.code}</dd><dt>Tenant ID · immutable</dt><dd><code className="access-identifier">{tenant.tenantId}</code></dd></dl>
  {mode==='profile'?<fieldset disabled={busy}><legend>Operational details</legend><label>Display name<input autoFocus name="name" required maxLength={250} defaultValue={tenant.name}/></label><label>Operational contact name<input name="contactName" maxLength={250} defaultValue={tenant.contactName??''}/></label><label>Operational contact email<input name="contactEmail" type="email" maxLength={254} defaultValue={tenant.contactEmail??''}/></label><p className="access-hint">Optional contact details. No email invitation or access grant is sent.</p></fieldset>
   :<p role="status" className="access-hint">{nextStatus==='SUSPENDED'?'All users will lose access to this tenant, including existing sessions. Strategies, trades, memberships and subscriptions are retained.':'Users regain access according to their existing active memberships, group permissions and enabled modules. Suspended accounts or memberships remain blocked.'}</p>}
  <div className="access-actions"><button className="access-primary" disabled={busy}>{busy?'Saving…':mode==='profile'?'Save tenant details':nextStatus==='SUSPENDED'?'Confirm suspension':'Confirm reactivation'}</button><button className="access-secondary" type="button" disabled={busy} onClick={cancel}>Cancel</button></div>
  <p className="access-hint">Changes are audited. If details have changed elsewhere, cancel, refresh and reopen this editor.</p>
 </form>;
}
