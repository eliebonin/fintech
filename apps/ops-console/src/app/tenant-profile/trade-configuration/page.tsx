import { redirect } from "next/navigation";
import { WorkspaceShell } from "@/components/workspace-shell";
import { getActiveTenantWorkspace } from "@/lib/tenant-session";
import { TradeConfigurationConsole } from "./trade-configuration-console";
export const dynamic="force-dynamic";
export default async function TradeConfigurationPage() {
  let workspace;
  try {workspace=await getActiveTenantWorkspace();}catch{redirect("/select-tenant");}
  const allowed=workspace.membershipRole==="TENANT_ADMIN"&&workspace.moduleCodes.includes("TRADING");
  return <WorkspaceShell moduleCodes={workspace.moduleCodes} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}>{allowed?<TradeConfigurationConsole key={workspace.tenantId} tenantId={workspace.tenantId}/>:<main className="mvp-page"><h1>Trade configuration</h1><p>Tenant administrator and Trading access are required.</p></main>}</WorkspaceShell>;
}
