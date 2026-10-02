import { NextRequest } from 'next/server';
import { afterEach,expect,it,vi } from 'vitest';
const session=vi.hoisted(()=>({context:vi.fn()}));
vi.mock('server-only',()=>({}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:session.context}));
import { GET } from './route';
afterEach(()=>{session.context.mockReset();vi.unstubAllGlobals();});
it('requires a selected tenant before any reference search',async()=>{session.context.mockRejectedValue(new Error('No session'));const fetch=vi.fn();vi.stubGlobal('fetch',fetch);expect((await GET(new NextRequest('http://test/api/reference-nodes/search?q=HSBC'))).status).toBe(401);expect(fetch).not.toHaveBeenCalled();});
it('uses the selected tenant rather than the demo default or forged header',async()=>{session.context.mockResolvedValue({tenantId:'selected-tenant',userAccountId:'actor'});let headers:Headers|undefined;vi.stubGlobal('fetch',async(_url:unknown,options:RequestInit)=>{headers=new Headers(options.headers);return Response.json({data:[],meta:{}});});expect((await GET(new NextRequest('http://test/api/reference-nodes/search?q=HSBC',{headers:{'X-Tenant-Id':'forged'}}))).status).toBe(200);expect(headers?.get('X-Tenant-Id')).toBe('selected-tenant');});
