import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));
afterEach(() => vi.unstubAllGlobals());

describe("trade history client", () => {
  it("forwards filters and pagination to the tenant-scoped API", async () => {
    const { getBookedTrades } = await import("./mvp-api-client");
    let requested: URL | undefined;
    vi.stubGlobal("fetch", async (input: URL) => {
      requested = input;
      return new Response(JSON.stringify({ data: [], meta: { total: 143 } }));
    });
    const result = await getBookedTrades({ tenantId: "tenant", userAccountId: "user", source: "local-session" }, {
      q: "ETP", side: "SELL", lifecycleStatus: "BOOKED", portfolioCode: "CUSTOM",
      limit: 25, offset: 50,
    });
    expect(requested?.searchParams.get("q")).toBe("ETP");
    expect(requested?.searchParams.get("side")).toBe("SELL");
    expect(requested?.searchParams.get("lifecycleStatus")).toBe("BOOKED");
    expect(requested?.searchParams.get("portfolioCode")).toBe("CUSTOM");
    expect(requested?.searchParams.get("offset")).toBe("50");
    expect(result.meta.total).toBe(143);
  });
});

describe("live instrument detail client", () => {
  it("loads a canonical instrument with tenant context", async () => {
    const { getInstrument } = await import("./mvp-api-client");
    const previousBaseUrl = process.env.REFERENCE_API_URL;
    process.env.REFERENCE_API_URL = "http://reference-api.test";
    let requestedUrl = "";
    let requestedHeaders: HeadersInit | undefined;
    const fetchImpl: typeof fetch = async (input, init) => {
      requestedUrl = String(input);
      requestedHeaders = init?.headers;
      return new Response(JSON.stringify({
        data: { instrumentId: "instrument-1", canonicalName: "Example" },
        meta: { correlationId: "corr-1" },
      }), { status: 200 });
    };

    const result = await getInstrument({ tenantId: "tenant", userAccountId: "user", source: "local-session" }, "instrument-1", fetchImpl);
    if (previousBaseUrl === undefined) delete process.env.REFERENCE_API_URL;
    else process.env.REFERENCE_API_URL = previousBaseUrl;

    expect(requestedUrl).toBe("http://reference-api.test/v1/instruments/instrument-1");
    expect(new Headers(requestedHeaders).get("X-Tenant-Id")).toBe("tenant");
    expect(new Headers(requestedHeaders).get("X-User-Account-Id")).toBe("user");
    expect(result.data.instrumentId).toBe("instrument-1");
  });
});
