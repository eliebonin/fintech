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
    <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes} sourceLabel={enabled ? "ECONOMIC P&L ALPHA" : "ACCESS RESTRICTED"}>
      <main className="mvp-page">
        <header className="mvp-header">
          <div>
            <p className="eyebrow">VALUATION AND P&amp;L</p>
            <h1>Valuation &amp; P&amp;L</h1>
            <p className="muted">Replayed booking evidence, frozen market inputs and staged attribution review.</p>
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
