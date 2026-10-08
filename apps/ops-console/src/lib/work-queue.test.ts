import { describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import { getWorkQueue } from "./work-queue";

describe("work queue client", () => {
  it('requests an explicit bounded page', async()=>{
    let url='';
    await getWorkQueue({tenantId:'tenant',userAccountId:'actor',offset:100,limit:100,
      fetchImpl:async(input)=>{url=String(input);return new Response(JSON.stringify({items:[],counts:{},meta:{}}));}});
    expect(new URL(url).searchParams.get('offset')).toBe('100');
    expect(new URL(url).searchParams.get('limit')).toBe('100');
  });
  it("calls the tenant-scoped queue endpoint", async () => {
    let requestedUrl = "";
    const fetchImpl: typeof fetch = async (input) => {
      requestedUrl = String(input);
      return new Response(JSON.stringify({
        counts: { MAPPING_REVIEW: 0, NAV_REVIEW: 0, MARKET_DATA_EXCEPTION: 0 },
        items: [],
        meta: { tenantContext: "tenant", source: "live-reference-api", apiVersion: "2026-09-01", correlationId: "corr-1" },
      }), { status: 200 });
    };

    const result = await getWorkQueue({
      baseUrl: "http://reference-api.test",
      tenantId: "00000000-0000-7000-8000-000000000011",
      userAccountId: "00000000-0000-7000-8000-000000000083",
      fetchImpl,
    });

    expect(requestedUrl).toBe("http://reference-api.test/v1/work-queue");
    expect(result.counts.MAPPING_REVIEW).toBe(0);
  });
});
