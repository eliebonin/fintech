import { apiRead } from "@/lib/server/api-read";
import { WorkspaceApiError } from "@/lib/server/workspace-errors";
import { resolveWorkspaceAccess } from "@/lib/server/workspace-access";
import { WorkspaceUnavailable } from "@/components/workspace-unavailable";
import { redirect } from "next/navigation";

import { WorkspaceShell } from "@/components/workspace-shell";
import { StrategyConsole } from "./strategy-console";

export const dynamic = "force-dynamic";
type Strategy = { strategyId: string; strategyCode: string; displayName: string; strategyType: string; baseCurrencyCode?: string | null; status: string };

export default async function StrategiesPage() {
  let context;
  let workspace;
  const access = await resolveWorkspaceAccess();
  if (access.kind === "session-required") redirect("/select-tenant");
  if (access.kind !== "ready") return <WorkspaceUnavailable forbidden={access.kind === "forbidden"} />;
  context = access.context; workspace = access.workspace;
  try {
  const response = await apiRead(new URL("/v1/strategies", process.env.REFERENCE_API_URL ?? "http://localhost:8000"), { headers: { "X-Tenant-Id": context.tenantId, "X-User-Account-Id": context.userAccountId }, cache: "no-store" });
  if (!response.ok) throw new WorkspaceApiError(response.status);
  const payload = await response.json() as { data: Strategy[] };
  const canWrite = workspace.permissionCodes?.includes("STRATEGY_WRITE") ?? false;
  return <WorkspaceShell sourceLabel={response.ok ? "LIVE API" : "API UNAVAILABLE"} moduleCodes={workspace.moduleCodes} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}><StrategyConsole initialStrategies={payload.data} canWrite={canWrite} /></WorkspaceShell>;
  } catch (error) {
    return <WorkspaceShell sourceLabel="API UNAVAILABLE" tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}><WorkspaceUnavailable resource="Strategies" forbidden={error instanceof WorkspaceApiError && [401,403].includes(error.status)} /></WorkspaceShell>;
  }
}
