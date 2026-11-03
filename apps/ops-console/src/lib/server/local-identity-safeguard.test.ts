import {createHmac} from 'node:crypto';
import {afterEach, beforeEach, expect, it, vi} from 'vitest';
vi.mock('server-only',()=>({}));
const h=vi.hoisted(()=>({cookies:{} as Record<string,string>}));
vi.mock('next/headers',()=>({cookies:async()=>({get:(name:string)=>h.cookies[name]?{value:h.cookies[name]}:undefined})}));
import {getActiveTenantContext} from '../tenant-session';
import {accessProxy} from './access-proxy';

const key='synthetic-local-bootstrap-key-for-tests-only';
beforeEach(()=>{vi.stubEnv('APP_ENV','local');vi.stubEnv('LOCAL_ACCESS_OPERATOR_KEY',key);});
afterEach(()=>{h.cookies={};vi.unstubAllGlobals();vi.unstubAllEnvs();});

it('never authenticates a signed legacy tenant cookie as the demo user',async()=>{
 const signature=createHmac('sha256','development-only-active-tenant-secret').update('tenant').digest('base64url');
 h.cookies.active_tenant=`tenant.${signature}`;
 await expect(getActiveTenantContext()).rejects.toMatchObject({status:401});
});

it('does not resolve a local session in a non-local environment',async()=>{
 vi.stubEnv('APP_ENV','production');h.cookies.local_access_session='opaque';
 const fetcher=vi.fn();vi.stubGlobal('fetch',fetcher);
 await expect(getActiveTenantContext()).rejects.toThrow();expect(fetcher).not.toHaveBeenCalled();
});

it('requires a configured server-only key before bootstrapping',async()=>{
 vi.stubEnv('LOCAL_ACCESS_OPERATOR_KEY','');const fetcher=vi.fn();vi.stubGlobal('fetch',fetcher);
 await expect(accessProxy('/v1/local-session/options',{},'operator')).rejects.toThrow('LOCAL_ACCESS_OPERATOR_KEY');
 expect(fetcher).not.toHaveBeenCalled();
});

it('permits an optimised local build and forwards the key only on guarded bootstrap',async()=>{
 vi.stubEnv('NODE_ENV','production');
 const fetcher=vi.fn(async()=>Response.json({tenants:[]}));vi.stubGlobal('fetch',fetcher);
 await accessProxy('/v1/local-session/options',{},'operator');
 const [url,init]=fetcher.mock.calls[0] as unknown as [URL,RequestInit];
 expect(String(url)).toBe('http://localhost:8000/v1/local-session/options');
 expect(new Headers(init.headers).get('X-Local-Operator-Key')).toBe(key);
 expect(init.redirect).toBe('error');
});

it('never forwards the bootstrap key to an arbitrary endpoint or another origin',async()=>{
 const fetcher=vi.fn();vi.stubGlobal('fetch',fetcher);
 await expect(accessProxy('https://example.org/v1/local-session/options',{},'operator')).rejects.toThrow();
 await expect(accessProxy('/v1/strategies',{},'operator')).rejects.toThrow();
 expect(fetcher).not.toHaveBeenCalled();
});
