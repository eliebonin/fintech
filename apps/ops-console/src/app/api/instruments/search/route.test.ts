import { NextRequest } from "next/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));
vi.mock("@/lib/tenant-session", () => ({ getActiveTenantContext: vi.fn(async () => ({ tenantId: "active-tenant", userAccountId: "active-user", source: "local-session" })) }));
vi.mock("@/lib/reference-api-client", () => ({ searchReferenceInstruments: vi.fn(async () => ({ data: [], meta: { source: "live-reference-api" } })) }));
vi.mock("@/lib/instrument-data", () => ({ searchInstruments: vi.fn(() => []) }));
vi.mock("@/lib/bff-error", () => ({ bffErrorResponse: vi.fn() }));

import { searchReferenceInstruments } from "@/lib/reference-api-client";
import { GET } from "./route";

describe("instrument search BFF", () => {
  it("uses the active tenant session rather than the legacy demo context", async () => {
    const response = await GET(new NextRequest("http://ops.test/api/instruments/search?q=HSBC"));

    expect(response.status).toBe(200);
    expect(searchReferenceInstruments).toHaveBeenCalledWith("HSBC", expect.objectContaining({ tenantId: "active-tenant", userAccountId: "active-user" }));
  });

  it("forwards pagination controls to the tenant-scoped catalogue search", async () => {
    await GET(new NextRequest("http://ops.test/api/instruments/search?q=HSBC&status=ACTIVE&limit=25&offset=50"));

    expect(searchReferenceInstruments).toHaveBeenCalledWith("HSBC", expect.objectContaining({ status: "ACTIVE", limit: 25, offset: 50 }));
  });
});
