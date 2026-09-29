import "server-only";

import { cookies } from "next/headers";

import type { TenantContext } from "./tenant-types";

export type ActiveTenantWorkspace = {
  tenantId: string;
  tenantCode: string;
  tenantName: string;
  membershipRole: string;
  moduleCodes: string[];
};

export async function selectActiveTenant(tenantId: string): Promise<ActiveTenantWorkspace> {
  if (!tenantId) throw new Error("Tenant selection is required");
  const response = await fetch(new URL("/v1/session/memberships", process.env.REFERENCE_API_URL ?? "http://localhost:8000"), {
    headers: { "X-User-Account-Id": process.env.DEMO_USER_ACCOUNT_ID ?? "00000000-0000-7000-8000-000000000083" },
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Tenant memberships are unavailable");
  const payload = (await response.json()) as { data: Array<{ tenantId: string; tenantCode: string; tenantName: string; membershipRole: string }> };
  const membership = payload.data.find((item) => item.tenantId === tenantId);
  if (!membership) throw new Error("Selected tenant is not an active membership");
  return { ...membership, moduleCodes: [] };
}

export async function getActiveTenantContext(): Promise<TenantContext> {
  const tenantId = (await cookies()).get("active_tenant")?.value;
  if (!tenantId) throw new Error("No active tenant has been selected");
  return {
    tenantId,
    userAccountId: process.env.DEMO_USER_ACCOUNT_ID ?? "00000000-0000-7000-8000-000000000083",
    source: "local-session",
  };
}
