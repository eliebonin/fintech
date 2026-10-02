import React from "react";
import {renderToStaticMarkup} from "react-dom/server";
import {expect,it,vi,afterEach} from "vitest";
vi.mock("server-only",()=>({}));
vi.mock("next/navigation",()=>({usePathname:()=>"/pnl/uk"}));
afterEach(()=>vi.unstubAllGlobals());
it("presents unsupported FX valuation as a domain boundary, without total or outage",async()=>{
  vi.stubGlobal("fetch",async()=>Response.json({code:"valuation.fx_forward_unsupported",detail:"unsupported"},{status:422}));
  const {default:Page}=await import("./[portfolio]/page");
  const html=renderToStaticMarkup(await Page({params:Promise.resolve({portfolio:"uk"}),searchParams:Promise.resolve({asOfDate:"2026-10-01"})}));
  expect(html).toContain("VALUATION UNSUPPORTED");expect(html).toContain("FX-forward valuation is not supported yet");expect(html).not.toContain("Total P&amp;L");expect(html).not.toContain("API UNAVAILABLE");
},15000);
