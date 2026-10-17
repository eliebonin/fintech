import { apiRead } from "@/lib/server/api-read";
import { WorkspaceApiError } from "@/lib/server/workspace-errors";
import { resolveWorkspaceAccess } from "@/lib/server/workspace-access";
import { WorkspaceUnavailable } from "@/components/workspace-unavailable";
import { redirect } from "next/navigation";

import { WorkspaceShell } from "@/components/workspace-shell";
import { StrategyConsole } from "./strategy-console";

type Strategy = { strategyId: string; strategyCode: string; displayName: string; strategyType: string; baseCurrencyCode?: string | null; status: string };

export async function StrategyPageContent({createOnly=false}:{createOnly?:boolean}) {
  let context;
  let workspace;
  const access = await resolveWorkspaceAccess();
  if (access.kind === "session-required") redirect("/select-tenant");
  if (access.kind !== "ready") return <WorkspaceUnavailable forbidden={access.kind === "forbidden"} />;
  context = access.context; workspace = access.workspace;
  try {
  const response = await apiRead(new URL("/v1/strategies", process.env.REFERENCE_API_URL ?? "http://localhost:8000"), { headers: { "X-Tenant-Id": context.tenantId, "X-User-Account-Id": context.userAccountId }, cache: "no-store" });
  if (!response.ok && !(response.status===403 && workspace.permissionCodes?.includes('STRATEGY_CREATE'))) throw new WorkspaceApiError(response.status);
  const payload = response.ok?await response.json() as { data: Strategy[] }:{data:[]};
  const canWrite = workspace.permissionCodes?.includes("STRATEGY_CREATE") ?? false;
  let accessGroups:Array<{groupId:string;name:string;scopeMode:string}>=[];
  if(canWrite&&createOnly){const options=await apiRead(new URL('/v1/strategies/access-options',process.env.REFERENCE_API_URL??'http://localhost:8000'),{headers:{'X-Tenant-Id':context.tenantId,'X-User-Account-Id':context.userAccountId},cache:'no-store'});if(!options.ok)throw new WorkspaceApiError(options.status);accessGroups=(await options.json()).groups;}
  return <WorkspaceShell sourceLabel={response.ok ? "LIVE API" : "ACCESS RESTRICTED"} moduleCodes={workspace.moduleCodes} permissionCodes={workspace.permissionCodes} userName={workspace.userName} actorId={workspace.actorId} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}><StrategyConsole initialStrategies={payload.data} canWrite={canWrite} accessGroups={accessGroups} createOnly={createOnly} writeContext={{tenantId:context.tenantId,userAccountId:context.userAccountId}} /></WorkspaceShell>;
  } catch (error) {
    return <WorkspaceShell sourceLabel="API UNAVAILABLE" tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes} permissionCodes={workspace.permissionCodes} userName={workspace.userName} actorId={workspace.actorId}><WorkspaceUnavailable resource="Strategies" forbidden={error instanceof WorkspaceApiError && [401,403].includes(error.status)} /></WorkspaceShell>;
  }
}
