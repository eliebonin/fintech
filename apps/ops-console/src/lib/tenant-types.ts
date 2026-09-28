/** Data-only tenant context shape. Client components may import this type. */
export type TenantContext = {
  tenantId: string;
  userAccountId: string;
  source: "local-session" | "auth0-session";
};
