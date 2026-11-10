import {NextRequest} from 'next/server';
import {describe,it,expect,vi,beforeEach} from 'vitest';
vi.mock('@/lib/reference-tenant-context',()=>({requireReferenceTenantContext:async()=>({tenantId:'selected',userAccountId:'actor'})}));
vi.mock('@/lib/reference-api-client',()=>({getEquityCreationOptions:vi.fn(async()=>({data:[]}))}));
import {getEquityCreationOptions} from '@/lib/reference-api-client';
import {GET} from './route';
beforeEach(()=>vi.clearAllMocks());
describe('creation choices boundary',()=>{
 it('uses verified context and forwards only the effective date',async()=>{
  const r=await GET(new NextRequest('http://test/api/instruments/equity-creation-options?effectiveDate=2026-11-03&tenantId=attacker'));
  expect(r.status).toBe(200);expect(getEquityCreationOptions).toHaveBeenCalledWith({tenantId:'selected',userAccountId:'actor'},'2026-11-03');
 });
 it('rejects a missing or malformed date before an upstream request',async()=>{
  expect((await GET(new NextRequest('http://test/api/instruments/equity-creation-options'))).status).toBe(400);
  expect(getEquityCreationOptions).not.toHaveBeenCalled();
 });
});
