import {afterEach,beforeEach,expect,it,vi} from 'vitest';
vi.mock('server-only',()=>({}));
const h=vi.hoisted(()=>({cookie:undefined as string|undefined}));
vi.mock('next/headers',()=>({cookies:async()=>({get:(name:string)=>name==='local_access_session'&&h.cookie?{value:h.cookie}:undefined})}));
import {getActiveTenantContext,getActiveTenantWorkspace} from '../tenant-session';

beforeEach(()=>vi.stubEnv('APP_ENV','test'));
afterEach(()=>{h.cookie=undefined;vi.unstubAllGlobals();vi.unstubAllEnvs();});
it('reports an absent session as session-required without a request',async()=>{const fetcher=vi.fn();vi.stubGlobal('fetch',fetcher);await expect(getActiveTenantContext()).rejects.toMatchObject({code:'ACTIVE_TENANT_REQUIRED'});expect(fetcher).not.toHaveBeenCalled();});
it('preserves workspace forbidden status',async()=>{h.cookie='opaque';vi.stubGlobal('fetch',async()=>Response.json({}, {status:403}));await expect(getActiveTenantWorkspace()).rejects.toMatchObject({status:403});});
it('rejects a workspace that no longer matches the selected user',async()=>{h.cookie='opaque';vi.stubGlobal('fetch',async()=>Response.json({tenantId:'tenant',userId:'new-user'}));await expect(getActiveTenantWorkspace({tenantId:'tenant',userAccountId:'old-user',source:'local-session'})).rejects.toMatchObject({status:403});});
