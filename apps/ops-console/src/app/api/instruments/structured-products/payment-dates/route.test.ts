import {beforeEach,expect,it,vi} from 'vitest';
vi.mock('server-only',()=>({}));
const api=vi.hoisted(()=>({GET:vi.fn(),POST:vi.fn()}));
vi.mock('@/lib/pricing-policy-api',()=>({pricingPolicyClient:async()=>api}));
beforeEach(()=>{vi.clearAllMocks();});
it('preserves the upstream request and correlation evidence',async()=>{
  const {GET}=await import('./route');
  api.GET.mockResolvedValue({error:{detail:'Calendar is unavailable'},response:new Response(null,{status:403,
    headers:{'X-Request-Id':'upstream-id','X-Correlation-Id':'correlation-id'}})});
  const result=await GET(new Request('http://localhost/api/instruments/structured-products/payment-dates'));
  expect(result.status).toBe(403);expect(result.headers.get('X-Request-Id')).toBe('upstream-id');
  expect(result.headers.get('X-Correlation-Id')).toBe('correlation-id');
});
it('rejects malformed JSON as a client error without an upstream call',async()=>{
  const {POST}=await import('./route');
  const result=await POST(new Request('http://localhost/api/instruments/structured-products/payment-dates',{method:'POST',body:'{'}));
  expect(result.status).toBe(400);expect(api.POST).not.toHaveBeenCalled();
});
