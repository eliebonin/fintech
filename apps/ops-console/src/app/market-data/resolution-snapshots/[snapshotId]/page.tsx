import { WorkspaceShell } from "@/components/workspace-shell";
import {pricingEvidenceLabel} from '@/lib/pricing-policy';
import {redirect} from 'next/navigation';
import {getActiveTenantContext,getActiveTenantWorkspace} from '@/lib/tenant-session';
import {pricingPolicyClient} from '@/lib/pricing-policy-api';
import { formatResolutionTimestamp, resolutionStatusLabel, type MarketDataResolutionSnapshot } from "@/lib/market-data-resolution";

export const dynamic = "force-dynamic";

export default async function MarketDataResolutionSnapshotPage({ params }: { params: Promise<{ snapshotId: string }> }) {
  const { snapshotId } = await params;
  try{await getActiveTenantContext();}catch{redirect('/select-tenant');}
  const workspace=await getActiveTenantWorkspace();
  let snapshot:MarketDataResolutionSnapshot|null=null;
  try{if(workspace.moduleCodes.includes('MARKET_DATA')){const result=await (await pricingPolicyClient()).GET('/v1/market-data-resolution-snapshots/{snapshot_id}',{params:{path:{snapshot_id:snapshotId}}});snapshot=result.data??null;}}catch{/* Do not re-resolve or use a fallback tenant. */}
  return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}><main className="mvp-page"><header className="mvp-header"><div><p className="eyebrow">FROZEN MARKET DATA EVIDENCE</p><h1>Resolution snapshot</h1><p className="muted">{snapshot ? `${snapshot.status} · cut ${formatResolutionTimestamp(snapshot.marketDataAsOfUtc)}` : "Snapshot is unavailable."}</p></div></header>
    {snapshot ? <section className="history-grid">{snapshot.items.map((item) => <article className="history-panel" key={item.subjectReferenceNodeId}><header className="history-heading"><div><p className="eyebrow">{resolutionStatusLabel(item.status)}</p><h2>{item.subjectReferenceNodeId}</h2><p className="muted">Policy rule {item.policyRuleId ?? "—"} · {item.selectionReason}</p></div><strong>{item.selectedValue ?? "—"}</strong></header><dl className="provenance"><dt>Series / observation</dt><dd>{item.marketDataSeriesId ?? "—"} / {item.marketDataObservationId ?? "—"}</dd><dt>Dataset / licence</dt><dd>{item.datasetId ?? "—"} / {item.acquisitionLicenceId ?? "—"}</dd><dt>Vintage</dt><dd>{item.marketDataVintageId ?? "—"}</dd><dt>Published / received</dt><dd>{formatResolutionTimestamp(item.sourcePublishedAtUtc)} / {formatResolutionTimestamp(item.receivedAtUtc)}</dd><dt>Pricing / staleness</dt><dd>{item.pricingDateRequested ?? "—"} → {item.pricingDateUsed ?? "—"} · {item.stalenessStatus}</dd><dt>Entitlement / exception</dt><dd>{item.entitlementDecision} / {item.exceptionCode ?? "—"}</dd></dl></article>)}</section> : <div className="error-panel">Frozen snapshot evidence could not be loaded.</div>}
    {snapshot?<section className="history-panel"><h2>Frozen pricing targets</h2>{snapshot.items.map(item=><details key={item.subjectReferenceNodeId}><summary>{item.subjectReferenceNodeId} · {pricingEvidenceLabel(item.pricingEvidence)}</summary><pre>{item.pricingEvidence?JSON.stringify(item.pricingEvidence,null,2):'No composite evidence was recorded for this legacy snapshot.'}</pre></details>)}</section>:null}
  </main></WorkspaceShell>;
}
