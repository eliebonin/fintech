import Link from "next/link";
import { redirect } from "next/navigation";

import { describeMvpError, getBookedTrades } from "@/lib/mvp-api-client";
import { formatTradeDateTime, formatTradeNumber, type BookedTrade } from "@/lib/trades";
import { getActiveTenantContext, getActiveTenantWorkspace } from "@/lib/tenant-session";
import { WorkspaceShell } from "@/components/workspace-shell";

export const dynamic = "force-dynamic";

function TradeRow({ trade }: { trade: BookedTrade }) {
  const instrument = trade.listingSymbol
    ? `${trade.instrumentName ?? trade.subjectName} · ${trade.listingSymbol}`
    : trade.instrumentName ?? trade.subjectName;
  return (
    <tr>
      <td><Link className="trade-subject-link" href={`/trades/${encodeURIComponent(trade.tradeId)}`}><strong>{instrument}</strong></Link><small>{trade.instrumentType ?? "Reference object"}</small></td>
      <td><strong>{trade.strategyCode}</strong><small>{trade.strategyName}</small></td>
      <td><strong>{formatTradeNumber(trade.quantity)}</strong><small>{trade.quantityUnit}</small></td>
      <td><strong>{formatTradeNumber(trade.executionPrice)}</strong><small>{trade.priceCurrency ?? "—"} · {trade.priceBasis ?? "—"}</small></td>
      <td><strong>{formatTradeDateTime(trade.tradeDatetimeUtc)}</strong><small>Settle {trade.settlementDate ?? "—"}</small></td>
      <td><strong>{trade.tradeType}</strong><small>{trade.marketActivity ?? trade.tradePurpose ?? "—"}</small></td>
      <td><strong>{trade.venueMic ?? "OTC / direct"}</strong><small>{trade.venueName ?? trade.executionChannel}</small></td>
      <td><span className={`quality quality-${trade.lifecycleStatus.toLowerCase()}`}>{trade.lifecycleStatus}</span><small>{trade.sourceSystemId ?? "Booked record"}</small></td>
    </tr>
  );
}

export default async function TradesPage({ searchParams }: { searchParams: Promise<{ portfolioCode?: string; fromDate?: string; toDate?: string }> }) {
  const query = await searchParams;
  const portfolioCode = query.portfolioCode ?? "";
  let context;
  let workspace;
  try { [context, workspace] = await Promise.all([getActiveTenantContext(), getActiveTenantWorkspace()]); } catch { redirect("/select-tenant"); }
  let trades: BookedTrade[] = [];
  let error = "";
  try {
    trades = (await getBookedTrades(context, { portfolioCode: portfolioCode || undefined, fromDate: query.fromDate, toDate: query.toDate, limit: 200 })).data;
  } catch (caught) {
    error = describeMvpError(caught, "Booked trades");
  }
  const usCount = trades.filter((trade) => trade.strategyCode === "MVP_US_PORTFOLIO").length;
  const ukCount = trades.filter((trade) => trade.strategyCode === "MVP_UK_PORTFOLIO").length;
  const sourceLabel = error ? "API UNAVAILABLE" : "LIVE API";
  return (
    <WorkspaceShell sourceLabel={sourceLabel} moduleCodes={workspace.moduleCodes} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}><main className="mvp-page">
      <header className="mvp-header"><div><p className="eyebrow">TRADE LEDGER</p><h1>Booked executions</h1><p className="muted">One row per booked economic event. Orders and execution fills are outside this read-only MVP view.</p></div><span className={`synthetic-badge ${error ? "source-unavailable" : ""}`}>{sourceLabel}</span></header>
      <form className="date-form trade-filter-form" method="get">
        <label>Portfolio <select name="portfolioCode" defaultValue={portfolioCode}><option value="">All portfolios</option><option value="MVP_US_PORTFOLIO">US portfolio</option><option value="MVP_UK_PORTFOLIO">UK portfolio</option></select></label>
        <label>From <input type="date" name="fromDate" defaultValue={query.fromDate} /></label>
        <label>To <input type="date" name="toDate" defaultValue={query.toDate} /></label>
        <button type="submit">Apply filters</button>
        {portfolioCode || query.fromDate || query.toDate ? <Link className="clear-link" href="/trades">Clear</Link> : null}
      </form>
      {error ? <div className="error-panel">{error}</div> : <>
        <section className="trade-summary"><div><small>Visible executions</small><strong>{trades.length}</strong></div><div><small>US portfolio</small><strong>{usCount}</strong></div><div><small>UK portfolio</small><strong>{ukCount}</strong></div><div><small>Lifecycle</small><strong>BOOKED</strong></div></section>
        <section className="table-wrap trades-table-wrap"><table className="trades-table"><thead><tr><th>Subject / listing</th><th>Portfolio</th><th>Quantity</th><th>Execution price</th><th>Trade / settlement</th><th>Type</th><th>Venue / channel</th><th>Status / source</th></tr></thead><tbody>{trades.length ? trades.map((trade) => <TradeRow key={trade.tradeId} trade={trade} />) : <tr><td colSpan={8} className="empty-table">No booked trades match these filters.</td></tr>}</tbody></table></section>
      </>}
    </main></WorkspaceShell>
  );
}
