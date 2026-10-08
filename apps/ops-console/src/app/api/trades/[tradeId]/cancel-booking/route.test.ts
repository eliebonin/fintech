import {NextRequest} from 'next/server';
import {afterEach,expect,it,vi} from 'vitest';
vi.mock('server-only',()=>({}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:async()=>({tenantId:'tenant',userAccountId:'actor'})}));
import {POST} from './route';
const context={params:Promise.resolve({tradeId:'00000000-0000-7000-8000-000000000001'})};
function request(headers:Record<string,string>={}){return new NextRequest('http://test/api/trades/id/cancel-booking',{method:'POST',headers,body:JSON.stringify({expectedSequenceNo:1,reason:'Wrong quantity'})});}
afterEach(()=>vi.unstubAllGlobals());
it('requires key and expected tenant before forwarding cancellation',async()=>{
 expect((await POST(request(),context)).status).toBe(400);
 expect((await POST(request({'Idempotency-Key':'key'}),context)).status).toBe(400);
 const fetch=vi.fn();vi.stubGlobal('fetch',fetch);
 expect((await POST(request({'Idempotency-Key':'key','X-Expected-Tenant-Id':'other'}),context)).status).toBe(409);expect(fetch).not.toHaveBeenCalled();
});
it('forwards server identity, scoped trade ID and unchanged reason/key',async()=>{
 let sent:any;
 vi.stubGlobal('fetch',async(url:URL,options:RequestInit)=>{sent={path:url.pathname,headers:new Headers(options.headers),body:JSON.parse(options.body as string),cache:options.cache};return Response.json({data:{trade:{tradeId:'saved'}},meta:{}});});
 expect((await POST(request({'Idempotency-Key':'same-key','X-Expected-Tenant-Id':'tenant','X-Tenant-Id':'forged'}),context)).status).toBe(200);
 expect(sent.path).toBe('/v1/trades/00000000-0000-7000-8000-000000000001/cancel-booking');expect(sent.headers.get('X-Tenant-Id')).toBe('tenant');expect(sent.headers.get('Idempotency-Key')).toBe('same-key');expect(sent.body).toEqual({expectedSequenceNo:1,reason:'Wrong quantity'});expect(sent.cache).toBe('no-store');
});
