import {NextRequest} from 'next/server';
import {beforeEach, expect, it, vi} from 'vitest';
const mocks=vi.hoisted(()=>({context:vi.fn(),get:vi.fn()}));
vi.mock('server-only',()=>({}));
vi.mock('@/lib/reference-tenant-context',()=>({requireReferenceTenantContext:mocks.context}));
vi.mock('@/lib/mvp-api-client',()=>({getMarketDataSeries:mocks.get}));
import {GET} from './route';
beforeEach(()=>vi.resetAllMocks());
it('passes selected context and both pagination dimensions to the upstream',async()=>{
 mocks.context.mockResolvedValue({tenantId:'chosen',userAccountId:'actor'});
 mocks.get.mockResolvedValue({data:[],meta:{total:0}});
 const response=await GET(new NextRequest('http://ops.test/api/market-data/series?offset=12&observationLimit=25&observationOffset=50'));
 expect(response.status).toBe(200);
 expect(mocks.get).toHaveBeenCalledWith({tenantId:'chosen',userAccountId:'actor'},expect.objectContaining({offset:12,observationLimit:25,observationOffset:50}));
});
it('does not query a demo tenant when no tenant is selected',async()=>{
 const {ReferenceApiError}=await import('@/lib/reference-api-client');
 mocks.context.mockRejectedValue(new ReferenceApiError(401,'Select a tenant','ACTIVE_TENANT_REQUIRED'));
 const response=await GET(new NextRequest('http://ops.test/api/market-data/series'));
 expect(response.status).toBe(401); expect(mocks.get).not.toHaveBeenCalled();
});
