import Link from "next/link";
import { redirect } from "next/navigation";
import { WorkspaceShell } from "@/components/workspace-shell";
import { resolveWorkspaceAccess } from "@/lib/server/workspace-access";
import { WorkspaceUnavailable } from "@/components/workspace-unavailable";
import { ValuationConsole } from "@/components/valuation-console";

export const dynamic = "force-dynamic";

/**
 * Tenant workspace for authoritative backend results, never browser pricing.
 * The retired demo endpoint remains gone; the new workflow has a bounded scope.
 */
export default async function ValuationPage() {
  const access = await resolveWorkspaceAccess();
  if (access.kind === "session-required") redirect("/select-tenant");
  if (access.kind !== "ready") return <WorkspaceUnavailable forbidden={access.kind === "forbidden"} />;
  const { workspace, context } = access;
  const actorId = context.userAccountId;
  const enabled = workspace.moduleCodes.includes("MARKET_DATA") && workspace.moduleCodes.includes("VALUATION");

  return (
    <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes} permissionCodes={workspace.permissionCodes} userName={workspace.userName} actorId={workspace.actorId} sourceLabel={enabled ? "ECONOMIC P&L ALPHA" : "ACCESS RESTRICTED"}>
      <main className="mvp-page pnl-page">
        <header className="pnl-page-heading">
          <div>
            <h1>P&amp;L validation</h1>
            <p className="muted">Inspect positions, review changes and publish with recorded review authority.</p>
            <p><Link href="/valuation/cash-balances">Manage dated cash balances</Link> · <Link href="/valuation/interest">Interest &amp; accrued balances</Link></p>
          </div>
          <span className="synthetic-badge">{enabled ? "ECONOMIC P&L ALPHA" : "ACCESS RESTRICTED"}</span>
        </header>
        {enabled ? (
          <><ValuationConsole canCalculate={workspace.permissionCodes?.includes("VALUATION_RUN") ?? false} canReview={workspace.permissionCodes?.includes("VALUATION_REVIEW") ?? false} actorId={actorId}/><p><Link href="/strategies">Strategies</Link> · <Link href="/market-data">Market data</Link></p></>
        ) : <p role="alert" className="error-panel">VALUATION and MARKET_DATA must both be enabled for this tenant. Contact your tenant administrator or change tenant.</p>}
      </main>
    </WorkspaceShell>
  );
}
