import {afterEach,expect,it,vi} from 'vitest';
import {NextRequest} from 'next/server';
const h=vi.hoisted(()=>({fetch:vi.fn(),context:vi.fn()}));
vi.mock('server-only',()=>({}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:h.context}));
vi.mock('@/lib/reference-fetch',()=>({referenceFetch:()=>h.fetch}));
import {GET} from './route';
afterEach(()=>vi.clearAllMocks());
it('forwards only scoped trade-timeline filters through the selected tenant context',async()=>{
 h.context.mockResolvedValue({tenantId:'selected-tenant',userAccountId:'selected-user'});
 h.fetch.mockResolvedValue(Response.json({items:[],total:0}));
 const response=await GET(new NextRequest('http://localhost/api/valuation/balance-trades?strategyId=s&instrumentId=b&fromDate=2026-01-01&toDate=2026-10-20&tenantId=spoofed'),{params:Promise.resolve({segments:['balance-trades']})});
 expect(response.status).toBe(200);const parsed=new URL(h.fetch.mock.calls[0][0]);
 expect(parsed.searchParams.get('instrumentId')).toBe('b');expect(parsed.searchParams.has('tenantId')).toBe(false);
});
it('forwards only the allowed series filters through the selected tenant context',async()=>{
 h.context.mockResolvedValue({tenantId:'selected-tenant',userAccountId:'selected-user'});
 h.fetch.mockResolvedValue(Response.json({items:[],total:0}));
 const response=await GET(new NextRequest('http://localhost/api/valuation/balance-series?strategyId=strategy&instrumentId=bond&fromDate=2024-01-01&toDate=2026-10-20&tenantId=spoofed&extra=ignore'),{params:Promise.resolve({segments:['balance-series']})});
 expect(response.status).toBe(200);
 const [url,init]=h.fetch.mock.calls[0],parsed=new URL(url);
 expect(parsed.searchParams.get('instrumentId')).toBe('bond');expect(parsed.searchParams.get('fromDate')).toBe('2024-01-01');
 expect(parsed.searchParams.has('tenantId')).toBe(false);expect(parsed.searchParams.has('extra')).toBe(false);
 expect(init.headers.get('X-Tenant-Id')).toBe('selected-tenant');
});
it('keeps arbitrary upstream paths unavailable',async()=>{
 const response=await GET(new NextRequest('http://localhost/api/valuation/arbitrary'),{params:Promise.resolve({segments:['arbitrary']})});
 expect(response.status).toBe(404);expect(h.fetch).not.toHaveBeenCalled();
});
it('forwards only strategy/day/stage for the interest review through verified context',async()=>{
 h.context.mockResolvedValue({tenantId:'selected-tenant',userAccountId:'selected-user'});
 h.fetch.mockResolvedValue(Response.json({rows:[],sourceHash:'a'.repeat(64)}));
 const response=await GET(new NextRequest('http://localhost/api/valuation/interest-review?strategyId=s&valueDate=2026-10-20&stage=BALANCE&tenantId=spoofed&fromDate=2020-01-01'),{params:Promise.resolve({segments:['interest-review']})});
 expect(response.status).toBe(200);const parsed=new URL(h.fetch.mock.calls[0][0]);
 expect(parsed.searchParams.get('valueDate')).toBe('2026-10-20');expect(parsed.searchParams.get('stage')).toBe('BALANCE');
 expect(parsed.searchParams.has('tenantId')).toBe(false);expect(parsed.searchParams.has('fromDate')).toBe(false);
});
it('forwards the history instrument filter and paging without accepting browser identity',async()=>{
 h.context.mockResolvedValue({tenantId:'selected-tenant',userAccountId:'selected-user'});
 h.fetch.mockResolvedValue(Response.json({items:[],total:0,offset:25,limit:25}));
 await GET(new NextRequest('http://localhost/api/valuation/balance-history?strategyId=s&instrumentId=b&fromDate=2026-10-01&toDate=2026-10-20&offset=25&limit=25&tenantId=spoofed'),{params:Promise.resolve({segments:['balance-history']})});
 const parsed=new URL(h.fetch.mock.calls[0][0]);
 expect(parsed.searchParams.get('instrumentId')).toBe('b');expect(parsed.searchParams.get('offset')).toBe('25');expect(parsed.searchParams.has('tenantId')).toBe(false);
});
