import { redirect } from "next/navigation";
import { WorkspaceShell } from "@/components/workspace-shell";
import { resolveWorkspaceAccess } from "@/lib/server/workspace-access";
import { WorkspaceUnavailable } from "@/components/workspace-unavailable";

import { TradeConfigurationConsole } from "./trade-configuration-console";
export const dynamic="force-dynamic";
export default async function TradeConfigurationPage() {
  const access = await resolveWorkspaceAccess();
  if (access.kind === "session-required") redirect("/select-tenant");
  if (access.kind !== "ready") return <WorkspaceUnavailable forbidden={access.kind === "forbidden"} />;
  const {workspace} = access;
  const allowed=workspace.permissionCodes?.includes("TRADE_CONFIGURE")??false;
  return <WorkspaceShell {...workspace}>{allowed?<TradeConfigurationConsole key={workspace.tenantId} tenantId={workspace.tenantId}/>:<main className="mvp-page"><h1>Trade configuration</h1><p>Trade configuration permission in the Trading module is required. Ask your tenant administrator to review your groups.</p></main>}</WorkspaceShell>;
}
