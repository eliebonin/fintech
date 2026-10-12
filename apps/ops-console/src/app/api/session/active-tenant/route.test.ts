import { WorkspaceApiError } from "@/lib/server/workspace-errors";
import { NextRequest } from "next/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));
vi.mock("@/lib/tenant-session", () => ({ selectActiveTenant: vi.fn(async (tenantId: string) => ({ tenantId, tenantCode: "DEMO", tenantName: "Demo", membershipRole: "TENANT_ADMIN", moduleCodes: ["TRADING"] })), signActiveTenantId: vi.fn((tenantId: string) => `${tenantId}.signature`) }));

import { selectActiveTenant } from "@/lib/tenant-session";
import { POST } from "./route";

describe("active tenant BFF route", () => {
  it("accepts a tenant selection only through the server session helper", async () => {
    const response = await POST(new NextRequest("http://ops.test/api/session/active-tenant", { method: "POST", body: JSON.stringify({ tenantId: "tenant-permitted" }) }));
    expect(response.status).toBe(200);
    expect(response.headers.get("set-cookie")).toContain("active_tenant=tenant-permitted.signature");
    expect(response.headers.get("X-Tenant-Context-Changed")).toBe("1");
    await expect(response.json()).resolves.toMatchObject({ tenantId: "tenant-permitted", tenantCode: "DEMO" });
  });

  it("does not set an active-tenant cookie for a tenant outside the membership list", async () => {
    vi.mocked(selectActiveTenant).mockRejectedValueOnce(new WorkspaceApiError(403));
    const response = await POST(new NextRequest("http://ops.test/api/session/active-tenant", { method: "POST", body: JSON.stringify({ tenantId: "tenant-foreign" }) }));
    expect(response.status).toBe(403);
    expect(response.headers.get("set-cookie")).toBeNull();
  });
});
