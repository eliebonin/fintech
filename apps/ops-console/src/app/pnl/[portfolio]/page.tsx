import Link from "next/link";

import { describeMvpError, getPortfolioPnl, MvpApiError } from "@/lib/mvp-api-client";
import { formatPnl, formatRate, pnlTone, type PortfolioPnlPayload } from "@/lib/portfolio-pnl";
import { resolveLocalTenantContext } from "@/lib/tenant-context";
import { WorkspaceShell } from "@/components/workspace-shell";

export const dynamic = "force-dynamic";

export default async function PortfolioPnlPage({ params, searchParams }: { params: Promise<{ portfolio: string }>; searchParams: Promise<{ asOfDate?: string }> }) {
  const { portfolio } = await params;
  const query = await searchParams;
  const asOfDate = query.asOfDate ?? "2026-08-28";
  let payload: PortfolioPnlPayload | undefined;
  let error = "";
  let unsupported=false;
  try { payload = await getPortfolioPnl(resolveLocalTenantContext(), portfolio === "uk" ? "MVP_UK_PORTFOLIO" : "MVP_US_PORTFOLIO", asOfDate); } catch (caught) { unsupported=caught instanceof MvpApiError&&["valuation.fx_forward_unsupported","valuation.option_unsupported"].includes(caught.code??''); error = unsupported?(caught instanceof MvpApiError&&caught.code==='valuation.option_unsupported'?"This strategy contains options. Option valuation is not supported yet.":"This strategy contains FX forwards. FX-forward valuation is not supported yet."):describeMvpError(caught, "Portfolio P&L"); }
  const data = payload?.data;
  const sourceLabel = unsupported ? "VALUATION UNSUPPORTED" : error ? "API UNAVAILABLE" : "LIVE API · DEMO DATA";
  return (
    <WorkspaceShell><main className="mvp-page">
      <header className="mvp-header"><div><p className="eyebrow">PORTFOLIO P&amp;L</p><h1>{data?.portfolioName ?? (portfolio === "uk" ? "UK portfolio" : "US portfolio")}</h1><p className="muted">Instrument-level display decomposition from immutable booked trades and observations.</p></div><span className={`synthetic-badge ${error ? "source-unavailable" : ""}`}>{sourceLabel}</span></header>
      <form className="date-form" method="get"><label>As of <input type="date" name="asOfDate" defaultValue={asOfDate} /></label><button type="submit">Refresh P&amp;L</button></form>
      {error ? <div className="error-panel">{error}</div> : data ? <><section className="pnl-summary"><div><small>Total P&amp;L</small><strong className={pnlTone(data.totalPnl)}>{formatPnl(data.totalPnl, data.baseCurrency)}</strong></div><div><small>Base currency</small><strong>{data.baseCurrency}</strong></div><div><small>Valuation cut</small><strong>{data.valuationCut.cutCode}</strong><span>{data.valuationCut.timezoneName} {data.valuationCut.localTime}</span></div><div><small>As of</small><strong>{data.asOfDate}</strong></div></section><section className="table-wrap"><table><thead><tr><th>Instrument</th><th>Type</th><th>Qty<br /><small>economic units</small></th><th>Price used<br /><small>local price · open → close</small></th><th>FX rate used<br /><small>open → close</small></th><th>Local price P&amp;L</th><th>FX P&amp;L</th><th>Total P&amp;L</th></tr></thead><tbody>{data.lines.map((line) => <tr key={`${line.instrumentId}-${line.listingId ?? "instrument"}`}><td><strong>{line.instrumentName}</strong><code>{line.listingId ? `listing ${line.listingId.slice(0, 10)}…` : `instrument ${line.instrumentId.slice(0, 10)}…`}</code></td><td>{line.instrumentType}</td><td>{line.quantity}</td><td><span className="used-value">{formatRate(line.openingPrice)} → {formatRate(line.closingPrice)}</span><small>{line.localCurrency}</small></td><td><span className="used-value">{formatRate(line.openingFx)} → {formatRate(line.closingFx)}</span><small>{data.baseCurrency} per local currency</small></td><td>{formatPnl(line.localPricePnl, data.baseCurrency)}</td><td>{formatPnl(line.fxPnl, data.baseCurrency)}</td><td className={pnlTone(line.totalPnl)}>{formatPnl(line.totalPnl, data.baseCurrency)}</td></tr>)}</tbody></table></section><p className="methodology">{data.methodology}</p></> : null}
    </main></WorkspaceShell>
  );
}
