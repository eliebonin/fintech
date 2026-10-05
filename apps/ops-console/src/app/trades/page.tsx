import Link from "next/link";
import { redirect } from "next/navigation";

import { describeMvpError, getBookedTrades, getHistoryStrategies, type HistoryStrategy } from "@/lib/mvp-api-client";
import { formatTradeDateTime, formatTradeNumber, formatTradeExactDecimal, tradeDirection, type BookedTrade } from "@/lib/trades";
import { bookedSwapFacts, historyHref, parseHistoryQuery, type HistorySearchParams } from "@/lib/trade-history";
import { getActiveTenantContext, getActiveTenantWorkspace } from "@/lib/tenant-session";
import { WorkspaceShell } from "@/components/workspace-shell";

export const dynamic = "force-dynamic";

function TradeRow({ trade, returnTo }: { trade: BookedTrade; returnTo: string }) {
  const swap=bookedSwapFacts(trade);
  const instrument = swap?trade.productEconomics!.terms.name:trade.instrumentName ?? trade.subjectName;
  return <tr>
    <td><strong>{formatTradeDateTime(trade.tradeDatetimeUtc)}</strong></td>
    <td><Link className="trade-subject-link" href={`/trades/${encodeURIComponent(trade.tradeId)}?returnTo=${encodeURIComponent(returnTo)}`}><strong>{instrument}</strong></Link><small>{[trade.listingSymbol, trade.venueMic].filter(Boolean).join(" · ") || trade.instrumentType}</small></td>
    <td><strong>{trade.strategyCode}</strong><small>{trade.strategyName}</small></td>
    <td><span className="quality">{tradeDirection(trade.quantity)}</span>{trade.positionEffect?<small>{trade.positionEffect}</small>:null}</td>
    <td className="trade-numeric"><strong>{(trade.instrumentType==="FX_FORWARD"||trade.productEconomics?formatTradeExactDecimal:formatTradeNumber)(swap?swap.bookedNotional:trade.quantity.replace(/^-/, ""))}</strong><small>{swap?`Booked nominal · ${trade.productEconomics!.terms.currency}`:trade.fxForwardEconomics?`Base amount · ${trade.fxForwardEconomics.baseCurrency}`:trade.quantityUnit}</small>{swap?<small>Contractual notional · {formatTradeExactDecimal(swap.terms.contractualNotional)} {trade.productEconomics!.terms.currency}</small>:null}</td>
    <td className="trade-numeric"><strong>{(trade.instrumentType==="FX_FORWARD"||trade.instrumentType==="OPTION"||trade.productEconomics?formatTradeExactDecimal:formatTradeNumber)(trade.executionPrice)}</strong><small>{swap?`SWAP_VALUE_PER_NOTIONAL · ${trade.productEconomics!.terms.currency}`:trade.productEconomics?`${trade.priceBasis} · ${trade.priceCurrency}`:trade.fxForwardEconomics?`Rate · ${trade.fxForwardEconomics.quoteConvention} · OTC`:trade.optionEconomics?`Quoted premium · ${trade.priceCurrency}`:trade.priceCurrency ?? "—"}</small>{swap?<small>Entry reference value (not a payment or verified MTM) · {formatTradeExactDecimal(trade.productEconomics!.amount)} {trade.productEconomics!.terms.currency}</small>:null}</td>
    <td>{trade.settlementDate ?? "—"}</td>
    <td><span className={`quality quality-${trade.lifecycleStatus.toLowerCase()}`}>{trade.lifecycleStatus}</span></td>
  </tr>;
}

