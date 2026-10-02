import { afterEach,expect,it,vi } from 'vitest';
vi.mock('server-only',()=>({}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:async()=>({tenantId:'selected-tenant',userAccountId:'actor'})}));
import { POST } from './route';
afterEach(()=>vi.unstubAllGlobals());
it('submits the option listing using the selected tenant session',async()=>{let headers:Headers|undefined;vi.stubGlobal('fetch',async(_url:unknown,options:RequestInit)=>{headers=new Headers(options.headers);return Response.json({data:{},meta:{}});});expect((await POST(new Request('http://test/api/instruments/equity-listing-proposals',{method:'POST',headers:{'Content-Type':'application/json','X-Tenant-Id':'forged'},body:JSON.stringify({instrumentId:'option'})}))).status).toBe(201);expect(headers?.get('X-Tenant-Id')).toBe('selected-tenant');expect(headers?.get('X-User-Account-Id')).toBe('actor');});
