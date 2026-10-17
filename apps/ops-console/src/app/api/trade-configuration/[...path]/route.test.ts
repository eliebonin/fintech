import {NextRequest} from "next/server";
import {describe,it,expect,vi,afterEach} from "vitest";
vi.mock("server-only",()=>({}));
vi.mock("@/lib/tenant-session",()=>({getActiveTenantContext:async()=>({tenantId:"selected-tenant",userAccountId:"selected-actor",source:"local-session"})}));
import {GET,POST} from "./route";
const context=(path:string)=>({params:Promise.resolve({path:path.split("/")})});
afterEach(()=>vi.unstubAllGlobals());
describe("trade configuration BFF",()=>{
  it('permits paged organisation reads but never arbitrary reference mutations',async()=>{
    const fetch=vi.fn(async(_input:RequestInfo|URL)=>new Response(JSON.stringify({data:{items:[],total:0}})));vi.stubGlobal('fetch',fetch);
    const result=await GET(new NextRequest('http://test/api/trade-configuration/organisations/candidates?q=Bank&offset=25',
      {headers:{'X-Expected-Tenant-Id':'selected-tenant'}}),context('organisations/candidates'));
    expect(result.status).toBe(200);expect(result.headers.get('Cache-Control')).toBe('private, no-store');
    expect(String(fetch.mock.calls[0]?.[0])).toContain('/v1/trade-configuration/organisations/candidates?q=Bank&offset=25');
    const rejected=await POST(new NextRequest('http://test/api/trade-configuration/organisation-roles/ISSUER',
      {method:'POST',headers:{'X-Expected-Tenant-Id':'selected-tenant'},body:'{}'}),context('organisation-roles/ISSUER'));
    expect(rejected.status).toBe(404);expect(fetch).toHaveBeenCalledTimes(1);
  });
  it('preserves organisation conflict and upstream request identity',async()=>{
    vi.stubGlobal('fetch',async()=>new Response(JSON.stringify({code:'organisation.conflict',detail:'Role list changed'}),
      {status:409,headers:{'X-Request-Id':'upstream-org-request'}}));
    const path='organisations/00000000-0000-7000-8000-000000000777';
    const result=await POST(new NextRequest(`http://test/api/trade-configuration/${path}`,{
      method:'POST',headers:{'X-Expected-Tenant-Id':'selected-tenant'},body:'{}'}),context(path));
    expect(result.status).toBe(409);expect(result.headers.get('X-Request-Id')).toBe('upstream-org-request');
    expect((await result.json()).error.code).toBe('organisation.conflict');
  });
  it("rejects unknown source paths without calling an upstream",async()=>{
    const fetch=vi.fn();vi.stubGlobal("fetch",fetch);
    const result=await GET(new NextRequest("http://test/api/trade-configuration/secm/person"),context("secm/person"));
    expect(result.status).toBe(404);expect(fetch).not.toHaveBeenCalled();
  });
  it("rejects tenant switches before forwarding a mutation",async()=>{
    const fetch=vi.fn();vi.stubGlobal("fetch",fetch);
    const result=await POST(new NextRequest("http://test/api/trade-configuration/catalogues",{method:"POST",headers:{"X-Expected-Tenant-Id":"old-tenant"},body:"{}"}),context("catalogues"));
    expect(result.status).toBe(409);expect(fetch).not.toHaveBeenCalled();
  });
  it("uses the trusted actor and tenant, not browser-supplied authority",async()=>{
    let sent:Headers|undefined;
    vi.stubGlobal("fetch",async (_url:URL,init:RequestInit)=>{sent=new Headers(init.headers);return new Response(JSON.stringify({data:[]}));});
    const result=await GET(new NextRequest("http://test/api/trade-configuration/catalogues?q=Desk",{headers:{"X-Expected-Tenant-Id":"selected-tenant","X-Tenant-Id":"forged-tenant"}}),context("catalogues"));
    expect(result.status).toBe(200);expect(sent?.get("X-Tenant-Id")).toBe("selected-tenant");expect(sent?.get("X-User-Account-Id")).toBe("selected-actor");
  });
});
