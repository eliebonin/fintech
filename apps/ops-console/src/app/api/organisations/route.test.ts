import {NextRequest} from "next/server";
import {describe,it,expect,vi,afterEach} from "vitest";
vi.mock("server-only",()=>({}));
vi.mock("@/lib/tenant-session",()=>({getActiveTenantContext:async()=>({tenantId:"selected-tenant",userAccountId:"selected-actor",source:"local-session"})}));
import {GET} from "./route";
afterEach(()=>vi.unstubAllGlobals());
describe("shared organisation lookup",()=>{
  it("uses the selected tenant and actor rather than legacy demo context",async()=>{
    let sent:Headers|undefined;
    vi.stubGlobal("fetch",async (_url:URL,init:RequestInit)=>{sent=new Headers(init.headers);return new Response(JSON.stringify({data:[],meta:{}}));});
    const response=await GET(new NextRequest("http://test/api/organisations?q=Bank"));
    expect(response.status).toBe(200);
    expect(sent?.get("X-Tenant-Id")).toBe("selected-tenant");
    expect(sent?.get("X-User-Account-Id")).toBe("selected-actor");
  });
});
