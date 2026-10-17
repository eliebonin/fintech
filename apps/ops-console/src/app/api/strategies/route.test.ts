import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {NextRequest} from 'next/server';

vi.mock('server-only',()=>({}));
const h=vi.hoisted(()=>({context:vi.fn(),upstream:vi.fn()}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:h.context}));
vi.mock('@/lib/reference-fetch',()=>({referenceFetch:()=>h.upstream}));
import {GET,POST} from './route';
import {SessionRequiredError,WorkspaceApiError} from '@/lib/server/workspace-errors';

function request(expected:Record<string,string>={},body='{"strategyCode":"ALPHA","displayName":"Alpha","strategyType":"FUND"}'){
 return new NextRequest('http://console.test/api/strategies',{method:'POST',headers:{
  'Content-Type':'application/json','X-Expected-Tenant-Id':'tenant-a','X-Expected-User-Id':'user-a',...expected},body});
}
beforeEach(()=>{
 h.context.mockResolvedValue({tenantId:'tenant-a',userAccountId:'user-a',source:'local-session'});
 h.upstream.mockResolvedValue(Response.json({data:{strategyId:'created',displayName:'Alpha'}},{status:201}));
});
afterEach(()=>vi.resetAllMocks());

it.each([
 [{'X-Expected-Tenant-Id':''},400,'WRITE_CONTEXT_REQUIRED'],
 [{'X-Expected-User-Id':''},400,'WRITE_CONTEXT_REQUIRED'],
 [{'X-Expected-Tenant-Id':'tenant-b'},409,'TENANT_CONTEXT_CHANGED'],
 [{'X-Expected-User-Id':'user-b'},409,'TENANT_CONTEXT_CHANGED'],
])('blocks missing or stale form context before forwarding %j',async(headers,status,code)=>{
 const response=await POST(request(headers));
 expect(response.status).toBe(status);
 expect((await response.json()).error.code).toBe(code);
 expect(h.upstream).not.toHaveBeenCalled();
});
it('forwards the server-resolved identity, never browser authoritative headers',async()=>{
 const response=await POST(request({'X-Tenant-Id':'forged','X-User-Account-Id':'forged'}));
 expect(response.status).toBe(201);
 const init=h.upstream.mock.calls[0][1];
 const headers=new Headers(init.headers);
 expect(headers.get('X-Tenant-Id')).toBe('tenant-a');
 expect(headers.get('X-User-Account-Id')).toBe('user-a');
 expect(JSON.parse(init.body)).toEqual({strategyCode:'ALPHA',displayName:'Alpha',strategyType:'FUND'});
});
it.each([
 [new SessionRequiredError(),401],
 [new WorkspaceApiError(403),403],
 [new WorkspaceApiError(503),503],
 [new Error('sensitive connection detail'),503],
])('preserves unavailable versus unauthenticated context (%s)',async(error,status)=>{
 h.context.mockRejectedValue(error);
 const response=await POST(request());
 expect(response.status).toBe(status);
 expect(JSON.stringify(await response.json())).not.toContain('sensitive connection detail');
 expect(h.upstream).not.toHaveBeenCalled();
});
it('does not require write-context headers on a strategy read',async()=>{
 h.upstream.mockResolvedValue(Response.json({data:[]}));
 expect((await GET()).status).toBe(200);
});
