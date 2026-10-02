import {NextRequest} from "next/server";
import {describe,it,expect,vi,afterEach} from "vitest";
vi.mock("server-only",()=>({}));
vi.mock("@/lib/tenant-session",()=>({getActiveTenantContext:async()=>({tenantId:"selected-tenant",userAccountId:"selected-actor",source:"local-session"})}));
import {GET,POST} from "./route";
const context=(path:string)=>({params:Promise.resolve({path:path.split("/")})});
afterEach(()=>vi.unstubAllGlobals());
describe("trade configuration BFF",()=>{
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
