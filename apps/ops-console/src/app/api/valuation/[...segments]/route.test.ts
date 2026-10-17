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
it('requires a stable key for explicit reassessment recalculation',async()=>{
 const {POST}=await import('./route');
 const response=await POST(new NextRequest('http://localhost/api/valuation/reassessments/recalculate',{method:'POST',body:'{}'}),{params:Promise.resolve({segments:['reassessments','recalculate']})});
 expect(response.status).toBe(400);expect(upstream).not.toHaveBeenCalled();
});
it('forwards exact-date cash queries without client-supplied authority',async()=>{
 const {GET,POST}=await import('./route');
 await GET(new NextRequest('http://localhost/api/valuation/cash-balances?strategyId=chosen&valueDate=2026-10-10&tenant=attacker'),{params:Promise.resolve({segments:['cash-balances']})});
 const url=new URL(String(upstream.mock.calls[0][0]));
 expect(url.searchParams.get('valueDate')).toBe('2026-10-10');expect(url.searchParams.get('strategyId')).toBe('chosen');expect(url.searchParams.has('tenant')).toBe(false);
 const noKey=await POST(new NextRequest('http://localhost/api/valuation/cash-balances',{method:'POST',body:'{}'}),{params:Promise.resolve({segments:['cash-balances']})});
 expect(noKey.status).toBe(400);
});
it('forwards an explicit self-publication only through its allowlisted endpoint',async()=>{
 const {POST}=await import('./route');const id='00000000-0000-7000-8000-000000000001';
 const response=await POST(new NextRequest(`http://localhost/api/valuation/batches/${id}/self-publish`,{method:'POST',body:JSON.stringify({comment:'Single-person desk',confirmSelfPublication:true})}),{params:Promise.resolve({segments:['batches',id,'self-publish']})});
 expect(response.status).toBe(200);expect(String(upstream.mock.calls[0][0])).toContain(`/batches/${id}/self-publish`);
 expect(JSON.parse(upstream.mock.calls[0][1].body)).toEqual({comment:'Single-person desk',confirmSelfPublication:true});
});
it('forwards report filters but not invented tenant or actor context',async()=>{
 const {GET}=await import('./route');
 await GET(new NextRequest('http://localhost/api/valuation/attempts?strategy_id=chosen&from_date=2026-10-01&to_date=2026-10-07&calculation_status=COMPLETED&publication_status=STAGED&results_only=true&offset=25&tenant=attacker'),{params:Promise.resolve({segments:['attempts']})});
 const url=new URL(String(upstream.mock.calls[0][0]));
 for(const [key,value] of Object.entries({strategy_id:'chosen',from_date:'2026-10-01',to_date:'2026-10-07',calculation_status:'COMPLETED',publication_status:'STAGED',results_only:'true',offset:'25'}))expect(url.searchParams.get(key)).toBe(value);
 expect(url.searchParams.has('tenant')).toBe(false);
});
it('allowlists keyed component requests and independent decisions',async()=>{
 const {POST}=await import('./route');const id='00000000-0000-7000-8000-000000000001';
 const response=await POST(new NextRequest(`http://localhost/api/valuation/batches/${id}/amendments`,{method:'POST',headers:{'Idempotency-Key':'retry-key'},body:'{}'}),{params:Promise.resolve({segments:['batches',id,'amendments']})});
 expect(response.status).toBe(200);expect(new Headers(upstream.mock.calls[0][1].headers).get('Idempotency-Key')).toBe('retry-key');
 const denied=await POST(new NextRequest('http://localhost/api/valuation/amendments/not-an-id/approve',{method:'POST',body:'{}'}),{params:Promise.resolve({segments:['amendments','not-an-id','approve']})});
 expect(denied.status).toBe(404);
});
it('forwards bounded option searches and selected lookup without browser authority',async()=>{
 const {GET}=await import('./route');
 const response=await GET(new NextRequest('http://localhost/api/valuation/option-choices?kind=strategies&q=alpha&limit=25&offset=500&selected_id=chosen&for_calculation=true&tenant=attacker'),{params:Promise.resolve({segments:['option-choices']})});
 expect(response.status).toBe(200);
 const url=new URL(String(upstream.mock.calls[0][0]));
 for(const [key,value] of Object.entries({kind:'strategies',q:'alpha',limit:'25',offset:'500',selected_id:'chosen',for_calculation:'true'}))expect(url.searchParams.get(key)).toBe(value);
 expect(url.searchParams.has('tenant')).toBe(false);
});
