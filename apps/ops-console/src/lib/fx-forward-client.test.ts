import {expect,it} from "vitest";
import {searchFxForwardBookingInstrumentsFromBff,submitFxForwardTradeFromBff} from "./browser-api-client";
it("forwards the next search page with escaped query",async()=>{
  let url="";const impl:typeof fetch=async(input)=>{url=String(input);return Response.json({data:[],meta:{total:35}});};
  await searchFxForwardBookingInstrumentsFromBff("EUR/USD & December",impl,25);
  const query=new URL(url,"http://test").searchParams;expect(query.get("q")).toBe("EUR/USD & December");expect(query.get("offset")).toBe("25");expect(query.get("limit")).toBe("25");
});
it("requires the frozen tenant/key on FX submission",async()=>{
  let headers:Headers|undefined;const impl:typeof fetch=async(_,init)=>{headers=new Headers(init?.headers);return Response.json({data:{trade:{tradeId:"trade"}}});};
  await submitFxForwardTradeFromBff({instrumentId:"instrument",strategyId:"strategy",side:"BUY",tradePurpose:"HEDGING",quantity:"1",tradeDatetime:"2026-10-01T10:00:00Z",counterpartyOrganisationId:"bank",expectedTermsFingerprint:"a".repeat(64)},"original-key","original-tenant",impl);
  expect(headers?.get("Idempotency-Key")).toBe("original-key");expect(headers?.get("X-Expected-Tenant-Id")).toBe("original-tenant");
});
