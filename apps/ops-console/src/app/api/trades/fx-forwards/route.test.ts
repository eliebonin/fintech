import { NextRequest } from "next/server";
import { afterEach, expect, it, vi } from "vitest";
vi.mock("server-only",()=>({}));
vi.mock("@/lib/tenant-session",()=>({getActiveTenantContext:async()=>({tenantId:"tenant",userAccountId:"actor"})}));
import { POST } from "./route";
afterEach(()=>vi.unstubAllGlobals());
function request(headers:Record<string,string>={}){return new NextRequest("http://test/api/trades/fx-forwards",{method:"POST",headers,body:JSON.stringify({instrumentId:"instrument"})});}
it("requires an idempotency key",async()=>expect((await POST(request())).status).toBe(400));
it("requires the expected tenant for every FX ticket",async()=>expect((await POST(request({"Idempotency-Key":"key"}))).status).toBe(400));
it("rejects changed tenant before forwarding",async()=>expect((await POST(request({"Idempotency-Key":"key","X-Expected-Tenant-Id":"other"}))).status).toBe(409));
it("uses server session identity and preserves the key",async()=>{
 let sent:Headers|undefined;
 vi.stubGlobal("fetch",async(_url:unknown,options:RequestInit)=>{sent=new Headers(options.headers);return Response.json({data:{trade:{tradeId:"trade"}},meta:{}});});
 const response=await POST(request({"Idempotency-Key":"key","X-Expected-Tenant-Id":"tenant","X-Tenant-Id":"forged"}));
 expect(response.status).toBe(201);expect(sent?.get("X-Tenant-Id")).toBe("tenant");expect(sent?.get("X-User-Account-Id")).toBe("actor");expect(sent?.get("Idempotency-Key")).toBe("key");
});
