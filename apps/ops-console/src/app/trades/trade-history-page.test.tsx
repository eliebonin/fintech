import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { BookedTrade } from "@/lib/trades";

vi.mock("server-only", () => ({}));
vi.mock("next/navigation", () => ({ usePathname: () => "/trades", redirect: (href: string) => { throw new Error(`redirect:${href}`); } }));
vi.mock("@/lib/tenant-session", () => ({
  getActiveTenantContext: async () => ({ tenantId: "tenant", userAccountId: "user", source: "local-session" }),
  getActiveTenantWorkspace: async () => ({ tenantName: "Test tenant", membershipRole: "TENANT_ADMIN", moduleCodes: ["TRADING"] }),
}));
beforeEach(() => vi.setSystemTime(new Date("2026-09-30T12:00:00Z")));
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

const trade: BookedTrade = {
  tradeId: "trade-1", subjectReferenceNodeId: "listing-1", subjectName: "Example listed",
  instrumentId: "instrument-1", instrumentName: "Example ETP", instrumentType: "ETP",
  listingId: "listing-1", listingSymbol: "ETP-TEST", venueMic: "XNAS", venueName: "Nasdaq",
  strategyId: "strategy-1", strategyCode: "CUSTOM", strategyName: "Custom sleeve", tradeType: "INVESTMENT",
  tradePurpose: null, marketActivity: null, executionPrice: "10.55", lockedYtm: null,
  priceBasis: "PRICE", priceCurrency: "USD", quantity: "-150", quantityUnit: "UNIT",
  tradeDatetimeUtc: "2026-09-30T11:17:48Z", instructionDate: null, settlementDate: "2026-10-02",
  traderPersonId: null, bookedByUserAccountId: "user", executionChannel: "MANUAL_UI",
  sourceSystemId: null, sourceReceivedAtUtc: null, executionVenueId: null, dealingCapacity: null,
  lifecycleStatus: "BOOKED", referenceInstrumentId: null, comment: null,
};

function fakeApi(data: BookedTrade[] = [trade], total = 143, detailTrade:BookedTrade=trade) {
  vi.stubGlobal("fetch", async (input: URL) => {
    const payload = input.pathname === "/v1/strategies"
      ? { data: [{ strategyId: "strategy-1", strategyCode: "CUSTOM", displayName: "Custom sleeve", status: "ARCHIVED" }] }
      : input.pathname === "/v1/trades/trade-1"
        ? { data: { trade:detailTrade, parties: [], fees: [], externalReferences: [], lifecycleEvents: [] } }
        : { data, meta: { total } };
    return new Response(JSON.stringify(payload));
  });
}

