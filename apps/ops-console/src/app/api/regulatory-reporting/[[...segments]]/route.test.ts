import {beforeEach,expect,it,vi} from 'vitest';
import {NextRequest} from 'next/server';
vi.mock('server-only',()=>({}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:async()=>({tenantId:'trusted-tenant',userAccountId:'trusted-user'})}));
const upstream=vi.hoisted(()=>vi.fn());
beforeEach(()=>{upstream.mockReset();upstream.mockResolvedValue(new Response('{}',{status:200}));vi.stubGlobal('fetch',upstream);});
it('allowlists routes and derives authoritative context',async()=>{
 const {GET}=await import('./route');
 expect((await GET(new NextRequest('http://localhost/api/regulatory-reporting/admin'),{params:Promise.resolve({segments:['admin']})})).status).toBe(404);
 await GET(new NextRequest('http://localhost/api/regulatory-reporting/candidates?strategyId=chosen&fromDate=2026-10-28&tenantId=bad'),{params:Promise.resolve({segments:['candidates']})});
 const [url,init]=upstream.mock.calls[0];expect(String(url)).toContain('fromDate=2026-10-28');expect(String(url)).not.toContain('tenantId');
 expect(new Headers(init.headers).get('X-Tenant-Id')).toBe('trusted-tenant');
});
it('requires a stable key for frozen exports',async()=>{
 const {POST}=await import('./route');const context={params:Promise.resolve({segments:['exports']})};
 expect((await POST(new NextRequest('http://localhost/api/regulatory-reporting/exports',{method:'POST',body:'{}'}),context)).status).toBe(400);
 expect(upstream).not.toHaveBeenCalled();
 await POST(new NextRequest('http://localhost/api/regulatory-reporting/exports',{method:'POST',body:'{}',headers:{'Idempotency-Key':'stable'}}),context);
 expect(new Headers(upstream.mock.calls[0][1].headers).get('Idempotency-Key')).toBe('stable');
});
