import {NextRequest} from 'next/server';
import {afterEach,expect,it,vi} from 'vitest';
vi.mock('server-only',()=>({}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:async()=>({tenantId:'tenant',userAccountId:'actor'})}));
import {POST} from './route';
afterEach(()=>vi.unstubAllGlobals());
function request(expected='tenant',body='{"canonicalName":"Performance swap","terms":{}}') {
  return new NextRequest('http://test/api/instruments/swaps',{method:'POST',headers:{'X-Expected-Tenant-Id':expected,'X-Tenant-Id':'forged'},body});
}
it('rejects missing and changed tenants before upstream submission',async()=>{
  const send=vi.fn();vi.stubGlobal('fetch',send);
  expect((await POST(request(''))).status).toBe(400);
  expect((await POST(request('other'))).status).toBe(409);
  expect(send).not.toHaveBeenCalled();
});
it('submits to the swap proposal endpoint with trusted identity',async()=>{
  let target='',headers=new Headers(),payload:unknown;
  vi.stubGlobal('fetch',async(url:URL,options:RequestInit)=>{target=url.pathname;headers=new Headers(options.headers);payload=JSON.parse(String(options.body));return Response.json({data:{proposalId:'proposal',status:'PENDING'}});});
  expect((await POST(request())).status).toBe(201);
  expect(target).toBe('/v1/instruments/swap-proposals');
  expect(headers.get('X-Tenant-Id')).toBe('tenant');
  expect(headers.get('X-User-Account-Id')).toBe('actor');
  expect(payload).toEqual({canonicalName:'Performance swap',terms:{}});
});
it('preserves upstream field errors and invalid JSON handling',async()=>{
  expect((await POST(request('tenant','{'))).status).toBe(400);
  vi.stubGlobal('fetch',async()=>Response.json({type:'about:blank',title:'Validation failed',status:422,detail:'Quote divisor required',code:'VALIDATION_ERROR',requestId:'request',errors:[{location:['body','terms','quoteFactor'],message:'Must be positive',type:'value_error'}]},{status:422}));
  const response=await POST(request());
  expect(response.status).toBe(422);
  expect((await response.json()).error.fieldErrors).toEqual({'terms.quoteFactor':['Must be positive']});
});
