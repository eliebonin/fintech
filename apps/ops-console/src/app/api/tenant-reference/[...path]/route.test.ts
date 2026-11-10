import {NextRequest} from 'next/server';
import {it,expect,vi,afterEach} from 'vitest';
vi.mock('server-only',()=>({}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:async()=>({tenantId:'tenant',userAccountId:'actor',source:'local-session'})}));
import {GET} from './route';
afterEach(()=>vi.unstubAllGlobals());
const ctx=(path:string)=>({params:Promise.resolve({path:path.split('/')})});
it('forwards only allowlisted scoped reference reads and preserves pages',async()=>{
 const fetch=vi.fn(async(_input:RequestInfo|URL)=>new Response(JSON.stringify({items:[],total:0,offset:25,limit:25})));vi.stubGlobal('fetch',fetch);
 const result=await GET(new NextRequest('http://test/api/tenant-reference/sources?q=Mandate&offset=25',{headers:{'X-Expected-Tenant-Id':'tenant'}}),ctx('sources'));
 expect(result.status).toBe(200);expect(String(fetch.mock.calls[0]?.[0])).toContain('/v1/tenant-reference/sources?q=Mandate&offset=25');
 expect(result.headers.get('Cache-Control')).toBe('private, no-store');
 expect((await GET(new NextRequest('http://test/api/tenant-reference/secm/users'),ctx('secm/users'))).status).toBe(404);
 expect(fetch).toHaveBeenCalledTimes(1);
});
it('rejects a changed tenant before accessing the source',async()=>{
 const fetch=vi.fn();vi.stubGlobal('fetch',fetch);
 expect((await GET(new NextRequest('http://test/api/tenant-reference/sources',{headers:{'X-Expected-Tenant-Id':'old'}}),ctx('sources'))).status).toBe(409);expect(fetch).not.toHaveBeenCalled();
});
