import { WorkspaceShell } from "@/components/workspace-shell";
import { formatResolutionTimestamp, resolutionStatusLabel, type MarketDataResolutionSnapshot } from "@/lib/market-data-resolution";

export const dynamic = "force-dynamic";

export default async function MarketDataResolutionSnapshotPage({ params }: { params: Promise<{ snapshotId: string }> }) {
  const { snapshotId } = await params;
  const baseUrl = process.env.OPS_CONSOLE_URL ?? "http://localhost:3000";
  const response = await fetch(new URL(`/api/market-data/resolution-snapshots/${snapshotId}`, baseUrl), { cache: "no-store" });
  const snapshot = response.ok ? await response.json() as MarketDataResolutionSnapshot : null;
  return <WorkspaceShell><main className="mvp-page"><header className="mvp-header"><div><p className="eyebrow">FROZEN MARKET DATA EVIDENCE</p><h1>Resolution snapshot</h1><p className="muted">{snapshot ? `${snapshot.status} · cut ${formatResolutionTimestamp(snapshot.marketDataAsOfUtc)}` : "Snapshot is unavailable."}</p></div></header>
    {snapshot ? <section className="history-grid">{snapshot.items.map((item) => <article className="history-panel" key={item.subjectReferenceNodeId}><header className="history-heading"><div><p className="eyebrow">{resolutionStatusLabel(item.status)}</p><h2>{item.subjectReferenceNodeId}</h2><p className="muted">Policy rule {item.policyRuleId ?? "—"} · {item.selectionReason}</p></div><strong>{item.selectedValue ?? "—"}</strong></header><dl className="provenance"><dt>Series / observation</dt><dd>{item.marketDataSeriesId ?? "—"} / {item.marketDataObservationId ?? "—"}</dd><dt>Dataset / licence</dt><dd>{item.datasetId ?? "—"} / {item.acquisitionLicenceId ?? "—"}</dd><dt>Vintage</dt><dd>{item.marketDataVintageId ?? "—"}</dd><dt>Published / received</dt><dd>{formatResolutionTimestamp(item.sourcePublishedAtUtc)} / {formatResolutionTimestamp(item.receivedAtUtc)}</dd><dt>Pricing / staleness</dt><dd>{item.pricingDateRequested ?? "—"} → {item.pricingDateUsed ?? "—"} · {item.stalenessStatus}</dd><dt>Entitlement / exception</dt><dd>{item.entitlementDecision} / {item.exceptionCode ?? "—"}</dd></dl></article>)}</section> : <div className="error-panel">Frozen snapshot evidence could not be loaded.</div>}
  </main></WorkspaceShell>;
}
