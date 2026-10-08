import {describe,it,expect,vi} from 'vitest';
import {NextRequest} from 'next/server';
vi.mock('server-only',()=>({}));
vi.mock('./tenant-session',()=>({getActiveTenantContext:async()=>({tenantId:'tenant-1',userAccountId:'actor-1',source:'local-session'})}));
import {readBookingWrite} from './booking-write-guard';

function request(body='{}',headers:Record<string,string>={}){
  return new NextRequest('http://test/api/trades',{method:'POST',body,headers:{'Idempotency-Key':'key','X-Expected-Tenant-Id':'tenant-1',...headers}});
}
describe('booking write guard',()=>{
  it.each([
    ['{}',{'Idempotency-Key':''},400,'IDEMPOTENCY_KEY_REQUIRED'],
    ['{}',{'X-Expected-Tenant-Id':''},400,'EXPECTED_TENANT_REQUIRED'],
    ['{}',{'X-Expected-Tenant-Id':'tenant-2'},409,'TENANT_CONTEXT_CHANGED'],
    ['{',{},400,'INVALID_JSON'],['null',{},400,'INVALID_JSON'],['[]',{},400,'INVALID_JSON'],
  ])('refuses invalid booking envelope %s %j',async(body,headers,status,code)=>{
    const result=await readBookingWrite(request(body,headers));
    expect(result.response?.status).toBe(status);
    expect((await result.response!.json()).error.code).toBe(code);
  });
  it('preserves legacy cash but refuses enriched cash without expected tenant',async()=>{
    const legacy=await readBookingWrite(request('{"listingId":"listing"}',{'X-Expected-Tenant-Id':''}),true);
    expect(legacy.response).toBeUndefined();expect(legacy.context?.tenantId).toBe('tenant-1');
    const enriched=await readBookingWrite(request('{"properties":[]}',{'X-Expected-Tenant-Id':''}),true);
    expect(enriched.response?.status).toBe(400);
  });
  it('ignores client tenant and actor headers and trims the retry key',async()=>{
    const result=await readBookingWrite(request('{}',{'Idempotency-Key':' key ','X-Tenant-Id':'forged','X-User-Account-Id':'forged'}));
    expect(result.context).toMatchObject({tenantId:'tenant-1',userAccountId:'actor-1'});
    expect(result.key).toBe('key');
  });
  it('requires explicit tenant context for a legacy-shaped cash correction',async()=>{
    const result=await readBookingWrite(request('{"correction":{"tradeId":"original"}}',{'X-Expected-Tenant-Id':''}),true);
    expect(result.response?.status).toBe(400);
  });
});
