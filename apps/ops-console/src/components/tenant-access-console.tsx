'use client';

import {useState, useRef, useEffect, type FormEvent, type KeyboardEvent} from 'react';
import Link from 'next/link';
import {accessLabel,accessRequest, type TenantAccess, type AccessUser, type AccessGroup} from '@/lib/access-administration';
import {StrategyAccessMatrix} from './strategy-access-matrix';
import {actionTitle,actionDescription,groupScopeSummary} from '@/lib/access-presentation';
import {useAccessData} from './access-loader';
import {ValuationPublicationSettings} from './valuation-publication-settings';

type Tab = 'users' | 'groups' | 'strategies';

export function TenantAccessConsole({initial, initialTab = 'users'}:{initial?:TenantAccess; initialTab?:Tab}) {
 const {data,error,busy,stale,reload,command} = useAccessData<TenantAccess>('/api/access',initial);
 const [tab,setTab] = useState<Tab>(initialTab);
 const [query,setQuery] = useState('');
 const [editor,setEditor] = useState<'user'|'group'|undefined>();
 const [editingGroup,setEditingGroup] = useState<AccessGroup>();
 const [editingUser,setEditingUser] = useState<AccessUser>();
 const [notice,setNotice] = useState('');
 const headers = data ? {'X-Expected-Tenant-Id':data.tenantId,'X-Expected-User-Id':data.userId} : undefined;
 const close = () => {setEditor(undefined);setEditingGroup(undefined);setEditingUser(undefined);};
 async function save(path:string, body:unknown, method='PUT') {
  setNotice('');
  const ok = await command(path,body,method,headers);
  if(ok) setNotice('Change saved. The access list has been refreshed where available.');
  return ok;
 }
 function selectTab(next:Tab) {
  setTab(next);setQuery('');
  window.history.replaceState(null,'',`?view=${next}`);
 }
 function tabKey(e:KeyboardEvent<HTMLButtonElement>) {
  if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key)) return;
  e.preventDefault();
  const tabs:Tab[]=['users','groups','strategies'];
  const next:Tab = e.key==='Home'?'users':e.key==='End'?'strategies':tabs[(tabs.indexOf(tab)+(e.key==='ArrowRight'?1:2))%3];
  selectTab(next);
  document.getElementById(`access-${next}-tab`)?.focus();
 }
 async function createUser(e:FormEvent<HTMLFormElement>) {
  e.preventDefault();
  const values = new FormData(e.currentTarget);
  if(await save('/api/access/users',{name:values.get('name'),role:values.get('role')},'POST')) close();
 }
 const search = query.trim().toLowerCase();
 const users = data?.users.filter(user => [user.name,accessLabel(user.role),user.status,
  ...user.groupIds.map(id=>data.groups.find(g=>g.groupId===id)?.name??'')].join(' ').toLowerCase().includes(search)) ?? [];
 const groups = data?.groups.filter(group=>[group.name,group.code,group.description,group.status].join(' ').toLowerCase().includes(search)) ?? [];
 const currentUser = data?.users.find(user=>user.userId===editingUser?.userId);

 return <main className="mvp-page access-admin-page">
  <header className="mvp-header"><div><p className="eyebrow">TENANT ADMINISTRATION</p><h1>Users &amp; groups</h1><p className="muted">Manage people, define group permissions and check access to each strategy.</p></div>
   <Link className="access-secondary" href="/tenant-profile">Tenant profile</Link></header>
  {error?<div role="alert" className="error-panel">{error}{stale?<button type="button" disabled={busy} onClick={()=>void reload()}>Refresh current state</button>:null}</div>:null}
  <p className="access-feedback" role="status">{busy?'Saving access changes…':notice}</p>
  {!data?<p role="status">{error?'Access configuration could not be loaded.':'Loading access configuration…'} <button className="access-secondary" disabled={busy} onClick={()=>void reload()}>Retry loading</button></p>:<>
   <div className="access-summary"><span><strong>{data.users.length}</strong> tenant users</span><span><strong>{data.groups.filter(g=>g.status==='ACTIVE').length}</strong> active groups</span><span><strong>{data.tenantModuleCodes.length}</strong> enabled modules</span></div>
   <p className="access-hint">Tenant administrators manage users and groups. Operational actions require group permissions for everyone, including administrators, within enabled tenant modules.</p>
   <div className="access-tabs" role="tablist" aria-label="Access management">
    {(['users','groups','strategies'] as const).map(value=><button key={value} id={`access-${value}-tab`} role="tab" aria-selected={tab===value} aria-controls={`access-${value}-panel`} tabIndex={tab===value?0:-1} disabled={busy||!!editor} onKeyDown={tabKey} onClick={()=>selectTab(value)}>{value==='users'?'Users':value==='groups'?'Groups':'Strategy access'} <span>{value==='users'?data.users.length:value==='groups'?data.groups.length:data.strategies?.length??0}</span></button>)}
   </div>
   <section role="tabpanel" id={`access-${tab}-panel`} aria-labelledby={`access-${tab}-tab`} tabIndex={0} inert={stale||undefined}>
    {tab!=='strategies'?<div className="access-section-heading"><div><h2>{tab==='users'?'Tenant users':'Permission groups'}</h2><p className="muted">{tab==='users'?'Add people, manage their tenant role and assign them to permission groups.':'Define what members can do and which strategies those actions apply to. Assign groups to users in the Users tab.'}</p></div></div>:null}
    {tab==='strategies'?<StrategyAccessMatrix/>:<>
    <div className="access-toolbar"><label>Search {tab}<input type="search" value={query} placeholder={tab==='users'?'Name, role or group':'Name, code or description'} onChange={e=>setQuery(e.target.value)}/></label>
     <div className="access-actions"><button className="access-secondary" disabled={busy||!!editor} onClick={()=>{setNotice('');void reload();}}>Refresh</button><button className="access-primary" disabled={busy||!!editor} onClick={()=>setEditor(tab==='users'?'user':'group')}>{tab==='users'?'Add user':'Create group'}</button></div></div>
    {editor==='user'&&!editingUser?<form className="access-editor" onSubmit={createUser}><h2>Add user</h2><p className="muted">Creates a local account, not an email invitation or production login. Assign operational groups after creating any user, including an administrator.</p>
     <fieldset disabled={busy} className="access-fields"><legend className="access-sr-only">New user</legend><label>Display name<input autoFocus name="name" required maxLength={250}/></label><label>Tenant role<select name="role" defaultValue="MEMBER"><option value="MEMBER">Member — group permissions</option><option value="TENANT_ADMIN">Tenant administrator</option></select></label></fieldset>
     <div className="access-actions"><button className="access-primary" disabled={busy}>{busy?'Creating…':'Create user'}</button><button className="access-secondary" type="button" disabled={busy} onClick={close}>Cancel</button></div></form>:null}
    {editor==='user'&&currentUser?<UserAccessEditor key={`${currentUser.userId}:${currentUser.role}:${currentUser.status}:${currentUser.groupIds.join(',')}`} user={currentUser} groups={data.groups} busy={busy} cancel={close}
     save={ids=>save(`/api/access/users/${currentUser.userId}/groups`,{groupIds:ids})}
     change={(status,role)=>save(`/api/access/users/${currentUser.userId}`,{status,role})}/>:null}
    {editor==='group'?<GroupForm group={editingGroup} data={data} busy={busy} cancel={close} save={async body=>{if(await save(editingGroup?`/api/access/groups/${editingGroup.groupId}`:'/api/access/groups',body,editingGroup?'PUT':'POST'))close();}}/>:null}
    <div className="access-table-scroll"><table className="access-table"><caption className="access-sr-only">{tab==='users'?'Tenant users and membership':'Tenant groups and permission grants'}</caption>
     <thead><tr>{(tab==='users'?['User','Role & status','Groups','Effective actions','']:['Group','Status','Members','Granted actions','Strategy scope','']).map((heading,index)=><th key={index} scope="col">{heading||<span className="access-sr-only">Manage</span>}</th>)}</tr></thead>
     <tbody>{tab==='users'?users.map(user=><tr key={user.userId}><td><strong>{user.name}</strong>{user.userId===data.userId?<small>Current user</small>:null}</td><td>{accessLabel(user.role)}<small className={user.status==='ACTIVE'&&user.accountStatus==='ACTIVE'?'access-status':'access-status muted'}>{accessLabel(user.status)}{user.accountStatus!=='ACTIVE'?` · account ${accessLabel(user.accountStatus)}`:''}</small></td><td>{user.groupIds.map(id=>data.groups.find(g=>g.groupId===id)?.name??'Unknown group').join(', ')||'No groups'}</td><td>{user.permissions.length} actions<small><Link href={`/tenant-profile/effective-access?userId=${encodeURIComponent(user.userId)}`} aria-label={`Explain access for ${user.name}`}>Explain access</Link></small></td><td><button className="access-secondary" disabled={busy||!!editor} aria-label={`Manage ${user.name}`} onClick={()=>{setEditingUser(user);setEditor('user');}}>Manage</button></td></tr>)
      :groups.map(group=><tr key={group.groupId}><td><strong>{group.name}</strong><small>{group.code}{group.description?` · ${group.description}`:''}</small></td><td><span className={group.status==='ACTIVE'?'access-status':'muted'}>{accessLabel(group.status)}</span></td><td>{data.users.filter(u=>u.groupIds.includes(group.groupId)).length}</td><td>{group.actions.length} actions</td><td><span className={group.scopeMode==='SELECTED'&&!group.strategyIds?.length?'access-no-grant':'access-scope-label'}>{groupScopeSummary(group)}</span><small>For strategy-scoped actions only</small></td><td><button className="access-secondary" disabled={busy||!!editor} aria-label={`Edit ${group.name}`} onClick={()=>{setEditingGroup(group);setEditor('group');}}>Edit group</button></td></tr>)}</tbody></table></div>
    {(tab==='users'?users:groups).length===0?<p className="access-empty" role="status">{search?'No matches. Try another search.':`No ${tab} yet. Use the button above to add one.`}</p>:null}
    {editor?<p className="access-hint">Save or cancel this editor before opening another. Role, membership and group assignments are separate changes.</p>:null}
    </>}</section>
   {tab==='groups'&&data.tenantModuleCodes.includes('VALUATION')?<ValuationPublicationSettings tenantId={data.tenantId} userId={data.userId}/>:null}
  </>}
 </main>;
}

