import { redirect } from "next/navigation";
import { WorkspaceShell } from "@/components/workspace-shell";
import { resolveWorkspaceAccess } from "@/lib/server/workspace-access";
import { WorkspaceUnavailable } from "@/components/workspace-unavailable";

import {TradeConfigurationWorkspace} from "@/features/trade-profiles/trade-configuration-workspace";
export const dynamic="force-dynamic";
export default async function TradeConfigurationPage({searchParams}:{searchParams:Promise<Record<string,string|string[]|undefined>>}={searchParams:Promise.resolve({})}) {
  const query=await searchParams;
  const view=query.section==="standard"?"traders":typeof query.view==="string"?query.view:"profiles";
  const access = await resolveWorkspaceAccess();
  if (access.kind === "session-required") redirect("/select-tenant");
  if (access.kind !== "ready") return <WorkspaceUnavailable forbidden={access.kind === "forbidden"} />;
  const {workspace} = access;
  const allowed=workspace.permissionCodes?.includes("TRADE_CONFIGURE")??false;
  return <WorkspaceShell {...workspace}>{allowed?<TradeConfigurationWorkspace key={workspace.tenantId+access.context.userAccountId+view} tenantId={workspace.tenantId} view={view} versionId={typeof query.profileVersionId==="string"?query.profileVersionId:undefined} query={typeof query.q==="string"?query.q:undefined}/>:<main className="mvp-page"><h1>Trade configuration</h1><p>Trade configuration permission in the Trading module is required. Ask your tenant administrator to review your groups.</p></main>}</WorkspaceShell>;
}
