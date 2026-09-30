import Link from "next/link";
import { redirect } from "next/navigation";

import { describeMvpError, getBookedTradeDetail } from "@/lib/mvp-api-client";
import { formatTradeDateTime, formatTradeNumber, type TradeDetailPayload } from "@/lib/trades";
import { getActiveTenantContext, getActiveTenantWorkspace } from "@/lib/tenant-session";
import { WorkspaceShell } from "@/components/workspace-shell";

export const dynamic = "force-dynamic";

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return <div className="detail-field"><small>{label}</small><strong>{value || "—"}</strong></div>;
}

function DetailContent({ detail }: { detail: TradeDetailPayload["data"] }) {
  const trade = detail.trade;
  return (
    <>
      <section className="detail-card">
        <div className="detail-card-heading"><div><p className="eyebrow">BOOKED EXECUTION · {trade.lifecycleStatus}</p><h2>{trade.instrumentName ?? trade.subjectName}</h2><p className="muted">{trade.listingSymbol ? `${trade.listingSymbol} · ${trade.venueMic ?? "venue unavailable"}` : "Instrument-level / OTC subject"}</p></div><span className="quality quality-booked">{trade.tradeType}</span></div>
        <div className="detail-fields"><Field label="Trade ID" value={trade.tradeId} /><Field label="Portfolio" value={`${trade.strategyCode} · ${trade.strategyName}`} /><Field label="Quantity" value={`${formatTradeNumber(trade.quantity)} ${trade.quantityUnit}`} /><Field label="Execution price" value={`${formatTradeNumber(trade.executionPrice)} ${trade.priceCurrency ?? ""}`} /><Field label="Price basis" value={trade.priceBasis} /><Field label="Trade time (UTC)" value={formatTradeDateTime(trade.tradeDatetimeUtc)} /><Field label="Settlement date" value={trade.settlementDate} /><Field label="Execution channel" value={trade.executionChannel} /></div>
      </section>
      <div className="detail-columns">
        <section className="detail-card"><div className="detail-card-heading"><div><p className="eyebrow">PARTIES &amp; PEOPLE</p><h2>Who is involved</h2></div></div><div className="party-list">{detail.parties.map((party) => <div className="party-row" key={party.tradePartyRoleId}><div><strong>{party.partyName}</strong><small>{party.role}</small></div><code>{party.organisationId ?? party.personId ?? "—"}</code></div>)}{trade.traderPersonId ? <div className="party-row"><div><strong>Trader</strong><small>Primary trader person</small></div><code>{trade.traderPersonId}</code></div> : null}<div className="party-row"><div><strong>Booked by</strong><small>Authenticated account</small></div><code>{trade.bookedByUserAccountId}</code></div></div></section>
        <section className="detail-card"><div className="detail-card-heading"><div><p className="eyebrow">FEES</p><h2>Charges &amp; revenue</h2></div></div>{detail.fees.length ? <div className="fee-list">{detail.fees.map((fee) => <div className="fee-row" key={fee.tradeFeeId}><div><strong>{fee.feeType}</strong><small>{fee.payerOrganisationName ?? "Unknown payer"} → {fee.recipientOrganisationName ?? "Unknown recipient"}</small></div><strong>{formatTradeNumber(fee.feeAmount)} {fee.feeCurrency ?? ""}</strong><small>{fee.feeRate ?? "—"} {fee.feeRateUnit ?? ""} · {fee.status}</small></div>)}</div> : <p className="muted">No fee records.</p>}</section>
      </div>
      <div className="detail-columns">
        <section className="detail-card"><div className="detail-card-heading"><div><p className="eyebrow">EXTERNAL REFERENCES</p><h2>Source identifiers</h2></div></div>{detail.externalReferences.length ? <div className="reference-list">{detail.externalReferences.map((reference) => <div className="reference-row" key={reference.tradeExternalReferenceId}><strong>{reference.referenceType}</strong><code>{reference.referenceValue}</code><small>{reference.sourceSystemId ?? "—"}</small></div>)}</div> : <p className="muted">No external references.</p>}</section>
        <section className="detail-card"><div className="detail-card-heading"><div><p className="eyebrow">LIFECYCLE</p><h2>Audit events</h2></div></div>{detail.lifecycleEvents.length ? <div className="event-list">{detail.lifecycleEvents.map((event) => <div className="event-row" key={event.tradeLifecycleEventId}><div><strong>{event.sequenceNo}. {event.eventType}</strong><small>{formatTradeDateTime(event.eventDatetimeUtc)} · {event.sourceSystemId ?? "internal"}</small></div><code>{event.sourceEventId ?? "—"}</code></div>)}</div> : <p className="muted">No lifecycle events.</p>}</section>
      </div>
    </>
  );
}

export default async function TradeDetailPage({ params }: { params: Promise<{ tradeId: string }> }) {
  const { tradeId } = await params;
  let context;
  let workspace;
  try { [context, workspace] = await Promise.all([getActiveTenantContext(), getActiveTenantWorkspace()]); } catch { redirect("/select-tenant"); }
  let detail: TradeDetailPayload["data"] | null = null;
  let error = "";
  try {
    detail = (await getBookedTradeDetail(context, tradeId)).data;
  } catch (caught) {
    error = describeMvpError(caught, "Booked trade");
  }
  const sourceLabel = error ? "API UNAVAILABLE" : "LIVE API";
  return (
    <WorkspaceShell sourceLabel={sourceLabel} moduleCodes={workspace.moduleCodes} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}><main className="mvp-page">
      <header className="mvp-header"><div><p className="eyebrow">TRADE DETAIL</p><h1>{detail?.trade.instrumentName ?? "Booked execution"}</h1><p className="muted">Normalized parties, fees, source references and append-only lifecycle evidence.</p></div><span className={`synthetic-badge ${error ? "source-unavailable" : ""}`}>{sourceLabel}</span></header>
      <p className="back-line"><Link href="/trades">← Back to booked executions</Link></p>
      {error ? <div className="error-panel">{error}</div> : detail ? <DetailContent detail={detail} /> : <div className="error-panel">Booked trade not found.</div>}
    </main></WorkspaceShell>
  );
}
