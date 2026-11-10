import {beforeEach,describe,expect,it,vi} from 'vitest';
import {NextRequest} from 'next/server';
const {proxy,origin}=vi.hoisted(()=>({proxy:vi.fn(),origin:vi.fn()}));
vi.mock('@/lib/server/access-proxy',()=>({accessProxy:proxy,sameOrigin:origin}));
import {POST} from './route';
const tenant='00000000-0000-0000-0000-000000000001';
const context=(path:string[])=>({params:Promise.resolve({path})});
const request=()=>new NextRequest(`http://localhost/api/platform/tenants/${tenant}/lifecycle-subscription/preview`,{method:'POST',body:JSON.stringify({maximumTier:2,expectedRevision:1})});
describe('reviewed platform lifecycle preview',()=>{
 beforeEach(()=>{proxy.mockReset();origin.mockReset();proxy.mockResolvedValue(Response.json({inputHash:'a'.repeat(64)}));});
 it('requires same origin and delegates with platform context',async()=>{
  const response=await POST(request(),context(['tenants',tenant,'lifecycle-subscription','preview']));
  expect(response.status).toBe(200);expect(origin).toHaveBeenCalledOnce();
  expect(proxy).toHaveBeenCalledWith(`/v1/platform/tenants/${tenant}/lifecycle-subscription/preview`,expect.objectContaining({method:'POST'}),'platform');
 });
 it('does not proxy other platform POST paths',async()=>{
  const response=await POST(request(),context(['tenants',tenant,'modules']));
  expect(response.status).toBe(404);expect(proxy).not.toHaveBeenCalled();
 });
 it('denies origin or platform-session failure before returning data',async()=>{
  origin.mockImplementation(()=>{throw new Error('Cross-origin write');});
  expect((await POST(request(),context(['tenants',tenant,'lifecycle-subscription','preview']))).status).toBe(403);
  expect(proxy).not.toHaveBeenCalled();
  origin.mockReset();proxy.mockRejectedValue(new Error('Not platform context'));
  expect((await POST(request(),context(['tenants',tenant,'lifecycle-subscription','preview']))).status).toBe(403);
 });
});
