import {afterEach,expect,it,vi} from 'vitest';
vi.mock('server-only',()=>({}));
const h=vi.hoisted(()=>({cookie:undefined as string|undefined}));
vi.mock('next/headers',()=>({cookies:async()=>({get:(name:string)=>name==='active_tenant'&&h.cookie?{value:h.cookie}:undefined})}));
import {getActiveTenantContext,getActiveTenantWorkspace,selectActiveTenant,signActiveTenantId} from '../tenant-session';
afterEach(()=>{h.cookie=undefined;vi.unstubAllGlobals();vi.unstubAllEnvs();});
it('reports absent and tampered cookies as session-required',async()=>{await expect(getActiveTenantContext()).rejects.toMatchObject({code:'ACTIVE_TENANT_REQUIRED'});h.cookie='tenant.invalid';await expect(getActiveTenantContext()).rejects.toMatchObject({code:'ACTIVE_TENANT_REQUIRED'});});
it('preserves workspace forbidden status',async()=>{h.cookie=signActiveTenantId('tenant');vi.stubGlobal('fetch',async()=>Response.json({}, {status:403}));await expect(getActiveTenantWorkspace()).rejects.toMatchObject({status:403});});
it('retains the production cookie-secret requirement',async()=>{vi.stubEnv('NODE_ENV','production');vi.stubEnv('ACTIVE_TENANT_COOKIE_SECRET','');expect(()=>signActiveTenantId('tenant')).toThrow('ACTIVE_TENANT_COOKIE_SECRET');});

it('reports selection outside active memberships as forbidden',async()=>{vi.stubGlobal('fetch',async()=>Response.json({data:[]}));await expect(selectActiveTenant('unavailable-tenant')).rejects.toMatchObject({status:403});});
