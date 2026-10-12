import React from 'react';
import {afterEach,it,expect,vi} from 'vitest';
const h=vi.hoisted(()=>({slots:[] as unknown[],cursor:0}));
// No DOM runtime is installed; keep the component and its handlers real, with a small state driver.
vi.mock('react',async original=>({...await original<typeof import('react')>(),useState:(initial:unknown)=>{
 const index=h.cursor++;if(!(index in h.slots))h.slots[index]=initial;
 return [h.slots[index],(value:unknown)=>h.slots[index]=typeof value==='function'?value(h.slots[index]):value];
},useRef:(value:unknown)=>({current:value}),useCallback:(callback:unknown)=>callback,useEffect:()=>{}}));
import {UserAccessEditor,TenantAccessConsole,GroupForm} from './tenant-access-console';
import {ContextSelector} from './context-selector';
import {PlatformTenants,TenantProfileEditor} from './platform-tenants';
const user={userId:'u',name:'Alice',role:'MEMBER',status:'ACTIVE',accountStatus:'ACTIVE',groupIds:['g'],permissions:['TRADE_READ']};
function find(node:any,predicate:(node:any)=>boolean):any {
 if(!node||typeof node!=='object')return;
 if(predicate(node))return node;
 for(const child of [node.props?.children].flat(Infinity)){const found=find(child,predicate);if(found)return found;}
}
afterEach(()=>{h.slots=[];h.cursor=0;vi.unstubAllGlobals();});
const access={tenantId:'tenant',userId:'admin',users:[user],groups:[],tenantModuleCodes:['TRADING'],actions:[]};
const platformTenant={tenantId:'tenant',code:'ALPHA',name:'Alpha',status:'ACTIVE',profileVersion:2,contactName:'Ops',contactEmail:'ops@example.org',moduleCodes:['TRADING'],users:[]};
it('opens a suspension confirmation without sending a write and cancels without changes',()=>{
 const send=vi.fn();vi.stubGlobal('fetch',send);
 const render=()=>{h.cursor=0;return PlatformTenants({initial:{tenants:[platformTenant],modules:[]}});};
 find(render(),n=>n.type==='button'&&n.props.children==='Suspend tenant').props.onClick();
 const editor=find(render(),n=>n.type===TenantProfileEditor);
 expect(editor.props.mode).toBe('status');expect(send).not.toHaveBeenCalled();
 editor.props.cancel();
 expect(find(render(),n=>n.type===TenantProfileEditor)).toBeUndefined();expect(send).not.toHaveBeenCalled();
});
it('retains the tenant editor and explains a stale-version rejection',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValueOnce(Response.json({detail:'Tenant details changed. Refresh and reopen.'},{status:409})));
 const render=()=>{h.cursor=0;return PlatformTenants({initial:{tenants:[platformTenant],modules:[]}});};
 find(render(),n=>n.type==='button'&&n.props.children==='Edit tenant').props.onClick();
 await find(render(),n=>n.type===TenantProfileEditor).props.save({name:'Changed',expectedVersion:2,status:'ACTIVE'});
 expect(find(render(),n=>n.type===TenantProfileEditor)).toBeDefined();
 expect(find(render(),n=>n.props?.role==='alert').props.children[0]).toContain('Tenant details changed');
});
it('closes a successfully saved tenant editor and displays the refreshed tenant name',async()=>{
 const updated={tenants:[{...platformTenant,name:'Updated',profileVersion:3}],modules:[]};
 const send=vi.fn().mockResolvedValueOnce(Response.json({updated:true,profileVersion:3})).mockResolvedValueOnce(Response.json(updated));
 vi.stubGlobal('fetch',send);
 const render=()=>{h.cursor=0;return PlatformTenants({initial:{tenants:[platformTenant],modules:[]}});};
 find(render(),n=>n.type==='button'&&n.props.children==='Edit tenant').props.onClick();
 await find(render(),n=>n.type===TenantProfileEditor).props.save({name:'Updated',expectedVersion:2,status:'ACTIVE'});
 expect(find(render(),n=>n.type===TenantProfileEditor)).toBeUndefined();
 expect(find(render(),n=>n.type==='h2'&&n.props.children==='Updated')).toBeDefined();
 expect(send.mock.calls[0][0]).toBe('/api/platform/tenants/tenant');
 expect(send.mock.calls[0][1].method).toBe('PUT');
});
it('filters users case-insensitively and announces an empty search',()=>{
 const render=()=>{h.cursor=0;return TenantAccessConsole({initial:access});};
 find(render(),n=>n.type==='input'&&n.props.type==='search').props.onChange({target:{value:'ALICE'}});
 expect(find(render(),n=>n.type==='strong'&&n.props.children==='Alice')).toBeDefined();
 find(render(),n=>n.type==='input'&&n.props.type==='search').props.onChange({target:{value:'missing'}});
 expect(find(render(),n=>n.type==='strong'&&n.props.children==='Alice')).toBeUndefined();
 expect(find(render(),n=>n.props?.role==='status'&&n.props.children==='No matches. Try another search.')).toBeDefined();
});
it('moves the selected tab and keyboard focus together',()=>{
 const focus=vi.fn(),replaceState=vi.fn();
 vi.stubGlobal('document',{getElementById:(id:string)=>id==='access-groups-tab'?{focus}:null});
 vi.stubGlobal('window',{history:{replaceState}});
 const render=()=>{h.cursor=0;return TenantAccessConsole({initial:access});};
 find(render(),n=>n.props?.id==='access-users-tab').props.onKeyDown({key:'ArrowRight',preventDefault(){}});
 expect(find(render(),n=>n.props?.id==='access-groups-tab').props['aria-selected']).toBe(true);
 expect(focus).toHaveBeenCalledOnce();
 expect(replaceState).toHaveBeenCalledWith(null,'','?view=groups');
});
it('clears the selected user when changing tenants and prevents entering with the old identity',()=>{
 const registry={tenants:[{tenantId:'a',code:'A',name:'Alpha',status:'ACTIVE',moduleCodes:['TRADING'],users:[{userId:'u',name:'Alice',role:'MEMBER'}]},{tenantId:'b',code:'B',name:'Beta',status:'ACTIVE',moduleCodes:[],users:[]}],modules:[]};
 const render=()=>{h.cursor=0;return ContextSelector({initial:registry});};
 const tenantSelect=(tree:any)=>find(tree,n=>n.type==='select'&&!n.props.disabled&&n.props.children?.[1]?.length===2);
 tenantSelect(render()).props.onChange({target:{value:'a'}});
 const userSelect=find(render(),n=>n.type==='select'&&n.props.children?.[1]?.length===1);
 userSelect.props.onChange({target:{value:'u'}});
 expect(find(render(),n=>n.type==='button'&&n.props.children==='Enter tenant workspace').props.disabled).toBe(false);
 tenantSelect(render()).props.onChange({target:{value:'b'}});
 expect(find(render(),n=>n.type==='button'&&n.props.children==='Enter tenant workspace').props.disabled).toBe(true);
 expect(find(render(),n=>n.type==='select'&&n.props.children?.[1]?.length===0).props.value).toBe('');
});
it('keeps other user edits available after saving a role through the console',async()=>{
 const updated={...access,users:[{...user,role:'TENANT_ADMIN'}]};
 vi.stubGlobal('fetch',vi.fn().mockResolvedValueOnce(Response.json({})).mockResolvedValueOnce(Response.json(updated)));
 const render=()=>{h.cursor=0;return TenantAccessConsole({initial:access});};
 find(render(),n=>n.type==='button'&&n.props['aria-label']==='Manage Alice').props.onClick();
 await find(render(),n=>n.type===UserAccessEditor).props.change('ACTIVE','TENANT_ADMIN');
 const editor=find(render(),n=>n.type===UserAccessEditor);
 expect(editor).toBeDefined();
 expect(editor.props.user.role).toBe('TENANT_ADMIN');
});
it('closes and clears a newly created group editor only after a successful save',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValueOnce(Response.json({})).mockResolvedValueOnce(Response.json(access)));
 const render=()=>{h.cursor=0;return TenantAccessConsole({initial:access,initialTab:'groups'});};
 find(render(),n=>n.type==='button'&&n.props.children==='Create group').props.onClick();
 await find(render(),n=>n.type===GroupForm).props.save({name:'Traders',code:'TRADERS',status:'ACTIVE',actions:[]});
 expect(find(render(),n=>n.type===GroupForm)).toBeUndefined();
});
it('retains the group editor and reports a failed save',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValueOnce(Response.json({error:{message:'Group code exists'}},{status:409})));
 const render=()=>{h.cursor=0;return TenantAccessConsole({initial:access,initialTab:'groups'});};
 find(render(),n=>n.type==='button'&&n.props.children==='Create group').props.onClick();
 await find(render(),n=>n.type===GroupForm).props.save({name:'Traders',code:'TRADERS',status:'ACTIVE',actions:[]});
 expect(find(render(),n=>n.type===GroupForm)).toBeDefined();
 expect(find(render(),n=>n.props?.role==='alert').props.children).toBe('Group code exists');
});
it('stages a role selection until explicit save and retains the editor after saving',async()=>{
 const change=vi.fn().mockResolvedValue(true),cancel=vi.fn();
 const render=()=>{h.cursor=0;return UserAccessEditor({user,groups:[],busy:false,save:async()=>true,change,cancel});};
 find(render(),n=>n.type==='select').props.onChange({target:{value:'TENANT_ADMIN'}});
 expect(change).not.toHaveBeenCalled();
 await find(render(),n=>n.type==='button'&&n.props.children==='Save role').props.onClick();
 expect(change).toHaveBeenCalledWith('ACTIVE','TENANT_ADMIN');
 expect(cancel).not.toHaveBeenCalled();
});
it('requires confirmation before changing membership status',async()=>{
 const change=vi.fn().mockResolvedValue(true);
 const render=()=>{h.cursor=0;return UserAccessEditor({user,groups:[],busy:false,save:async()=>true,change,cancel:()=>{}});};
 find(render(),n=>n.type==='button'&&n.props.children==='Suspend membership').props.onClick();
 expect(change).not.toHaveBeenCalled();
 await find(render(),n=>n.type==='button'&&Array.isArray(n.props.children)&&n.props.children[0]==='Confirm ').props.onClick();
 expect(change).toHaveBeenCalledWith('SUSPENDED','MEMBER');
});
it('blocks assignment to a suspended group that was not already assigned',()=>{
 h.cursor=0;
 const tree=UserAccessEditor({user,groups:[{groupId:'old',code:'OLD',name:'Old',description:null,status:'SUSPENDED',actions:[]}],busy:false,save:async()=>true,change:async()=>true,cancel:()=>{}});
 expect(find(tree,n=>n.type==='input'&&n.props.type==='checkbox').props.disabled).toBe(true);
});
