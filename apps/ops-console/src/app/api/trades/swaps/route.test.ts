import {NextRequest} from 'next/server';
import {afterEach,expect,it,vi} from 'vitest';
vi.mock('server-only',()=>({}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:async()=>({tenantId:'tenant',userAccountId:'actor'})}));
import {POST} from './route';

afterEach(()=>vi.unstubAllGlobals());
const payload={instrumentId:'swap',executionPrice:'0',quantity:'1000000',executionRoute:'OTC'};
function request(headers:Record<string,string>={}){return new NextRequest('http://test/api/trades/swaps',{method:'POST',headers,body:JSON.stringify(payload)});}
const headers={'Idempotency-Key':'key','X-Expected-Tenant-Id':'tenant'};
it('requires replay key and expected tenant',async()=>{
  expect((await POST(request())).status).toBe(400);
  expect((await POST(request({'Idempotency-Key':'key'}))).status).toBe(400);
});
it('rejects a tenant change without an upstream write',async()=>{
  const send=vi.fn();vi.stubGlobal('fetch',send);
  expect((await POST(request({...headers,'X-Expected-Tenant-Id':'other'}))).status).toBe(409);
  expect(send).not.toHaveBeenCalled();
});
it('forwards one unchanged swap request with trusted identity and zero quote',async()=>{
  const send=vi.fn(async()=>Response.json({data:{trade:{tradeId:'trade'}},meta:{}}));vi.stubGlobal('fetch',send);
  expect((await POST(request({...headers,'X-Tenant-Id':'forged'}))).status).toBe(201);
  expect(send).toHaveBeenCalledTimes(1);
  const [url,options]=send.mock.calls[0] as unknown as [string,RequestInit];
  expect(String(url)).toMatch(/\/v1\/trades\/swaps$/);
  expect(JSON.parse(String(options.body))).toEqual(payload);
  expect(new Headers(options.headers).get('X-Tenant-Id')).toBe('tenant');
  expect(new Headers(options.headers).get('Idempotency-Key')).toBe('key');
});
it.each([403,409,422])('preserves upstream denial and validation status %i',async(status)=>{
  vi.stubGlobal('fetch',async()=>Response.json({status,requestId:'request',code:'product.terms_changed',detail:'Review again',errors:[{location:['body','quantity'],message:'Invalid increment'}]},{status}));
  const response=await POST(request(headers));
  expect(response.status).toBe(status);
  const problem=(await response.json()).error;
  expect(problem.code).toBe('product.terms_changed');
  expect(problem.fieldErrors).toEqual({quantity:['Invalid increment']});
});
