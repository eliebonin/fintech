import { redirect } from "next/navigation";

import { WorkspaceShell } from "@/components/workspace-shell";
import { getActiveTenantContext, getActiveTenantWorkspace } from "@/lib/tenant-session";
import { StrategyConsole } from "./strategy-console";

export const dynamic = "force-dynamic";
type Strategy = { strategyId: string; strategyCode: string; displayName: string; strategyType: string; baseCurrencyCode?: string | null; status: string };

export default async function StrategiesPage() {
  let context;
  let workspace;
  try { [context, workspace] = await Promise.all([getActiveTenantContext(), getActiveTenantWorkspace()]); } catch { redirect("/select-tenant"); }
  const response = await fetch(new URL("/v1/strategies", process.env.REFERENCE_API_URL ?? "http://localhost:8000"), { headers: { "X-Tenant-Id": context.tenantId, "X-User-Account-Id": context.userAccountId }, cache: "no-store" });
  const payload = response.ok ? await response.json() as { data: Strategy[] } : { data: [] };
  const canWrite = workspace.membershipRole === "TENANT_ADMIN" && workspace.moduleCodes.some((module) => module === "TRADING" || module === "FUND_MANAGEMENT");
  return <WorkspaceShell sourceLabel={response.ok ? "LIVE API" : "API UNAVAILABLE"} moduleCodes={workspace.moduleCodes} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}><StrategyConsole initialStrategies={payload.data} canWrite={canWrite} moduleCodes={workspace.moduleCodes} /></WorkspaceShell>;
}
