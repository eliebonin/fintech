'use client';
import Link from 'next/link';
import {accessLabel,type AccessExplanation,type EffectiveAccess} from '@/lib/access-administration';
import {useAccessData} from './access-loader';

const reasons:Record<string,string>={
 ACCOUNT_INACTIVE:'Account is inactive',MEMBERSHIP_INACTIVE:'Membership is inactive',
 MODULE_NOT_ENABLED:'None of the required tenant modules is enabled',
 NO_ACTIVE_ACTION_GRANT:'No active group grants this action',
 NO_STRATEGY_SCOPE:'No current strategy is included in the granting groups’ scope',
};
function ActionList({actions}:{actions:AccessExplanation[]}) {
 return <ul className="access-module-rows">{actions.map(action=><li key={action.code}><div><strong>{accessLabel(action.code)}</strong><p className="access-hint">{action.grantSources.length?`Granted by: ${action.grantSources.join(', ')}`:'No active grant source'}</p>{action.strategyNames?<p className="access-hint">Strategies: {action.strategyNames.join(', ')||'none'}</p>:null}{action.blockers.map(reason=><p className="access-hint" key={reason}>{reasons[reason]??accessLabel(reason)}</p>)}{action.moduleCodes.length>1?<p className="access-hint">Requires any one of: {action.moduleCodes.map(accessLabel).join(', ')}</p>:null}</div><span className={action.allowed?'access-status':'muted'}>{action.allowed?'Allowed':'Not allowed'}</span></li>)}</ul>;
}

export function EffectiveAccessView({data}:{data:EffectiveAccess}) {
 const granted=data.actions.filter(action=>action.allowed).length;
 return <main className="mvp-page access-admin-page"><header className="mvp-header"><div><p className="eyebrow">EFFECTIVE ACCESS</p><h1>{data.name}</h1><p className="muted">Why this member can—or cannot—use each capability. Current as of {data.asOfDate}.</p></div><Link className="access-secondary" href="/tenant-profile">Tenant profile</Link></header>
  <div className="access-summary"><span><strong>{data.modules.filter(module=>module.enabled).length}</strong> enabled subscriptions</span><span><strong>{granted}</strong> allowed actions</span><span>{accessLabel(data.role)}</span></div>
  <section className="tenant-profile-card"><h2>Membership &amp; groups</h2><p>Account: {accessLabel(data.accountStatus)} · Membership: {accessLabel(data.membershipStatus)}</p>
   {data.groups.length?<ul>{data.groups.map(group=><li key={group.groupId}>{group.name} — {accessLabel(group.status)}{group.status!=='ACTIVE'?' (grants ignored)':''}</li>)}</ul>:<p>No group assignments.</p>}
   <p className="access-hint">Tenant administrators manage users and groups without a module subscription. All operational actions require explicit active group grants, including for administrators. Group names alone confer no authority. Platform administration grants no tenant access.</p>
   <p className="access-hint">Strategy scope: {data.strategyScope}</p>
   <details><summary>Access administration</summary><ActionList actions={data.actions.filter(action=>!action.moduleCodes.length)}/></details>
  </section>
  <h2>Modules</h2><p className="muted">Subscription, personal permission and product delivery are separate. Enabling a planned module does not deliver its workflow.</p>
  <div className="access-profile-grid">{data.modules.map(module=><section key={module.code} className="tenant-profile-card"><h3>{module.name}</h3><p><span className={module.enabled?'access-status':'muted'}>{module.enabled?'Enabled':'Not enabled'}</span> · {module.accessible?'Actions granted':'No actions granted'} · {accessLabel(module.deliveryStatus)}</p><p className="access-hint">{module.deliveryNote}</p>
   {module.actions.length?<details><summary>Explain actions ({module.actions.filter(action=>action.allowed).length}/{module.actions.length} allowed)</summary><ActionList actions={module.actions}/></details>:<p className="access-hint">No standalone actions are assigned to this module in the current action catalogue.</p>}
  </section>)}</div>
 </main>;
}

export function EffectiveAccessConsole({userId}:{userId?:string}) {
 const {data,error,reload}=useAccessData<EffectiveAccess>('/api/effective-access'+(userId?'?userId='+encodeURIComponent(userId):''));
 if(error)return <main className="mvp-page"><h1>Effective access</h1><p role="alert">{error}</p><button onClick={()=>void reload()}>Retry</button><p><Link href="/tenant-profile">Back to tenant profile</Link></p></main>;
 if(!data)return <main className="mvp-page"><h1>Effective access</h1><p role="status">Loading current permissions…</p></main>;
 return <EffectiveAccessView data={data}/>;
}
