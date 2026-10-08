import Link from "next/link";
import { redirect } from "next/navigation";
import { WorkspaceShell } from "@/components/workspace-shell";
import { getActiveTenantContext, getActiveTenantWorkspace } from "@/lib/tenant-session";
import { ValuationConsole } from "@/components/valuation-console";

export const dynamic = "force-dynamic";

/**
 * Tenant workspace for authoritative backend results, never browser pricing.
 * The retired demo endpoint remains gone; the new workflow has a bounded scope.
 */
export default async function ValuationPage() {
  let actorId = "";
  try {
    actorId = (await getActiveTenantContext()).userAccountId;
  } catch {
    redirect("/select-tenant");
  }
  const workspace = await getActiveTenantWorkspace();
  const enabled = workspace.moduleCodes.includes("MARKET_DATA") && workspace.moduleCodes.includes("VALUATION");

  return (
    <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes} sourceLabel={enabled ? "MARKET-ONLY ALPHA" : "ACCESS RESTRICTED"}>
      <main className="mvp-page">
        <header className="mvp-header">
          <div>
            <p className="eyebrow">VALUATION AND P&amp;L</p>
            <h1>Valuation &amp; P&amp;L</h1>
            <p className="muted">Replayed booking evidence, frozen market inputs and staged attribution review.</p>
          </div>
          <span className="synthetic-badge">{enabled ? "MARKET-ONLY ALPHA" : "ACCESS RESTRICTED"}</span>
        </header>
        {enabled ? (
          <><ValuationConsole canManage={workspace.membershipRole === "TENANT_ADMIN"} actorId={actorId}/><p><Link href="/strategies">Strategies</Link> · <Link href="/market-data">Market data</Link></p></>
        ) : <p role="alert" className="error-panel">VALUATION and MARKET_DATA must both be enabled for this tenant. Contact your tenant administrator or change tenant.</p>}
      </main>
    </WorkspaceShell>
  );
}