export function UserAccessEditor({user,groups,busy,save,change,cancel}:{user:AccessUser;groups:AccessGroup[];busy:boolean;save:(groups:string[])=>Promise<unknown>;change:(status:string,role:string)=>Promise<boolean>;cancel:()=>void}) {
 const [selected,setSelected] = useState(user.groupIds);
 const [role,setRole] = useState(user.role==='TENANT_ADMIN'?'TENANT_ADMIN':'MEMBER');
 const [confirmStatus,setConfirmStatus] = useState(false);
 const heading=useRef<HTMLHeadingElement>(null);
 useEffect(()=>{heading.current?.focus();},[]);
 return <section className="access-editor" aria-label={`Manage ${user.name}`}><h2 tabIndex={-1} ref={heading}>Manage {user.name}</h2>
  <p className="muted">Changes affect this tenant membership only. Account status: {accessLabel(user.accountStatus)}.</p>
  <div className="access-editor-columns"><div><label>Tenant role<select value={role} disabled={busy} onChange={e=>setRole(e.target.value)}><option value="MEMBER">Member</option><option value="TENANT_ADMIN">Tenant administrator</option></select></label>
   <p className="access-hint">The administrator role manages users and groups only. Operational actions require group permissions. Changing this selection does not save it; changing a role does not remove existing group assignments.</p><button className="access-secondary" disabled={busy||role===(user.role==='TENANT_ADMIN'?'TENANT_ADMIN':'MEMBER')} onClick={()=>void change(user.status,role)}>Save role</button>
   <details><summary>Effective permissions ({user.permissions.length})</summary><ul>{user.permissions.map(p=><li key={p}>{accessLabel(p)}</li>)}</ul>{!user.permissions.length?<p>No module actions are granted.</p>:null}</details>
  </div><div><fieldset disabled={busy}><legend>Group assignments</legend>{groups.length===0?<p>Create a group before assigning permissions.</p>:groups.map(group=><label className="access-check" key={group.groupId}><input type="checkbox" checked={selected.includes(group.groupId)} disabled={group.status!=='ACTIVE'&&!selected.includes(group.groupId)} onChange={e=>setSelected(old=>e.target.checked?[...old,group.groupId]:old.filter(id=>id!==group.groupId))}/>{group.name}{group.status!=='ACTIVE'?' (suspended — remove only)':''}</label>)}</fieldset><button className="access-primary" disabled={busy} onClick={()=>void save(selected)}>Save groups</button></div></div>
  <div className="access-editor-footer"><button className="access-secondary" disabled={busy} onClick={cancel}>Close without saving unsaved changes</button>
   {!confirmStatus?<button className="access-secondary" disabled={busy} onClick={()=>setConfirmStatus(true)}>{user.status==='ACTIVE'?'Suspend membership':'Reactivate membership'}</button>:<div className="access-actions"><span>{user.status==='ACTIVE'?'This user will lose access to this tenant.':'This membership will become active; account and group restrictions still apply.'}</span><button className="access-secondary" disabled={busy} onClick={async()=>{if(await change(user.status==='ACTIVE'?'SUSPENDED':'ACTIVE',user.role==='TENANT_ADMIN'?'TENANT_ADMIN':'MEMBER'))setConfirmStatus(false);}}>Confirm {user.status==='ACTIVE'?'suspension':'reactivation'}</button><button className="access-secondary" disabled={busy} onClick={()=>setConfirmStatus(false)}>Keep current status</button></div>}
  </div>
 </section>;
}

