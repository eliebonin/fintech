import {NextRequest} from 'next/server';
import {it,expect,vi,afterEach} from 'vitest';
vi.mock('server-only',()=>({}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:async()=>({tenantId:'tenant',userAccountId:'actor',source:'local-session'})}));
vi.mock('@/lib/reference-fetch',()=>({referenceFetch:()=>fetch}));
import {GET,POST} from './route';
afterEach(()=>vi.unstubAllGlobals());
const ctx=(path:string)=>({params:Promise.resolve({path:path.split('/')})});
it('forwards scoped reads using verified context and preserves paging',async()=>{
 const upstream=vi.fn(async(_input:RequestInfo|URL,_init?:RequestInit)=>new Response(JSON.stringify({items:[],total:0,offset:25,limit:25})));vi.stubGlobal('fetch',upstream);
 const response=await GET(new NextRequest('http://test/api/trade-profiles/register?offset=25',{headers:{'X-Expected-Tenant-Id':'tenant','X-Tenant-Id':'forged'}}),ctx('register'));
 expect(response.status).toBe(200);expect(response.headers.get('Cache-Control')).toBe('private, no-store');
 expect(String(upstream.mock.calls[0]?.[0])).toContain('/v1/trade-profiles?offset=25');
 expect(new Headers(upstream.mock.calls[0]?.[1]?.headers).get('X-Tenant-Id')).toBe('tenant');
 expect((await GET(new NextRequest('http://test/api/trade-profiles/secm/trades'),ctx('secm/trades'))).status).toBe(404);
});
it('rejects changed context before mutation and preserves conflict messages',async()=>{
 const upstream=vi.fn(async()=>new Response(JSON.stringify({detail:'Assignment changed. Review again.',code:'profile.changed'}),{status:409,headers:{'X-Request-Id':'review-request'}}));vi.stubGlobal('fetch',upstream);
 expect((await POST(new NextRequest('http://test/api/trade-profiles/default',{method:'POST',headers:{'X-Expected-Tenant-Id':'old'},body:'{}'}),ctx('default'))).status).toBe(409);
 expect(upstream).not.toHaveBeenCalled();
 const result=await POST(new NextRequest('http://test/api/trade-profiles/default',{method:'POST',headers:{'X-Expected-Tenant-Id':'tenant'},body:'{}'}),ctx('default'));
 expect(result.status).toBe(409);expect(result.headers.get('X-Request-Id')).toBe('review-request');expect((await result.json()).error.message).toContain('Review again');
});
