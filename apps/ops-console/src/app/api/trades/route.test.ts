import { NextRequest } from "next/server";
import { describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  getActiveTenantContext: vi.fn(async () => ({ tenantId: "active-tenant", userAccountId: "active-user", source: "local-session" })),
  bookListedCashTrade: vi.fn(async () => ({ data: { trade: { tradeId: "trade-1" } }, meta: {} })),
}));

vi.mock("server-only", () => ({}));
vi.mock("@/lib/tenant-session", () => ({ getActiveTenantContext: mocks.getActiveTenantContext }));
vi.mock("@/lib/reference-api-client", () => ({ bookListedCashTrade: mocks.bookListedCashTrade }));
vi.mock("@/lib/bff-error", () => ({ bffErrorResponse: vi.fn() }));

import { POST } from "./route";

describe("trade booking BFF", () => {
  it("forwards only active session context and the retry key", async () => {
    const request = new NextRequest("http://ops.test/api/trades", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": "retry-1", "X-Tenant-Id": "forged" },
      body: JSON.stringify({ listingId: "listing-1" }),
    });

    const response = await POST(request);

    expect(response.status).toBe(201);
    expect(mocks.bookListedCashTrade).toHaveBeenCalledWith(
      { listingId: "listing-1" },
      expect.objectContaining({ tenantId: "active-tenant", userAccountId: "active-user" }),
      "retry-1",
    );
  });

  it("rejects a missing idempotency key before upstream work", async () => {
    const response = await POST(new NextRequest("http://ops.test/api/trades", { method: "POST", body: "{}" }));

    expect(response.status).toBe(400);
    expect(mocks.bookListedCashTrade).toHaveBeenCalledTimes(1);
  });
});
