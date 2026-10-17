import {afterEach,expect,it,vi} from 'vitest';
import {NextRequest} from 'next/server';
const proxy=vi.hoisted(()=>vi.fn());
vi.mock('@/lib/server/access-proxy',()=>({accessProxy:proxy}));
import {GET} from './route';
afterEach(()=>vi.resetAllMocks());
it('forwards only the inspection target; identity remains server-derived',async()=>{
 proxy.mockResolvedValue(Response.json({userId:'selected'}));
 const result=await GET(new NextRequest('http://localhost/api/effective-access?userId=selected&tenantId=foreign'));
 expect(proxy).toHaveBeenCalledWith('/v1/tenant-workspace/effective-access?userId=selected');
 expect(result.status).toBe(200);
 expect(result.headers.get('cache-control')).toBe('no-store');
});
it('does not expose stale member details after upstream denial',async()=>{
 proxy.mockResolvedValue(Response.json({error:{message:'Access denied'}},{status:403}));
 const result=await GET(new NextRequest('http://localhost/api/effective-access'));
 expect(result.status).toBe(403);
 expect(await result.json()).toEqual({error:{message:'Access denied'}});
});
