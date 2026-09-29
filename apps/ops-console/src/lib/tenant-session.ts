import "server-only";

import { createHmac, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";

import type { TenantContext } from "./tenant-types";

export type ActiveTenantWorkspace = {
  tenantId: string;
  tenantCode: string;
  tenantName: string;
  membershipRole: string;
  moduleCodes: string[];
  platformRole?: string | null;
};

const DEV_COOKIE_SECRET = "development-only-active-tenant-secret";

function tenantCookieSecret(): string {
  const configured = process.env.ACTIVE_TENANT_COOKIE_SECRET;
  if (configured) return configured;
  if (process.env.NODE_ENV !== "production") return DEV_COOKIE_SECRET;
  throw new Error("ACTIVE_TENANT_COOKIE_SECRET must be configured in production");
}

export function signActiveTenantId(tenantId: string): string {
  const signature = createHmac("sha256", tenantCookieSecret()).update(tenantId).digest("base64url");
  return `${tenantId}.${signature}`;
}

function readSignedActiveTenantId(value: string): string | null {
  const separator = value.lastIndexOf(".");
  if (separator < 1) return null;
  const tenantId = value.slice(0, separator);
  const expected = signActiveTenantId(tenantId);
  const actualBuffer = Buffer.from(value);
  const expectedBuffer = Buffer.from(expected);
  return actualBuffer.length === expectedBuffer.length && timingSafeEqual(actualBuffer, expectedBuffer) ? tenantId : null;
}

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
  const workspaceResponse = await fetch(new URL("/v1/tenant-workspace", process.env.REFERENCE_API_URL ?? "http://localhost:8000"), {
    headers: {
      "X-Tenant-Id": membership.tenantId,
      "X-User-Account-Id": process.env.DEMO_USER_ACCOUNT_ID ?? "00000000-0000-7000-8000-000000000083",
    },
    cache: "no-store",
  });
  if (!workspaceResponse.ok) throw new Error("Tenant workspace is unavailable");
  const workspace = (await workspaceResponse.json()) as { data: ActiveTenantWorkspace };
  return workspace.data;
}

export async function getActiveTenantContext(): Promise<TenantContext> {
  const rawTenantId = (await cookies()).get("active_tenant")?.value;
  const tenantId = rawTenantId ? readSignedActiveTenantId(rawTenantId) : null;
  if (!tenantId) throw new Error("No active tenant has been selected");
  return {
    tenantId,
    userAccountId: process.env.DEMO_USER_ACCOUNT_ID ?? "00000000-0000-7000-8000-000000000083",
    source: "local-session",
  };
}

export async function getActiveTenantWorkspace(): Promise<ActiveTenantWorkspace> {
  const context = await getActiveTenantContext();
  const response = await fetch(new URL("/v1/tenant-workspace", process.env.REFERENCE_API_URL ?? "http://localhost:8000"), {
    headers: { "X-Tenant-Id": context.tenantId, "X-User-Account-Id": context.userAccountId },
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Active tenant workspace is unavailable");
  return ((await response.json()) as { data: ActiveTenantWorkspace }).data;
}
