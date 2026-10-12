import {afterEach,expect,it,vi} from 'vitest';
vi.mock('server-only',()=>({}));
const h=vi.hoisted(()=>({token:undefined as string|undefined}));
vi.mock('next/headers',()=>({cookies:async()=>({get:(name:string)=>name==='local_access_session'&&h.token?{value:h.token}:undefined})}));
import {getActiveTenantContext} from '../tenant-session';
import {forwardLocalSession} from './local-session-forward';
afterEach(()=>{h.token=undefined;vi.unstubAllGlobals();});

it('uses the backend-selected user, not the fixed demo account',async()=>{
 h.token='opaque-token';
 vi.stubGlobal('fetch',async()=>Response.json({tenantId:'tenant-b',userId:'trader-b'}));
 expect(await getActiveTenantContext()).toEqual({tenantId:'tenant-b',userAccountId:'trader-b',source:'local-session'});
});
it('never falls back to the demo actor when a selected session is rejected',async()=>{
 h.token='expired';vi.stubGlobal('fetch',async()=>Response.json({}, {status:403}));
 await expect(getActiveTenantContext()).rejects.toMatchObject({status:403});
});
it('forwards the opaque credential only to the private API origin',async()=>{
 h.token='opaque-token';
 const upstream=await forwardLocalSession('http://localhost:8000/v1/trades',{headers:{'X-Tenant-Id':'tenant-b'}});
 expect(new Headers(upstream?.headers).get('X-Local-Access-Token')).toBe('opaque-token');
 expect(new Headers(upstream?.headers).get('X-Tenant-Id')).toBe('tenant-b');
 expect(await forwardLocalSession('https://example.org/',{headers:{Accept:'application/json'}})).toEqual({headers:{Accept:'application/json'}});
});
it('leaves browser-relative requests alone',async()=>{
 expect(await forwardLocalSession('/api/trades',{method:'POST'})).toEqual({method:'POST'});
});