describe("trade history rendered pages", () => {
  const genericTrade:BookedTrade={...trade,instrumentType:'SWAP',quantity:'-400000',quantityUnit:'NOMINAL',executionPrice:'2',settlementDate:null,productEconomics:{bookedNotional:'400000',amount:'-8000',amountKind:'ENTRY_REFERENCE_VALUE',terms:{instrumentId:'swap',name:'Swap at booking',kind:'SWAP',executionRoute:'OTC',currency:'GBP',bookingEligible:true,termsFingerprint:'b'.repeat(64),maturityDate:'2029-10-01',swapDetails:{performanceReferenceId:'ref',performanceReferenceName:'Equity at booking',performanceDirection:'RECEIVE',returnProfileCode:'TOTAL',fundingReferenceId:null,effectiveDate:'2026-09-01',sourceFacts:{},genericTerms:{schemaVersion:1,contractualNotional:'1000000',notionalCurrencyId:'gbp',effectiveDate:'2026-09-01',maturityDate:'2029-10-01',performanceDirection:'RECEIVE',performanceReferenceId:'ref',returnBasis:'TOTAL',returnProfileId:'total',leverage:'2',financingTreatment:'NONE',performanceResetFrequency:'CUSTOM',performanceScheduleDescription:'Historical reset rule',redemptionRule:'CONTINUE',continuationDescription:'Historical proceeds rule',quoteCurrencyId:'gbp',quoteFactor:'100',sourceReference:'Historical confirmation',additionalFundingAcknowledged:false}}}}};
  it('renders both generic notionals and whole-swap entry value from the booked snapshot',async()=>{
    const {DetailContent}=await import('./[tradeId]/page');
    const html=renderToStaticMarkup(<DetailContent detail={{trade:genericTrade,parties:[],fees:[],externalReferences:[],lifecycleEvents:[]}}/>);
    for(const value of ['Booked nominal','400,000 GBP','Contractual notional','1000000 GBP','Equity at booking','Historical reset rule','Historical proceeds rule','Historical confirmation','No separate funding leg','-8,000 GBP','not independently verified MTM'])expect(html).toContain(value);
    expect(html).not.toContain('Funding spread (decimal)');expect(html).not.toContain('Canonical funding direction');
  },15000);
  it('uses the generic snapshot identity throughout details even when current master names conflict',async()=>{
    const current={...genericTrade,instrumentName:'CURRENT instrument name',subjectName:'CURRENT subject name'};
    const {DetailContent,default:Page}=await import('./[tradeId]/page');
    const detailHtml=renderToStaticMarkup(<DetailContent detail={{trade:current,parties:[],fees:[],externalReferences:[],lifecycleEvents:[]}}/>);
    fakeApi([current],1,current);const pageHtml=renderToStaticMarkup(await Page({params:Promise.resolve({tradeId:'trade-1'}),searchParams:Promise.resolve({})}));
    expect(detailHtml).toContain('<h2>Swap at booking</h2>');expect(detailHtml).not.toContain('CURRENT');expect(pageHtml).toContain('<h1>Swap at booking</h1>');expect(pageHtml).not.toContain('CURRENT');
  },15000);
  it('shows both generic nominal amounts and labels the immutable entry value in history',async()=>{
    fakeApi([{...genericTrade,quantity:'-500000'}]);const {default:Page}=await import('./page');const html=renderToStaticMarkup(await Page({searchParams:Promise.resolve({range:'all'})}));
    for(const value of ['Swap at booking','<strong>400,000</strong>','Booked nominal','Contractual notional','1,000,000 GBP','SWAP_VALUE_PER_NOTIONAL · GBP','Entry reference value','-8,000 GBP'])expect(html).toContain(value);
  });
  it("renders FX booking-snapshot obligations and full rate precision",async()=>{
    const {DetailContent}=await import("./[tradeId]/page");
    const fx={baseCurrency:"EUR",quoteCurrency:"USD",quoteConvention:"USD_PER_EUR",agreedRate:"1.123456789012",settlementDate:"2026-12-15",receiveCurrency:"EUR",receiveAmount:"0.000001",payCurrency:"USD",payAmount:"0.000001123456789012",termsFingerprint:"a".repeat(64),source:"BOOKING_SNAPSHOT" as const};
    const html=renderToStaticMarkup(<DetailContent detail={{trade:{...trade,instrumentType:"FX_FORWARD",listingId:null,listingSymbol:null,venueMic:null,venueName:null,quantity:"0.000001",executionPrice:"1.123456789012",fxForwardEconomics:fx},parties:[],fees:[],externalReferences:[],lifecycleEvents:[]}}/>);
    expect(html).toContain("0.000001123456789012 USD");expect(html).toContain("1.123456789012 USD_PER_EUR");expect(html).toContain("booking snapshot");expect(html).toContain("OTC");
  },15000);
  it.each([[404,"NOT FOUND"],[403,"ACCESS DENIED"],[503,"API UNAVAILABLE"]])("labels a %s detail response as %s", async (status,label) => {
    vi.stubGlobal("fetch", async () => new Response("failure", {status}));
    const { default: Page } = await import("./[tradeId]/page");
    const html=renderToStaticMarkup(await Page({params:Promise.resolve({tradeId:"missing"}),searchParams:Promise.resolve({})}));
    expect(html).toContain(label);
    if(status<500)expect(html).not.toContain("API UNAVAILABLE");
  },15000);
  it("renders historical property types with false, exact decimals and named trader", async () => {
    const { DetailContent } = await import("./[tradeId]/page");
    const html=renderToStaticMarkup(<DetailContent detail={{trade,parties:[],fees:[],externalReferences:[],lifecycleEvents:[],traderName:"Responsible trader",tags:[{tagId:"tag",code:"OLD",label:"Historical tag"}],properties:[
      {definitionId:"flag",code:"FLAG",label:"Internal cross",valueType:"BOOLEAN",required:false,choices:[],description:null,value:false},
      {definitionId:"decimal",code:"WEIGHT",label:"Weight",valueType:"DECIMAL",required:false,choices:[],description:null,value:"0.123456789012"},
      {definitionId:"zero",code:"ZERO",label:"Zero",valueType:"DECIMAL",required:false,choices:[],description:null,value:"0"}
    ]}}/>);
    expect(html).toContain("Internal cross (BOOLEAN)");
    expect(html).toContain("<strong>No</strong>");
    expect(html).toContain("<strong>0</strong>");
    expect(html).toContain("0.123456789012");
    expect(html).toContain("Historical tag");
    expect(html).toContain("Responsible trader");
  });
  it("forwards default UTC bounds but leaves all-history reads unbounded", async () => {
    const requests: URL[] = [];
    vi.stubGlobal("fetch", async (input: URL) => {
      requests.push(input);
      return new Response(JSON.stringify({ data: [], meta: { total: 0 } }));
    });
    const { default: Page } = await import("./page");
    await Page({ searchParams: Promise.resolve({}) });
    const recent = requests.find((url) => url.pathname === "/v1/trades")!;
    expect(recent.searchParams.get("fromDate")).toBe("2026-09-17");
    expect(recent.searchParams.get("toDate")).toBe("2026-09-30");
    requests.length = 0;
    await Page({ searchParams: Promise.resolve({ range: "all" }) });
    const all = requests.find((url) => url.pathname === "/v1/trades")!;
    expect(all.searchParams.has("fromDate")).toBe(false);
    expect(all.searchParams.has("toDate")).toBe(false);
  });
  it("shows real strategy choices, sell side, totals and filter-preserving links", async () => {
    fakeApi();
    const { default: Page } = await import("./page");
    const html = renderToStaticMarkup(await Page({ searchParams: Promise.resolve({ q: "ETP", page: "2" }) }));
    expect(html).toContain("Trade history</h1>");
    expect(html).toContain("Custom sleeve (archived)");
    expect(html).toContain("SELL");
    expect(html).toContain("26–50 of 143");
    expect(html).toContain("returnTo=%2Ftrades%3Fq%3DETP");
    expect(html).toContain('scope="col"');
  });
  it("shows a clear-filters action for no matches", async () => {
    fakeApi([], 0);
    const { default: Page } = await import("./page");
    const html = renderToStaticMarkup(await Page({ searchParams: Promise.resolve({ q: "missing" }) }));
    expect(html).toContain("No trades match these filters.");
    expect(html).toContain("Clear filters");
  });
  it("distinguishes an empty tenant history from no matching trades", async () => {
    fakeApi([], 0);
    const { default: Page } = await import("./page");
    const html = renderToStaticMarkup(await Page({ searchParams: Promise.resolve({ range: "all" }) }));
    expect(html).toContain("No trades have been recorded for this tenant.");
    expect(html).toContain("Book your first trade");
  });
  it("redirects an out-of-range page to the last valid page with filters", async () => {
    fakeApi([], 1);
    const { default: Page } = await import("./page");
    await expect(Page({ searchParams: Promise.resolve({ q: "ETP", page: "999", range: "all" }) })).rejects.toThrow("redirect:/trades?q=ETP&range=all&pageSize=25&page=1");
  });
  it("shows API failure with retry instead of claiming history is empty", async () => {
    vi.stubGlobal("fetch", async () => new Response("unavailable", { status: 503 }));
    const { default: Page } = await import("./page");
    const html = renderToStaticMarkup(await Page({ searchParams: Promise.resolve({}) }));
    expect(html).toContain("trade history service is unavailable");
    expect(html).toContain("Retry");
    expect(html).not.toContain("No trades have been recorded");
  });
  it("preserves the originating search/page in the details back link", async () => {
    fakeApi();
    const { default: Page } = await import("./[tradeId]/page");
    const html = renderToStaticMarkup(await Page({ params: Promise.resolve({ tradeId: "trade-1" }), searchParams: Promise.resolve({ returnTo: "/trades?q=ETP&range=all&page=2" }) }));
    expect(html).toContain('href="/trades?q=ETP&amp;range=all&amp;pageSize=25&amp;page=2"');
  });
  it("remounts uncontrolled filter and page controls when URL state changes", async () => {
    fakeApi();
    const { default: Page } = await import("./page");
    const filtered = await Page({ searchParams: Promise.resolve({ side: "SELL", page: "2", pageSize: "50" }) });
    const cleared = await Page({ searchParams: Promise.resolve({}) });
    function formKeys(node: React.ReactNode): (string | null)[] {
      if (!React.isValidElement<{ children?: React.ReactNode }>(node)) return [];
      return [
        ...(node.type === "form" ? [node.key] : []),
        ...React.Children.toArray(node.props.children).flatMap(formKeys),
      ];
    }
    const before = formKeys(filtered);
    const after = formKeys(cleared);
    expect(before).toHaveLength(2);
    expect(before.every((key) => key !== null)).toBe(true);
    expect(before[0]).not.toBe(after[0]);
    expect(before[1]).not.toBe(after[1]);
  });
  it("explains the default empty range and offers all history", async () => {
    fakeApi([], 0);
    const { default: Page } = await import("./page");
    const html = renderToStaticMarkup(await Page({ searchParams: Promise.resolve({}) }));
    expect(html).toContain("No trades in the last 14 days.");
    expect(html).toContain("View all history");
    expect(html).toContain("2026-09-17");
    expect(html).toContain("Last 30 days");
  });
});
