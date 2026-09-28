import "server-only";

import type { TenantContext } from "./tenant-types";

export type { TenantContext } from "./tenant-types";

const DEFAULT_TENANT_ID = "00000000-0000-7000-8000-000000000011";
const DEFAULT_USER_ACCOUNT_ID = "00000000-0000-7000-8000-000000000083";

/**
 * Local seam for the authenticated session. Auth0 claim mapping will replace
 * the environment lookup without changing BFF route signatures.
 */
export function resolveLocalTenantContext(): TenantContext {
  return {
    tenantId: process.env.DEMO_TENANT_ID ?? DEFAULT_TENANT_ID,
    userAccountId: process.env.DEMO_USER_ACCOUNT_ID ?? DEFAULT_USER_ACCOUNT_ID,
    source: "local-session",
  };
}
