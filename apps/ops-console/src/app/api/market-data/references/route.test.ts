import {it,expect,vi} from 'vitest';
import {NextRequest} from 'next/server';
const mocks=vi.hoisted(()=>({access:vi.fn(),get:vi.fn()}));
vi.mock('@/lib/server/workspace-access',()=>({resolveWorkspaceAccess:mocks.access}));
vi.mock('@/lib/pricing-policy-api',()=>({pricingPolicyClient:async()=>({GET:mocks.get})}));
vi.mock('server-only',()=>({}));
import {GET} from './route';
it('requires the market-data module before searching reference metadata',async()=>{
 mocks.access.mockResolvedValue({kind:'ready',workspace:{moduleCodes:['SECURITY_MASTER']}});
 const response=await GET(new NextRequest('http://ops.test/api/market-data/references?q=HSBC'));
 expect(response.status).toBe(403);expect(mocks.get).not.toHaveBeenCalled();
});
it('forwards upstream failures without inventing fixture references',async()=>{
 mocks.access.mockResolvedValue({kind:'ready',workspace:{moduleCodes:['MARKET_DATA']}});
 mocks.get.mockResolvedValue({error:{code:'UNAVAILABLE'},response:new Response(null,{status:503})});
 const response=await GET(new NextRequest('http://ops.test/api/market-data/references?q=HSBC'));
 expect(response.status).toBe(503);expect(await response.json()).toEqual({error:{code:'UNAVAILABLE'}});
});
