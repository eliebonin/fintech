import {beforeEach,expect,it,vi} from 'vitest';
import {NextRequest} from 'next/server';
vi.mock('server-only',()=>({}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:async()=>({tenantId:'trusted-tenant',userAccountId:'trusted-user'})}));
const upstream=vi.hoisted(()=>vi.fn());
beforeEach(()=>{upstream.mockReset();upstream.mockResolvedValue(new Response(JSON.stringify({items:[],scope:'MARKET_ONLY'}),{status:200}));vi.stubGlobal('fetch',upstream);});

it('does not forward arbitrary routes or untrusted tenant headers',async()=>{
 const {GET}=await import('./route');
 const missing=await GET(new NextRequest('http://localhost/api/valuation/admin'),{params:Promise.resolve({segments:['admin']})});
 expect(missing.status).toBe(404);expect(upstream).not.toHaveBeenCalled();
 await GET(new NextRequest('http://localhost/api/valuation/attempts?limit=10&tenant=attacker',{headers:{'X-Tenant-Id':'attacker'}}),{params:Promise.resolve({segments:['attempts']})});
 const [url,init]=upstream.mock.calls[0];
 expect(String(url)).toContain('/v1/valuation/attempts?limit=10');expect(String(url)).not.toContain('attacker');
 expect(new Headers(init.headers).get('X-Tenant-Id')).toBe('trusted-tenant');
});
it('requires a stable key before forwarding a calculation',async()=>{
 const {POST}=await import('./route');
 const response=await POST(new NextRequest('http://localhost/api/valuation/attempts',{method:'POST',body:'{}'}),{params:Promise.resolve({segments:['attempts']})});
 expect(response.status).toBe(400);expect(upstream).not.toHaveBeenCalled();
});
it('allowlists keyed component requests and independent decisions',async()=>{
 const {POST}=await import('./route');const id='00000000-0000-7000-8000-000000000001';
 const response=await POST(new NextRequest(`http://localhost/api/valuation/batches/${id}/amendments`,{method:'POST',headers:{'Idempotency-Key':'retry-key'},body:'{}'}),{params:Promise.resolve({segments:['batches',id,'amendments']})});
 expect(response.status).toBe(200);expect(new Headers(upstream.mock.calls[0][1].headers).get('Idempotency-Key')).toBe('retry-key');
 const denied=await POST(new NextRequest('http://localhost/api/valuation/amendments/not-an-id/approve',{method:'POST',body:'{}'}),{params:Promise.resolve({segments:['amendments','not-an-id','approve']})});
 expect(denied.status).toBe(404);
});
