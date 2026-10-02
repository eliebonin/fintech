import {NextRequest} from 'next/server';
import {afterEach,expect,it,vi} from 'vitest';
vi.mock('server-only',()=>({}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:async()=>({tenantId:'tenant',userAccountId:'actor'})}));
import {POST} from './route';
afterEach(()=>vi.unstubAllGlobals());
function request(headers:Record<string,string>={}){return new NextRequest('http://test/api/trades/futures',{method:'POST',headers,body:JSON.stringify({listingId:'listing'})});}
it('requires replay key and expected tenant',async()=>{expect((await POST(request())).status).toBe(400);expect((await POST(request({'Idempotency-Key':'key'}))).status).toBe(400);});
it('rejects tenant switches before writing upstream',async()=>{const send=vi.fn();vi.stubGlobal('fetch',send);expect((await POST(request({'Idempotency-Key':'key','X-Expected-Tenant-Id':'other'}))).status).toBe(409);expect(send).not.toHaveBeenCalled();});
it('forwards trusted server identity and unchanged key',async()=>{let headers:Headers|undefined;vi.stubGlobal('fetch',async(_url:unknown,options:RequestInit)=>{headers=new Headers(options.headers);return Response.json({data:{trade:{tradeId:'trade'}},meta:{}});});expect((await POST(request({'Idempotency-Key':'key','X-Expected-Tenant-Id':'tenant','X-Tenant-Id':'forged'}))).status).toBe(201);expect(headers?.get('X-Tenant-Id')).toBe('tenant');expect(headers?.get('Idempotency-Key')).toBe('key');});
