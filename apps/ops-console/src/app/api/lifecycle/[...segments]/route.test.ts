import {beforeEach,expect,it,vi} from 'vitest';
import {NextRequest} from 'next/server';
vi.mock('server-only',()=>({}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:async()=>({tenantId:'trusted-tenant',userAccountId:'trusted-user'})}));
const upstream=vi.hoisted(()=>vi.fn());
it('allowlists coupon reads and keyed confirmations with trusted context only',async()=>{
 const {GET,POST}=await import('./route');
 const context={params:Promise.resolve({segments:['coupons','payments']})};
 expect((await POST(new NextRequest('http://localhost/api/lifecycle/coupons/payments',{method:'POST',body:'{}'}),context)).status).toBe(400);
 await GET(new NextRequest('http://localhost/api/lifecycle/coupons/payments?strategyId=chosen&fromDate=2026-10-01&toDate=2026-10-15&tenant=bad'),context);
 expect(String(upstream.mock.calls[0][0])).toContain('fromDate=2026-10-01');
 expect(String(upstream.mock.calls[0][0])).not.toContain('tenant=bad');
});
beforeEach(()=>{upstream.mockReset();upstream.mockResolvedValue(new Response(JSON.stringify({items:[]}),{status:200}));vi.stubGlobal('fetch',upstream);});
it('allowlists lifecycle routes and retains strategy filters without accepting actor headers',async()=>{
 const {GET}=await import('./route');
 const absent=await GET(new NextRequest('http://localhost/api/lifecycle/admin'),{params:Promise.resolve({segments:['admin']})});expect(absent.status).toBe(404);
 await GET(new NextRequest('http://localhost/api/lifecycle/bond-redemptions?strategyId=chosen&offset=25&tenant=bad'),{params:Promise.resolve({segments:['bond-redemptions']})});
 const [url,init]=upstream.mock.calls[0];expect(String(url)).toContain('strategyId=chosen');expect(String(url)).not.toContain('tenant=bad');
 expect(new Headers(init.headers).get('X-Tenant-Id')).toBe('trusted-tenant');
});
it('requires a stable key before forwarding financial booking',async()=>{
 const {POST}=await import('./route');
 const response=await POST(new NextRequest('http://localhost/api/lifecycle/bond-redemptions/book',{method:'POST',body:'{}'}),{params:Promise.resolve({segments:['bond-redemptions','book']})});
 expect(response.status).toBe(400);expect(upstream).not.toHaveBeenCalled();
});
it('forwards only allowlisted FX maturity commands and requires a stable key',async()=>{
 const {GET,POST}=await import('./route');
 expect((await POST(new NextRequest('http://localhost/api/lifecycle/fx-forward/closures/book',{method:'POST',body:'{}'}),
  {params:Promise.resolve({segments:['fx-forward','closures','book']})})).status).toBe(400);
 await GET(new NextRequest('http://localhost/api/lifecycle/fx-forward/options?strategyId=chosen'),
  {params:Promise.resolve({segments:['fx-forward','options']})});
 expect(String(upstream.mock.calls[0][0])).toContain('/v1/lifecycle/fx-forward/options?strategyId=chosen');
});

it('forwards scoped assistance queries and rejects a stale tenant context',async()=>{
 const {GET,POST}=await import('./route');
 const context={params:Promise.resolve({segments:['assistance']})};
 const response=await GET(new NextRequest('http://localhost/api/lifecycle/assistance?strategyId=chosen&eventType=BOND_MATURITY&tenant=bad',{headers:{'X-Expected-Tenant-Id':'trusted-tenant'}}),context);
 expect(response.status).toBe(200);expect(String(upstream.mock.calls[0][0])).toContain('eventType=BOND_MATURITY');
 upstream.mockClear();
 expect((await POST(new NextRequest('http://localhost/api/lifecycle/assistance',{method:'POST',headers:{'X-Expected-Tenant-Id':'old-tenant'},body:'{}'}),context)).status).toBe(409);
 expect(upstream).not.toHaveBeenCalled();
});

it('forwards complete worklist filters and rejects cross-context reads or writes',async()=>{
 const {GET,POST}=await import('./route');
 const context={params:Promise.resolve({segments:['worklist']})};
 const response=await GET(new NextRequest('http://localhost/api/lifecycle/worklist?fromDate=2026-11-01&toDate=2026-11-30&attention=ACTIONABLE&status=OVERDUE&includeEarlierOverdue=true&offset=25&limit=25&tenant=untrusted',{headers:{'X-Expected-Tenant-Id':'trusted-tenant'}}),context);
 expect(response.status).toBe(200);
 const target=new URL(String(upstream.mock.calls[0][0]));
 expect(target.searchParams.get('attention')).toBe('ACTIONABLE');expect(target.searchParams.get('includeEarlierOverdue')).toBe('true');expect(target.searchParams.get('offset')).toBe('25');expect(target.searchParams.has('tenant')).toBe(false);
 upstream.mockClear();
 expect((await GET(new NextRequest('http://localhost/api/lifecycle/worklist',{headers:{'X-Expected-Tenant-Id':'other'}}),context)).status).toBe(409);
 expect((await POST(new NextRequest('http://localhost/api/lifecycle/worklist',{method:'POST',body:'{}'}),context)).status).toBe(404);
 expect(upstream).not.toHaveBeenCalled();
});
