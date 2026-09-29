import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { mockGet, mockPost } = vi.hoisted(() => ({ mockGet: vi.fn(), mockPost: vi.fn() }));

vi.mock("server-only", () => ({}));
vi.mock("api-contracts", () => ({ createReferenceApiClient: vi.fn(() => ({ GET: mockGet, POST: mockPost })) }));
vi.mock("@/lib/tenant-context", () => ({ resolveLocalTenantContext: () => ({ tenantId: "tenant-server", userAccountId: "user-server", source: "local-session" }) }));

import { POST } from "./resolution-snapshots/route";
import { GET } from "./valuation-policies/route";

describe("market-data BFF routes", () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
  });

  it("requires a valuation date before querying active policies", async () => {
    const response = await GET(new NextRequest("http://ops.test/api/market-data/valuation-policies"));

    expect(response.status).toBe(400);
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("passes the selected valuation date to the typed upstream policy route", async () => {
    mockGet.mockResolvedValue({ data: [{ valuationPolicyId: "policy-1", valuationCutId: "cut-1" }], response: new Response(null, { status: 200 }) });

    const response = await GET(new NextRequest("http://ops.test/api/market-data/valuation-policies?valuationDate=2026-08-28"));

    expect(mockGet).toHaveBeenCalledWith("/v1/market-data/valuation-policies", { params: { query: { valuationDate: "2026-08-28" } } });
    await expect(response.json()).resolves.toEqual([{ valuationPolicyId: "policy-1", valuationCutId: "cut-1" }]);
  });

  it("creates snapshot commands with a server-generated idempotency key", async () => {
    mockPost.mockResolvedValue({ data: { marketDataResolutionSnapshotId: "snapshot-1" }, response: new Response(null, { status: 201, headers: { Location: "/v1/market-data-resolution-snapshots/snapshot-1" } }) });
    const body = { valuationPolicyId: "policy-1", valuationDate: "2026-08-28", valuationCutId: "cut-1", marketDataAsOfUtc: "2026-08-28T16:00:00Z", subjectReferenceNodeIds: ["node-1"], usePurpose: "VALUATION" };

    const response = await POST(new NextRequest("http://ops.test/api/market-data/resolution-snapshots", { method: "POST", body: JSON.stringify(body) }));

    expect(mockPost).toHaveBeenCalledWith("/v1/market-data-resolution-snapshots", expect.objectContaining({ body, params: { header: { "Idempotency-Key": expect.any(String) } } }));
    expect(response.status).toBe(201);
  });
});
