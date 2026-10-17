import {it,expect,vi,beforeEach} from 'vitest';
import {NextRequest} from 'next/server';
const mocks=vi.hoisted(()=>({access:vi.fn(),get:vi.fn()}));
vi.mock('@/lib/server/workspace-access',()=>({resolveWorkspaceAccess:mocks.access}));
vi.mock('@/lib/pricing-policy-api',()=>({pricingPolicyClient:async()=>({GET:mocks.get})}));
vi.mock('server-only',()=>({}));
import {GET} from './route';
beforeEach(()=>vi.clearAllMocks());
it('bounds visible-label lookup and returns only exact authorized IDs',async()=>{
 mocks.access.mockResolvedValue({kind:'ready',workspace:{moduleCodes:['MARKET_DATA']}});
 const id='00000000-0000-7000-8000-000000000001';
 mocks.get.mockResolvedValue({data:{data:[{referenceNodeId:id,canonicalName:'Exact'},{referenceNodeId:'other',canonicalName:'Must not leak'}]},response:new Response(null,{status:200})});
 const response=await GET(new NextRequest(`http://ops.test/api/market-data/references?ids=${id},${id}`));
 expect(await response.json()).toEqual({labels:{[id]:'Exact'}});
});
it('rejects malformed bulk IDs instead of widening the search',async()=>{
 mocks.access.mockResolvedValue({kind:'ready',workspace:{moduleCodes:['MARKET_DATA']}});
 const response=await GET(new NextRequest('http://ops.test/api/market-data/references?ids=not-a-uuid'));expect(response.status).toBe(400);
});
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
