import { NextRequest } from 'next/server';
import { afterEach,expect,it,vi } from 'vitest';
vi.mock('server-only',()=>({}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:async()=>({tenantId:'tenant',userAccountId:'actor'})}));
import { POST } from './route';
afterEach(()=>vi.unstubAllGlobals());
function request(headers:Record<string,string>={}){return new NextRequest('http://test/api/trades/options',{method:'POST',headers,body:JSON.stringify({listingId:'listing'})});}
it('requires key and expected tenant',async()=>{expect((await POST(request())).status).toBe(400);expect((await POST(request({'Idempotency-Key':'key'}))).status).toBe(400);});
it('rejects changed tenant before forwarding',async()=>{const fetch=vi.fn();vi.stubGlobal('fetch',fetch);expect((await POST(request({'Idempotency-Key':'key','X-Expected-Tenant-Id':'other'}))).status).toBe(409);expect(fetch).not.toHaveBeenCalled();});
it('forwards only server identity and original idempotency key',async()=>{let sent:Headers|undefined;vi.stubGlobal('fetch',async(_url:unknown,options:RequestInit)=>{sent=new Headers(options.headers);return Response.json({data:{trade:{tradeId:'trade'}},meta:{}});});expect((await POST(request({'Idempotency-Key':'key','X-Expected-Tenant-Id':'tenant','X-Tenant-Id':'forged'}))).status).toBe(201);expect(sent?.get('X-Tenant-Id')).toBe('tenant');expect(sent?.get('Idempotency-Key')).toBe('key');});
