import {describe,it,expect,vi,afterEach} from "vitest";
import {configurationRequest} from "./trade-configuration-client";
afterEach(()=>vi.unstubAllGlobals());
describe("configuration transport",()=>{
  it('fails explicitly when history exceeds the display budget',async()=>{
    vi.stubGlobal('fetch',async()=>new Response(JSON.stringify({data:[],pagination:{limit:1000,offset:0,total:10001}})));
    await expect(configurationRequest('tenant','properties')).rejects.toThrow('no records have been silently omitted');
  });
  it('reads all bounded property pages without dropping history',async()=>{
    const fetch=vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({data:[{code:'A'},{code:'B'}],pagination:{limit:2,offset:0,total:3}}))).mockResolvedValueOnce(new Response(JSON.stringify({data:[{code:'C'}],pagination:{limit:2,offset:2,total:3}})));
    vi.stubGlobal('fetch',fetch);
    expect(await configurationRequest('tenant','properties')).toEqual([{code:'A'},{code:'B'},{code:'C'}]);
    expect(fetch.mock.calls[1][0]).toBe('/api/trade-configuration/properties?limit=2&offset=2');
  });
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