export default async function TradesPage({ searchParams }: { searchParams: Promise<HistorySearchParams> }) {
  const query = parseHistoryQuery(await searchParams);
  let context;
  let workspace;
  try { [context, workspace] = await Promise.all([getActiveTenantContext(), getActiveTenantWorkspace()]); } catch { redirect("/select-tenant"); }
  let trades: BookedTrade[] = [];
  let strategies: HistoryStrategy[] = [];
  let total = 0;
  let error = "";
  let strategyError = "";
  const [tradeResult, strategyResult] = await Promise.allSettled([
    getBookedTrades(context, { portfolioCode: query.portfolioCode || undefined, fromDate: query.fromDate || undefined, toDate: query.toDate || undefined,
      q: query.q || undefined, side: query.side || undefined, lifecycleStatus: query.lifecycleStatus || undefined,
      limit: query.pageSize, offset: (query.page - 1) * query.pageSize }),
    getHistoryStrategies(context),
  ]);
  if (tradeResult.status === "fulfilled") { trades = tradeResult.value.data; total = tradeResult.value.meta.total ?? trades.length; }
  else error = describeMvpError(tradeResult.reason, "Trade history");
  if (strategyResult.status === "fulfilled") strategies = strategyResult.value.data;
  else strategyError = "Strategy choices could not be loaded. Your current filter is preserved; retry to load the choices.";
  const pages = Math.max(1, Math.ceil(total / query.pageSize));
  if (!error && query.page > pages) redirect(historyHref(query, pages));
  const returnTo = historyHref(query);
  const otherFilters = Boolean(query.q || query.portfolioCode || query.side || query.lifecycleStatus);
  const filtered = otherFilters || query.range !== "all";
  const rangeLabel = query.range === "14d" ? "Last 14 days" : query.range === "30d" ? "Last 30 days" : query.range === "all" ? "All history" : "Custom range";
  const rangeHref = (range: "14d" | "30d" | "all") => {
    const dates = parseHistoryQuery({ range });
    return historyHref({ ...query, range: dates.range, fromDate: dates.fromDate, toDate: dates.toDate }, 1);
  };
  const statuses = [...new Set(["BOOKED", "CANCELLED", "SUPERSEDED", "VOID", ...trades.map((trade) => trade.lifecycleStatus), ...(query.lifecycleStatus ? [query.lifecycleStatus] : [])])];
  const sourceLabel = error ? "API UNAVAILABLE" : "LIVE API";
  return <WorkspaceShell sourceLabel={sourceLabel} moduleCodes={workspace.moduleCodes} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}><main className="mvp-page">
    <header className="mvp-header"><div><p className="eyebrow">TENANT TRADE LEDGER</p><h1>Trade history</h1><p className="muted">Recorded trades, newest first. Open a trade to inspect its booking details and lifecycle events.</p></div><Link className="clear-link" href="/trades/new">Book trade</Link></header>
    <nav className="trade-range-links" aria-label="Trade history date range">
      {(["14d", "30d", "all"] as const).map((range) => <Link key={range} href={rangeHref(range)} aria-current={query.range === range ? "page" : undefined}>{range === "14d" ? "Last 14 days" : range === "30d" ? "Last 30 days" : "All history"}</Link>)}
      <a href="#history-filters" aria-current={query.range === "custom" ? "page" : undefined}>Custom</a>
      <span>{rangeLabel}{query.range !== "all" ? ` · ${query.fromDate || "Any date"} to ${query.toDate || "Any date"} (UTC)` : " · No date restriction"}</span>
    </nav>
    <form id="history-filters" key={`filters:${returnTo}`} className="date-form trade-filter-form" method="get" action="/trades">
      <input type="hidden" name="range" value="custom" />
      <label>Search<input type="search" name="q" maxLength={200} defaultValue={query.q} placeholder="Instrument, symbol or trade ID" /></label>
      <label>Strategy<select name="portfolioCode" defaultValue={query.portfolioCode}><option value="">All strategies</option>
        {query.portfolioCode && !strategies.some((strategy) => strategy.strategyCode === query.portfolioCode) ? <option value={query.portfolioCode}>{query.portfolioCode}</option> : null}
        {strategies.map((strategy) => <option key={strategy.strategyId} value={strategy.strategyCode}>{strategy.strategyCode} · {strategy.displayName}{strategy.status !== "ACTIVE" ? ` (${strategy.status.toLowerCase()})` : ""}</option>)}
      </select></label>
      <label>Trade date from (UTC)<input type="date" name="fromDate" defaultValue={query.fromDate} /></label>
      <label>Trade date to (UTC)<input type="date" name="toDate" defaultValue={query.toDate} /></label>
      <label>Side<select name="side" defaultValue={query.side}><option value="">All sides</option><option value="BUY">Buy</option><option value="SELL">Sell</option></select></label>
      <label>Status<select name="lifecycleStatus" defaultValue={query.lifecycleStatus}><option value="">All statuses</option>{statuses.map((status) => <option key={status}>{status}</option>)}</select></label>
      <label>Trades per page<select name="pageSize" defaultValue={query.pageSize}>{[25, 50, 100].map((size) => <option key={size}>{size}</option>)}</select></label>
      <button type="submit">Apply filters</button>{filtered ? <Link className="clear-link" href="/trades">Clear filters</Link> : null}
    </form>
    {strategyError ? <p className="error-panel" role="alert">{strategyError} <Link href={returnTo}>Retry</Link></p> : null}
    {error ? <div className="error-panel" role="alert">{error} <Link href={returnTo}>Retry</Link></div> : <>
      <section className="table-wrap trades-table-wrap" aria-label="Trade history results"><table className="trades-table"><caption className="trade-caption">{total} {filtered ? "matching" : "recorded"} trades · trade times in UTC</caption><thead><tr>{["Trade time (UTC)", "Instrument / listing", "Strategy", "Side", "Quantity", "Price / currency", "Settlement date", "Status"].map((label) => <th key={label} scope="col">{label}</th>)}</tr></thead>
        <tbody>{trades.length ? trades.map((trade) => <TradeRow key={trade.tradeId} trade={trade} returnTo={returnTo} />) : <tr><td colSpan={8} className="empty-table">{!otherFilters && query.range === "14d" ? <>No trades in the last 14 days. <Link href={rangeHref("all")}>View all history</Link></> : !otherFilters && query.range === "30d" ? <>No trades in the last 30 days. <Link href={rangeHref("all")}>View all history</Link></> : filtered ? <>No trades match these filters. <Link href="/trades">Clear filters</Link> · <Link href={rangeHref("all")}>View all history</Link></> : <>No trades have been recorded for this tenant. <Link href="/trades/new">Book your first trade</Link></>}</td></tr>}</tbody>
      </table></section>
      <nav className="trade-pagination" aria-label="Trade history pagination"><span>{total ? (query.page - 1) * query.pageSize + 1 : 0}–{Math.min(query.page * query.pageSize, total)} of {total}</span>
        {query.page > 1 ? <Link href={historyHref(query, query.page - 1)}>Previous</Link> : <span aria-disabled="true">Previous</span>}
        <form key={`pagination:${returnTo}`} method="get" action="/trades">{Object.entries(query).filter(([key, value]) => key !== "page" && value !== "").map(([key, value]) => <input type="hidden" key={key} name={key} value={value} />)}<label>Page <input type="number" name="page" min={1} max={pages} defaultValue={query.page} aria-label="Page number" /></label><span> of {pages}</span><button type="submit">Go</button></form>
        {query.page < pages ? <Link href={historyHref(query, query.page + 1)}>Next</Link> : <span aria-disabled="true">Next</span>}
      </nav>
    </>}
  </main></WorkspaceShell>;
}
