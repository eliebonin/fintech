import { describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import { listDayCountConventions, listDayCountConventionsFromBff, searchReferenceInstruments, searchReferenceNodes, submitBondProposal, submitCryptoAssetProposal } from "./reference-api-client";

describe("reference API client", () => {
  it("builds a tenant-scoped search request and preserves the view contract", async () => {
    let requestedUrl = "";
    let requestedHeaders: HeadersInit | undefined;
    const fetchImpl: typeof fetch = async (input, init) => {
      requestedUrl = String(input);
      requestedHeaders = init?.headers;
      return new Response(JSON.stringify({
        data: [],
        meta: { tenantContext: "tenant", source: "live-reference-api", apiVersion: "2026-09-01", correlationId: "corr-1" },
      }), { status: 200, headers: { "content-type": "application/json" } });
    };

    const result = await searchReferenceInstruments("HSBC", {
      baseUrl: "http://reference-api.test",
      tenantId: "00000000-0000-7000-8000-000000000011",
      userAccountId: "00000000-0000-7000-8000-000000000083",
      fetchImpl,
    });

    expect(requestedUrl).toBe("http://reference-api.test/v1/instruments/search?q=HSBC&limit=50&offset=0");
    expect(new Headers(requestedHeaders).get("X-Tenant-Id")).toBe("00000000-0000-7000-8000-000000000011");
    expect(new Headers(requestedHeaders).get("X-User-Account-Id")).toBe("00000000-0000-7000-8000-000000000083");
    expect(result.meta.source).toBe("live-reference-api");
  });

  it("raises a typed error for non-success API responses", async () => {
    const fetchImpl: typeof fetch = async () => new Response(JSON.stringify({ detail: "Tenant context is required" }), { status: 401 });

    await expect(searchReferenceInstruments("HSBC", {
      baseUrl: "http://reference-api.test",
      tenantId: "tenant",
      userAccountId: "user",
      fetchImpl,
    })).rejects.toMatchObject({ status: 401 });
  });

  it("preserves safe Problem Details fields without exposing unknown upstream bodies", async () => {
    const problemFetch: typeof fetch = async () => new Response(JSON.stringify({
      type: "https://api.fortem.local/problems/request-conflict",
      title: "Conflict",
      status: 409,
      detail: "The request conflicts with the current resource state.",
      instance: "/v1/instruments/search",
      code: "request.conflict",
      requestId: "00000000-0000-4000-8000-000000000001",
    }), { status: 409, headers: { "content-type": "application/problem+json" } });

    await expect(searchReferenceInstruments("HSBC", {
      baseUrl: "http://reference-api.test",
      tenantId: "tenant",
      userAccountId: "user",
      fetchImpl: problemFetch,
    })).rejects.toMatchObject({ status: 409, code: "request.conflict", requestId: "00000000-0000-4000-8000-000000000001" });

    const unknownFetch: typeof fetch = async () => new Response(JSON.stringify({ detail: "upstream-secret" }), { status: 502 });
    await expect(searchReferenceInstruments("HSBC", {
      baseUrl: "http://reference-api.test",
      tenantId: "tenant",
      userAccountId: "user",
      fetchImpl: unknownFetch,
    })).rejects.toThrow("Reference API returned HTTP 502");
  });

  it("builds a reference-node search for non-instrument underlyings", async () => {
    let requestedUrl = "";
    const fetchImpl: typeof fetch = async (input) => {
      requestedUrl = String(input);
      return new Response(JSON.stringify({
        data: [{ referenceNodeId: "index-1", canonicalName: "Demo index", nodeType: "INDEX", status: "ACTIVE", isTradable: false }],
        meta: { tenantContext: "tenant", source: "live-reference-api", apiVersion: "2026-09-01", correlationId: "corr-1" },
      }), { status: 200 });
    };

    const result = await searchReferenceNodes("", {
      baseUrl: "http://reference-api.test",
      tenantId: "tenant",
      userAccountId: "user",
      nodeType: ["INDEX", "FX_PAIR"],
      instrumentType: "DIGITAL_ASSET",
      fetchImpl,
    });

    expect(requestedUrl).toBe("http://reference-api.test/v1/reference-nodes/search?q=&limit=50&offset=0&node_type=INDEX%2CFX_PAIR&instrument_type=DIGITAL_ASSET");
    expect(result.data[0].nodeType).toBe("INDEX");
  });

  it("builds a reference-node search with an explicit reference level", async () => {
    let requestedUrl = "";
    const fetchImpl: typeof fetch = async (input) => {
      requestedUrl = String(input);
      return new Response(JSON.stringify({
        data: [{ referenceNodeId: "listing-1", canonicalName: "Demo listing", nodeType: "LISTING", instrumentType: "EQUITY", status: "ACTIVE", isTradable: true }],
        meta: { tenantContext: "tenant", source: "live-reference-api", apiVersion: "2026-09-01", correlationId: "corr-1" },
      }), { status: 200 });
    };

    const result = await searchReferenceNodes("HSBC", {
      baseUrl: "http://reference-api.test",
      tenantId: "tenant",
      userAccountId: "user",
      instrumentType: "EQUITY",
      referenceLevel: "LISTING",
      fetchImpl,
    });

    expect(requestedUrl).toBe("http://reference-api.test/v1/reference-nodes/search?q=HSBC&limit=50&offset=0&instrument_type=EQUITY&reference_level=LISTING");
    expect(result.data[0].nodeType).toBe("LISTING");
  });

  it("submits a sparse bond proposal to the tenant-scoped endpoint", async () => {
    let requestedUrl = "";
    const fetchImpl: typeof fetch = async (input) => {
      requestedUrl = String(input);
      return new Response(JSON.stringify({
        data: { proposalId: "proposal-1", status: "PENDING", proposalType: "CREATE_BOND", submissionMode: "MANUAL", couponType: "ZERO", enrichmentStatus: "PENDING_ENRICHMENT", proposedAt: "2026-09-03T00:00:00Z" },
        meta: { tenantContext: "tenant", source: "live-reference-api", apiVersion: "2026-09-01", correlationId: "corr-1" },
      }), { status: 201 });
    };

    const result = await submitBondProposal({ canonicalName: "Sparse note", effectiveFrom: "2026-09-03", couponType: "ZERO" }, {
      baseUrl: "http://reference-api.test",
      tenantId: "tenant",
      userAccountId: "user",
      fetchImpl,
    });

    expect(requestedUrl).toBe("http://reference-api.test/v1/bond-proposals");
    expect(result.data.enrichmentStatus).toBe("PENDING_ENRICHMENT");
  });

  it("submits a cryptoasset proposal to the upstream reference API", async () => {
    let requestedUrl = "";
    let requestedHeaders: HeadersInit | undefined;
    const fetchImpl: typeof fetch = async (input, init) => {
      requestedUrl = String(input);
      requestedHeaders = init?.headers;
      return new Response(JSON.stringify({
        data: { proposalId: "proposal-crypto-1", status: "PENDING", proposalType: "CREATE_CRYPTO_ASSET", submissionMode: "MANUAL", canonicalName: "Test Ethereum", effectiveFrom: "2026-09-07", assetSubtype: "NATIVE", nativeSymbol: "TSTETH", proposedAt: "2026-09-07T00:00:00Z" },
        meta: { tenantContext: "tenant", source: "live-reference-api", apiVersion: "2026-09-01", correlationId: "corr-1" },
      }), { status: 201 });
    };

    const result = await submitCryptoAssetProposal({ canonicalName: "Test Ethereum", assetSubtype: "NATIVE", nativeSymbol: "TSTETH" }, {
      baseUrl: "http://reference-api.test",
      tenantId: "tenant",
      userAccountId: "user",
      fetchImpl,
    });

    expect(requestedUrl).toBe("http://reference-api.test/v1/crypto-asset-proposals");
    expect(new Headers(requestedHeaders).get("X-Tenant-Id")).toBe("tenant");
    expect(result.data.proposalId).toBe("proposal-crypto-1");
  });

  it("loads governed day-count conventions for the bond form", async () => {
    let requestedUrl = "";
    const fetchImpl: typeof fetch = async (input) => {
      requestedUrl = String(input);
      return new Response(JSON.stringify({
        data: [{ dayCountConventionId: "convention-1", code: "ACT_ACT_ICMA", displayName: "Actual/Actual ICMA", description: "Coupon period basis", standardSource: "ICMA" }],
        meta: { tenantContext: "tenant", source: "live-reference-api", apiVersion: "2026-09-01", correlationId: "corr-1", total: 1 },
      }), { status: 200 });
    };

    const result = await listDayCountConventions({ baseUrl: "http://reference-api.test", tenantId: "tenant", userAccountId: "user", fetchImpl });

    expect(requestedUrl).toBe("http://reference-api.test/v1/day-count-conventions");
    expect(result.data[0].code).toBe("ACT_ACT_ICMA");
  });

  it("loads day-count conventions through the browser BFF route", async () => {
    let requestedUrl = "";
    const fetchImpl: typeof fetch = async (input) => {
      requestedUrl = String(input);
      return new Response(JSON.stringify({ data: [], meta: {} }), { status: 200 });
    };

    await listDayCountConventionsFromBff(fetchImpl);

    expect(requestedUrl).toBe("/api/day-count-conventions");
  });

  it("posts cryptoasset decisions to the tenant-scoped reference API", async () => {
    const client = await import("./reference-api-client");
    expect(typeof client.decideCryptoAssetProposal).toBe("function");
    if (typeof client.decideCryptoAssetProposal !== "function") return;

    let requestedUrl = "";
    let requestedBody = "";
    const fetchImpl: typeof fetch = async (input, init) => {
      requestedUrl = String(input);
      requestedBody = String(init?.body ?? "");
      return new Response(JSON.stringify({
        data: {
          proposalId: "proposal-1",
          status: "APPROVED",
          proposalType: "CREATE_CRYPTO_ASSET",
          submissionMode: "MANUAL",
          canonicalName: "Test Bitcoin",
          effectiveFrom: "2026-09-07",
          assetSubtype: "NATIVE",
          nativeSymbol: "TSTBTC",
          instrumentId: "instrument-1",
          currencyId: "currency-1",
          proposedAt: "2026-09-07T00:00:00Z",
        },
        meta: {},
      }), { status: 200 });
    };

    const result = await client.decideCryptoAssetProposal("proposal-1", { decision: "APPROVED", reason: "Validated" }, {
      baseUrl: "http://reference-api.test",
      tenantId: "tenant",
      userAccountId: "user",
      fetchImpl,
    });

    expect(requestedUrl).toBe("http://reference-api.test/v1/crypto-asset-proposals/proposal-1/decision");
    expect(JSON.parse(requestedBody)).toEqual({ decision: "APPROVED", reason: "Validated" });
    expect(result.data.status).toBe("APPROVED");
  });

});
