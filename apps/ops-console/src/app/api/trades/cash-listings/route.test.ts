import {NextRequest} from 'next/server';
import {afterEach,expect,it,vi} from 'vitest';
vi.mock('server-only',()=>({}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:async()=>({tenantId:'tenant',userAccountId:'actor'})}));
import {GET} from './route';
import {GET as detail} from './[listingId]/route';
afterEach(()=>vi.unstubAllGlobals());
it('reads with trusted tenant identity and forwards date and raw offset without caching',async()=>{
  let received:URL|undefined,headers:Headers|undefined,cache:RequestCache|undefined;
  vi.stubGlobal('fetch',async(url:URL,init:RequestInit)=>{received=url;headers=new Headers(init.headers);cache=init.cache;return Response.json({data:[],meta:{total:30}});});
  const result=await GET(new NextRequest('http://test/api/trades/cash-listings?q=HSBC&asOfDate=2026-09-30&offset=25',{headers:{'X-Tenant-Id':'forged'}}));
  expect(result.status).toBe(200);expect(headers?.get('X-Tenant-Id')).toBe('tenant');
  expect(received?.pathname).toBe('/v1/trades/cash-listings');expect(received?.searchParams.get('offset')).toBe('25');
  expect(received?.searchParams.get('asOfDate')).toBe('2026-09-30');expect(cache).toBe('no-store');
});
it('refreshes selected readiness and preserves opaque upstream refusal',async()=>{
  vi.stubGlobal('fetch',async(url:URL)=>{expect(url.pathname).toBe('/v1/trades/cash-listings/listing');expect(url.searchParams.get('asOfDate')).toBe('2026-10-01');return Response.json({detail:'Not found'},{status:404});});
  const response=await detail(new NextRequest('http://test/api/trades/cash-listings/listing?asOfDate=2026-10-01'),{params:Promise.resolve({listingId:'listing'})});
  expect(response.status).toBe(404);
});
it('does not turn an unavailable readiness service into a ready result',async()=>{
  vi.stubGlobal('fetch',async()=>new Response('Offline',{status:503}));
  const response=await GET(new NextRequest('http://test/api/trades/cash-listings?q=HSBC'));
  expect(response.status).toBe(503);expect((await response.json()).data).toBeUndefined();
});
