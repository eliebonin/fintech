import {describe,it,expect,vi,afterEach} from "vitest";
import {configurationRequest} from "./trade-configuration-client";
afterEach(()=>vi.unstubAllGlobals());
describe("configuration transport",()=>{
  it("pins reads and writes to the page tenant",async()=>{
    const fetch=vi.fn(async()=>new Response(JSON.stringify({data:{catalogueId:"catalogue"}})));vi.stubGlobal("fetch",fetch);
    await configurationRequest("tenant","catalogues",{label:"Rationale"});
    expect(fetch).toHaveBeenCalledWith("/api/trade-configuration/catalogues",expect.objectContaining({method:"POST",headers:expect.objectContaining({"X-Expected-Tenant-Id":"tenant"}),body:JSON.stringify({label:"Rationale"})}));
  });
  it("surfaces stale or denied configuration instead of swallowing it",async()=>{
    vi.stubGlobal("fetch",async()=>new Response(JSON.stringify({error:{message:"Reload this page."}}),{status:409}));
    await expect(configurationRequest("tenant","properties")).rejects.toThrow("Reload this page.");
  });
});