export function GroupForm({group,data,busy,cancel,save}:{group?:AccessGroup;data:TenantAccess;busy:boolean;cancel:()=>void;save:(body:unknown)=>Promise<void>}) {
 const [actions,setActions] = useState(group?.actions??[]);
 const [scopeMode,setScopeMode]=useState<'ALL'|'SELECTED'>(group?.scopeMode??'SELECTED');
 const [strategyIds,setStrategyIds]=useState(group?.strategyIds??[]);
 const [strategyQuery,setStrategyQuery]=useState('');
 type Preview={changes:Array<{name:string;strategyName:string;added:string[];removed:string[]}>;globalChanges?:Array<{name:string;added:string[];removed:string[]}>;impactHash:string;includesFutureStrategies:boolean;unassignedNewGroup:boolean};
 type GroupDraft={code:FormDataEntryValue|null;name:FormDataEntryValue|null;description:FormDataEntryValue|null;status:FormDataEntryValue|null;actions:string[];scopeMode:'ALL'|'SELECTED';strategyIds:string[];expectedVersion?:number;expectedImpactHash?:string};
 const [preview,setPreview]=useState<{body:GroupDraft;result:Preview}>();
 const [previewError,setPreviewError]=useState('');
 const [previewBusy,setPreviewBusy]=useState(false);
 const previewSequence=useRef(0);
 const editorHeading=useRef<HTMLHeadingElement>(null);
 const reviewHeading=useRef<HTMLHeadingElement>(null);
 const reviewing=!!preview;
 useEffect(()=>{(reviewing?reviewHeading:editorHeading).current?.focus();},[reviewing]);
 const sections = [...new Set(data.actions.map(action=>action.moduleCodes.join('|')))];
 const visibleStrategies=(data.strategies??[]).filter(strategy=>strategy.name.toLowerCase().includes(strategyQuery.trim().toLowerCase()));
 const changeCount=preview?preview.result.changes.length+(preview.result.globalChanges?.length??0):0;
 async function submit(e:FormEvent<HTMLFormElement>) {
  e.preventDefault();
  const values = new FormData(e.currentTarget);
  const body={code:values.get('code'),name:values.get('name'),description:values.get('description')||null,status:values.get('status'),actions,scopeMode,strategyIds:scopeMode==='ALL'?[]:strategyIds,expectedVersion:group?.versionNo};
  const sequence=++previewSequence.current;
  setPreviewError('');setPreviewBusy(true);setPreview(undefined);
  try {
   const result=await accessRequest<Preview>('/api/access/groups/preview',{method:'POST',headers:{'X-Expected-Tenant-Id':data.tenantId,'X-Expected-User-Id':data.userId},body:JSON.stringify({...body,groupId:group?.groupId})});
   if(sequence===previewSequence.current)setPreview({body:{...body,expectedImpactHash:result.impactHash},result});
  } catch(error) {if(sequence===previewSequence.current)setPreviewError(error instanceof Error?error.message:'Preview unavailable.');}
  finally {if(sequence===previewSequence.current)setPreviewBusy(false);}
 }
 return <form className="access-editor access-group-editor" onSubmit={submit} onChange={()=>{previewSequence.current++;setPreview(undefined);setPreviewBusy(false);}}><h2 tabIndex={-1} ref={editorHeading}>{group?`Edit ${group.name}`:'Create group'}</h2>
  <p className="muted">Set up the group, choose its permissions and strategy scope, then review the effect before saving.</p>
  <div hidden={!!preview}>
  <h3 className="access-step-heading"><span>1</span> Group details</h3>
  <fieldset disabled={busy} className="access-fields"><legend className="access-sr-only">Group details</legend><label>Name<input autoFocus name="name" required maxLength={250} defaultValue={group?.name}/></label><label>Code<input name="code" required maxLength={100} pattern="[A-Za-z0-9_-]+" defaultValue={group?.code}/><small>Stable identifier: letters, numbers, hyphens or underscores.</small></label><label>Description<input name="description" maxLength={2000} defaultValue={group?.description??''}/></label><label>Status<select name="status" defaultValue={group?.status??'ACTIVE'}><option value="ACTIVE">Active</option><option value="SUSPENDED">Suspended</option></select><small>Suspending a group disables all its grants.</small></label></fieldset>
  <h3 className="access-step-heading"><span>2</span> What can members do? <small className="access-count">{actions.length} selected</small></h3><p className="access-hint">Only enabled tenant modules can receive new grants. Existing grants for disabled modules can be removed; they do not provide access.</p>
  <div className="access-permission-grid">{sections.map(section=>{
   const enabled=section.split('|').some(module=>data.tenantModuleCodes.includes(module));
   return <fieldset key={section} disabled={busy}><legend>{section.split('|').map(accessLabel).join(' / ')||'Administration'}{!enabled?' — module disabled':''}</legend>
    {data.actions.filter(a=>a.moduleCodes.join('|')===section).map(action=><label className="access-check access-permission-check" key={action.code}><input type="checkbox" checked={actions.includes(action.code)} disabled={!enabled&&!actions.includes(action.code)} onChange={e=>setActions(old=>e.target.checked?[...old,action.code]:old.filter(a=>a!==action.code))}/><span><strong>{actionTitle(action.code)}</strong><small>{actionDescription(action.code)}</small></span></label>)}</fieldset>;
  })}</div>
  <h3 className="access-step-heading"><span>3</span> Which strategies?</h3>
  <p className="access-hint">This scope limits strategy, trade, valuation and strategy-calendar actions. Instrument management, trade-field setup and strategy creation remain tenant-wide. Market-data evidence has its own context checks.</p>
  <fieldset disabled={busy||previewBusy}><legend>Strategy scope for operational actions</legend><label>Scope<select value={scopeMode} onChange={e=>setScopeMode(e.target.value as 'ALL'|'SELECTED')}><option value="SELECTED">Selected strategies only</option><option value="ALL">All tenant strategies, including future ones</option></select></label>
   {scopeMode==='ALL'?<p className="access-warning">These actions apply to all current and future tenant strategies. Unrelated groups cannot widen this group’s grants.</p>:<>
    <p className={strategyIds.length?'access-hint':'access-warning'}>An empty selection grants no strategy access. Tenant-wide configuration and creation permissions remain separate.</p>
    <label>Find a strategy<input type="search" value={strategyQuery} placeholder="Strategy name" onChange={e=>setStrategyQuery(e.target.value)}/></label>
    <p className="access-hint">{strategyIds.length} selected · showing {visibleStrategies.length} of {data.strategies?.length??0}. Searching does not remove selections.</p>
    <div className="access-strategy-options">{visibleStrategies.map(strategy=><label className="access-check" key={strategy.strategyId}><input type="checkbox" checked={strategyIds.includes(strategy.strategyId)} onChange={e=>setStrategyIds(old=>e.target.checked?[...old,strategy.strategyId]:old.filter(id=>id!==strategy.strategyId))}/>{strategy.name}{strategy.status!=='ACTIVE'?` (${accessLabel(strategy.status)} — history only)`:''}</label>)}</div>
    {!visibleStrategies.length?<p role="status">{data.strategies?.length?'No strategies match your search.':'No strategies yet. You can save this scope empty and assign strategies later.'}</p>:null}
   </>}
  </fieldset>
  </div>
  {previewError?<p role="alert">{previewError}</p>:null}
  {preview?<section className="access-review" aria-label="Access change preview" role="region" aria-live="polite"><h3 tabIndex={-1} ref={reviewHeading} className="access-step-heading"><span>4</span> Review access changes</h3>
   <dl className="access-review-summary">
    <div><dt>Group</dt><dd>{String(preview.body.name)} <small>({String(preview.body.code)})</small></dd></div>
    <div><dt>Status</dt><dd>{accessLabel(String(preview.body.status))}</dd></div>
    <div><dt>Permissions</dt><dd>{preview.body.actions.map(actionTitle).join(', ')||'None — no operational actions'}</dd></div>
    <div><dt>Strategy scope</dt><dd>{preview.body.scopeMode==='ALL'?'All current and future strategies':preview.body.strategyIds.length?preview.body.strategyIds.map(id=>data.strategies?.find(s=>s.strategyId===id)?.name??id).join(', '):'No strategies selected'}</dd></div>
   </dl>
   <p><strong>{changeCount}</strong> access changes below. One user may have changes on several strategies.</p>
   {preview.result.unassignedNewGroup?<p className="access-warning">New group: nobody gains access until assigned to it.</p>:null}
   {preview.result.globalChanges?.length?<section><h4>Tenant-wide changes</h4><ul className="access-impact-list">{preview.result.globalChanges.map((change,i)=><li key={i}><strong>{change.name}</strong><p>Gains: {change.added.map(actionTitle).join(', ')||'none'}<br/>Loses: {change.removed.map(actionTitle).join(', ')||'none'}</p></li>)}</ul></section>:null}
   {preview.result.changes.length?<section><h4>Strategy-access changes</h4><ul className="access-impact-list">{preview.result.changes.map((change,i)=><li key={i}><strong>{change.name}</strong> · {change.strategyName}<p>Gains: {change.added.map(actionTitle).join(', ')||'none'}<br/>Loses: {change.removed.map(actionTitle).join(', ')||'none'}</p></li>)}</ul></section>:<p>No current strategy-access changes.</p>}
   {preview.result.includesFutureStrategies?<p className="access-warning">Also includes future tenant strategies.</p>:null}
   <p className="access-hint">Preview reflects current assignments. The saved revision is checked; editing the form requires another preview.</p>
   <div className="access-actions"><button type="button" className="access-primary" disabled={busy} onClick={()=>void save(preview.body)}>{busy?'Saving…':'Confirm and save group'}</button><button type="button" className="access-secondary" disabled={busy} onClick={()=>{previewSequence.current++;setPreview(undefined);}}>Edit configuration</button></div>
  </section>:null}
  <div className="access-editor-footer">{!preview?<button className="access-primary" disabled={busy||previewBusy}>{previewBusy?'Checking impact…':'Preview access changes'}</button>:<span className="access-hint">Nothing is saved until you confirm.</span>}<button className="access-secondary" type="button" disabled={busy} onClick={cancel}>Cancel</button></div>
 </form>;
}
