import {expect,it,vi} from 'vitest';
import {NextRequest} from 'next/server';
import {SessionRequiredError} from '@/lib/server/workspace-errors';
vi.mock('server-only',()=>({}));
vi.mock('@/lib/pricing-policy-api',()=>({pricingPolicyClient:vi.fn()}));
import {pricingPolicyClient} from '@/lib/pricing-policy-api';
import {GET,POST} from './route';
it('returns a non-retryable session error rather than pretending the API is down',async()=>{
 vi.mocked(pricingPolicyClient).mockRejectedValue(new SessionRequiredError());
 const request=new NextRequest('http://ops.test/api/market-data/sources');
 const response=await GET(request);
 expect(response.status).toBe(401);
 expect((await response.json()).error).toMatchObject({code:'ACTIVE_TENANT_REQUIRED',retryable:false});
 const posted=await POST(new NextRequest(request.url,{method:'POST',headers:{'Idempotency-Key':'stable-key'},body:'{}'}));
 expect(posted.status).toBe(401);
});
