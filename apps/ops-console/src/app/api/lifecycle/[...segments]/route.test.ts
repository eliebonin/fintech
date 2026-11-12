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


it('forwards coupon inspection only as an expected-tenant GET with scoped source IDs',async()=>{
 const {GET,POST}=await import('./route');const context={params:Promise.resolve({segments:['worklist','coupon']})};
 const response=await GET(new NextRequest('http://localhost/api/lifecycle/worklist/coupon?strategyId=chosen&periodId=source-period&tenant=untrusted',{headers:{'X-Expected-Tenant-Id':'trusted-tenant'}}),context);
 expect(response.status).toBe(200);const target=new URL(String(upstream.mock.calls[0][0]));
 expect(target.searchParams.get('periodId')).toBe('source-period');expect(target.searchParams.get('strategyId')).toBe('chosen');expect(target.searchParams.has('tenant')).toBe(false);
 upstream.mockClear();
 expect((await GET(new NextRequest('http://localhost/api/lifecycle/worklist/coupon',{headers:{'X-Expected-Tenant-Id':'stale'}}),context)).status).toBe(409);
 expect((await POST(new NextRequest('http://localhost/api/lifecycle/worklist/coupon',{method:'POST',body:'{}'}),context)).status).toBe(404);
 expect(upstream).not.toHaveBeenCalled();
});

it('future inspection is GET-only, context-bound and forwards only scoped milestone inputs',async()=>{
 const {GET,POST}=await import('./route');const context={params:Promise.resolve({segments:['worklist','future']})};
 const url='http://localhost/api/lifecycle/worklist/future?strategyId=strategy&instrumentId=instrument&milestoneKind=LAST_TRADE&tenant=bad';
 expect((await GET(new NextRequest(url),context)).status).toBe(409);expect(upstream).not.toHaveBeenCalled();
 expect((await GET(new NextRequest(url,{headers:{'X-Expected-Tenant-Id':'trusted-tenant'}}),context)).status).toBe(200);
 expect(String(upstream.mock.calls[0][0])).toContain('milestoneKind=LAST_TRADE');expect(String(upstream.mock.calls[0][0])).not.toContain('tenant=bad');
 upstream.mockClear();expect((await POST(new NextRequest(url,{method:'POST',body:'{}'}),context)).status).toBe(404);expect(upstream).not.toHaveBeenCalled();
});

it('option inspection is GET-only and binds the expected tenant and milestone scope',async()=>{
 const {GET,POST}=await import('./route');const context={params:Promise.resolve({segments:['worklist','option']})};
 const url='http://localhost/api/lifecycle/worklist/option?strategyId=strategy&instrumentId=option&milestoneKind=EXPIRY&actor=bad';
 expect((await GET(new NextRequest(url),context)).status).toBe(409);expect(upstream).not.toHaveBeenCalled();
 expect((await GET(new NextRequest(url,{headers:{'X-Expected-Tenant-Id':'trusted-tenant'}}),context)).status).toBe(200);
 expect(String(upstream.mock.calls[0][0])).toContain('milestoneKind=EXPIRY');expect(String(upstream.mock.calls[0][0])).not.toContain('actor=bad');
 upstream.mockClear();expect((await POST(new NextRequest(url,{method:'POST',body:'{}'}),context)).status).toBe(404);expect(upstream).not.toHaveBeenCalled();
});

it('structured schedule inspection is GET-only and tenant/position scoped',async()=>{
 const {GET,POST}=await import('./route');const context={params:Promise.resolve({segments:['worklist','structured']})};
 const url='http://localhost/api/lifecycle/worklist/structured?strategyId=strategy&instrumentId=held&eventKey=notice&actor=bad';
 expect((await GET(new NextRequest(url),context)).status).toBe(409);expect(upstream).not.toHaveBeenCalled();
 expect((await GET(new NextRequest(url,{headers:{'X-Expected-Tenant-Id':'trusted-tenant'}}),context)).status).toBe(200);
 expect(String(upstream.mock.calls[0][0])).toContain('eventKey=notice');expect(String(upstream.mock.calls[0][0])).not.toContain('actor=bad');
 upstream.mockClear();expect((await POST(new NextRequest(url,{method:'POST',body:'{}'}),context)).status).toBe(404);expect(upstream).not.toHaveBeenCalled();
});


it('read failures offer filter retry without booking-key instructions; writes keep uncertain-outcome guidance',async()=>{
 const {GET,POST}=await import('./route');upstream.mockRejectedValue(new DOMException('Read timed out','TimeoutError'));
 const read=await GET(new NextRequest('http://localhost/api/lifecycle/worklist',{headers:{'X-Expected-Tenant-Id':'trusted-tenant'}}),{params:Promise.resolve({segments:['worklist']})});
 const body=await read.json();expect(read.status).toBe(503);expect(body.error.message).toContain('Retry the applied filters');expect(body.error.message).not.toMatch(/booking|request key/i);
 const write=await POST(new NextRequest('http://localhost/api/lifecycle/bond-redemptions/book',{method:'POST',headers:{'Idempotency-Key':'unchanged-key'},body:'{}'}),{params:Promise.resolve({segments:['bond-redemptions','book']})});
 expect((await write.json()).error.message).toContain('same request key');
});


it('gives the full-population worklist a bounded read budget without extending small reads or writes',async()=>{
 const deadline=vi.spyOn(AbortSignal,'timeout');const {GET,POST}=await import('./route');upstream.mockImplementation(async()=>Response.json({items:[]}));
 await GET(new NextRequest('http://localhost/api/lifecycle/worklist',{headers:{'X-Expected-Tenant-Id':'trusted-tenant'}}),{params:Promise.resolve({segments:['worklist']})});
 expect(deadline).toHaveBeenLastCalledWith(30000);
 await GET(new NextRequest('http://localhost/api/lifecycle/worklist/options',{headers:{'X-Expected-Tenant-Id':'trusted-tenant'}}),{params:Promise.resolve({segments:['worklist','options']})});
 expect(deadline).toHaveBeenLastCalledWith(10000);
 await POST(new NextRequest('http://localhost/api/lifecycle/bond-redemptions/book',{method:'POST',headers:{'Idempotency-Key':'unchanged-key'},body:'{}'}),{params:Promise.resolve({segments:['bond-redemptions','book']})});
 expect(deadline).toHaveBeenLastCalledWith(35000);deadline.mockRestore();
});
