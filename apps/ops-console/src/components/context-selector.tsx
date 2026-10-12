'use client';
import {useState} from 'react';
import Link from 'next/link';
import {accessRequest,accessLabel,type Registry} from '@/lib/access-administration';
import {useAccessData} from './access-loader';

export function ContextSelector({initial}:{initial?:Registry}) {
 const {data,error,busy,reload,setBusy,setError}=useAccessData<Registry>('/api/session/context',initial);
 const [tenantId,setTenantId]=useState(''),[userId,setUserId]=useState('');
 const tenant=data?.tenants.find(t=>t.tenantId===tenantId);
 const user=tenant?.users.find(u=>u.userId===userId);
 const tenants=data?.tenants.filter(t=>t.status==='ACTIVE')??[];
 async function reset() {
  setBusy(true);setError('');
  try {await accessRequest('/api/session/context',{method:'DELETE'});window.location.assign('/select-context');}
  catch(e){setError(e instanceof Error?e.message:'Session reset failed.');setBusy(false);}
 }
 async function enter(platform=false) {
  setBusy(true);setError('');
  try {
   await accessRequest('/api/session/context',{method:'POST',body:JSON.stringify(platform?{}:{tenantId,userId})});
   // Full navigation clears forms and in-flight reads from the previous identity.
   window.location.assign(platform?'/platform/tenants':'/tenant-profile');
  }catch(e){setError(e instanceof Error?e.message:'Context switch failed.');setBusy(false);}
 }
 return <main className="mvp-page access-admin-page access-context-page">
  <header className="mvp-header"><div><p className="eyebrow">LOCAL ACCESS TESTING</p><h1>Choose your workspace</h1><p className="muted">Explore a tenant as one of its users, or manage the platform outside tenant workspaces.</p></div><span className="synthetic-badge">DEVELOPMENT ONLY</span></header>
  <div className="access-hint">This is a local development testing tool, not a production login. Changes are real local-database writes, attributed to the operator and selected user.</div>
  {error?<div role="alert" className="error-panel"><p>{error}</p><div className="access-actions"><button className="access-secondary" disabled={busy} onClick={()=>void reload()}>Retry loading</button><button className="access-secondary" disabled={busy} onClick={()=>void reset()}>Reset testing session</button></div></div>:null}
  <div className="access-context-grid">
   <section className="tenant-profile-card access-context-main"><p className="eyebrow">TENANT WORKSPACE</p><h2>Choose a tenant and user</h2><p className="muted">You will use this user’s permissions. Platform administrator privileges are not carried into the tenant.</p>
    <form onSubmit={e=>{e.preventDefault();if(tenant&&user&&!busy)void enter();}}>
     <div className="access-fields"><label><span className="access-step">1</span> Tenant<select required value={tenantId} disabled={busy||!data} onChange={e=>{setTenantId(e.target.value);setUserId('');}}><option value="">Choose tenant</option>{tenants.map(t=><option key={t.tenantId} value={t.tenantId}>{t.name} · {t.code}</option>)}</select></label>
      <label><span className="access-step">2</span> User<select required value={userId} disabled={!tenant||busy} onChange={e=>setUserId(e.target.value)}><option value="">{tenant?'Choose user':'Choose a tenant first'}</option>{tenant?.users.map(u=><option key={u.userId} value={u.userId}>{u.name} · {accessLabel(u.role)}</option>)}</select></label></div>
     <div className="access-context-preview" role="status">
      {!data?'Loading available tenants…':!tenants.length?'No active tenants are available. Use platform administration to review tenant status.':!tenant?'Choose a tenant and user to continue.':!tenant.users.length?'This tenant has no selectable users.':<><strong>{tenant.name}</strong><p>{user?`Enter as ${user.name} · ${accessLabel(user.role)}`:'Choose a user to continue.'}</p><span className="access-hint">Tenant subscriptions — individual access may be narrower</span><div className="module-list">{tenant.moduleCodes.length?tenant.moduleCodes.map(code=><span key={code}>{data.modules.find(m=>m.code===code)?.name??accessLabel(code)}</span>):<span>No enabled modules</span>}</div></>}
      {!tenant&&data&&tenants.length===0?<p>Choose a tenant and user to continue once a tenant is available.</p>:null}
     </div>
     <button className="access-primary" disabled={busy||!tenant||!user}>{busy?'Opening workspace…':'Enter tenant workspace'}</button>
    </form>
   </section>
   <aside className="tenant-profile-card access-context-aside"><p className="eyebrow">SERVICE OPERATOR</p><h2>Platform administration</h2><p className="muted">View tenants and enable or disable their module subscriptions.</p><p className="access-hint">This context is outside any tenant. Switch back here to test a different user.</p><button className="access-secondary" disabled={busy||!data} onClick={()=>void enter(true)}>Enter platform administration</button></aside>
  </div>
  <Link href="/tenant-profile">Back to current tenant</Link>
 </main>;
}
