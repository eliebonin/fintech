import Link from "next/link";
import {redirect} from 'next/navigation';

import { describeMvpError, getMarketDataSeries } from "@/lib/mvp-api-client";
import {
  formatMarketDataValue,
  sortObservationsChronologically,
  summarizeSeries,
  type MarketDataObservation,
  type MarketDataSeries,
} from "@/lib/market-data-series";
import {getActiveTenantContext, getActiveTenantWorkspace} from '@/lib/tenant-session';
import { WorkspaceShell } from "@/components/workspace-shell";
import { MarketDataResolutionForm } from "@/components/market-data-resolution-form";

export const dynamic = "force-dynamic";

function formatUtc(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toISOString().replace("T", " ").replace(".000Z", "Z");
}

function Sparkline({ series, large = false }: { series: MarketDataSeries; large?: boolean }) {
  const observations = sortObservationsChronologically(series.observations);
  const points = large ? observations : observations.slice(-45);
  if (!points.length) return <span className="muted">No observations</span>;
  const values = points.map((point) => Number(point.value));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const width = large ? 680 : 120;
  const height = large ? 180 : 32;
  const bottom = large ? 164 : 28;
  const amplitude = large ? 140 : 24;
  const path = values.map((value, index) => `${(index / Math.max(values.length - 1, 1)) * width},${bottom - ((value - min) / span) * amplitude}`).join(" ");
  return (
    <svg aria-label={`${series.seriesType} ${large ? "history chart" : "sparkline"}`} className={large ? "history-chart" : "sparkline"} width="100%" height={height} viewBox={`0 0 ${width} ${height}`} role="img">
      {large ? <line x1="0" x2={width} y1={bottom} y2={bottom} stroke="#e2e8f0" strokeWidth="1" /> : null}
      <polyline fill="none" stroke="#2563eb" strokeWidth={large ? "2.5" : "2"} points={path} />
    </svg>
  );
}

function Provenance({ series }: { series: MarketDataSeries }) {
  return (
    <dl className="provenance">
      <dt>Provider</dt><dd>{series.providerName ?? series.providerCode ?? "—"}<code>{series.providerId?.slice(0, 10) ?? "—"}…</code></dd>
      <dt>Dataset</dt><dd>{series.datasetCode ?? "—"}<code>{series.datasetId?.slice(0, 10) ?? "—"}…</code></dd>
      <dt>Licence</dt><dd>{series.licenceName ?? series.licenceCode ?? "—"}<code>{series.licenceId?.slice(0, 10) ?? "—"}…</code></dd>
      <dt>Valuation cut</dt><dd>{series.valuationCut ?? "—"} · {series.timezoneName ?? "UTC"}</dd>
      <dt>Expected coverage</dt><dd>{series.expectedFrequency} · {series.expectedCalendarCode ?? "No calendar"}</dd>
      <dt>Declared range</dt><dd>{series.coverageStartDate ?? "—"} → {series.coverageEndDate ?? "open-ended"}</dd>
    </dl>
  );
}

function ObservationTable({ observations, valueType }: { observations: MarketDataObservation[]; valueType: string }) {
  return (
    <div className="history-table-wrap">
      <table className="history-table">
        <thead><tr><th>Market date</th><th>Observed at (UTC)</th><th>Received at (UTC)</th><th>Value</th><th>Source</th><th>Vintage</th><th>Basis</th><th>Quality</th></tr></thead>
        <tbody>
          {observations.map((observation) => (
            <tr key={observation.observationId}>
              <td>{observation.marketDate ?? "—"}</td>
              <td>{formatUtc(observation.observedAt)}</td>
              <td>{formatUtc(observation.receivedAt)}</td>
              <td>{formatMarketDataValue(observation.value, valueType)}</td>
              <td>{observation.providerCode ?? "—"}<br /><small>{observation.datasetCode}</small></td>
              <td title={observation.sourceObservationKey ?? undefined}>{observation.vintageKey ?? "No batch"}</td>
              <td>{observation.valueBasis}</td>
              <td><span className={`quality quality-${observation.qualityStatus.toLowerCase()}`}>{observation.qualityStatus}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function HistoryPanel({ series }: { series: MarketDataSeries }) {
  const observations = sortObservationsChronologically(series.observations);
  const summary = summarizeSeries(observations);
  return (
    <article className="history-panel">
      <header className="history-heading">
        <div>
          <p className="eyebrow">{series.seriesType} · {series.valueType}{series.currency ? ` · ${series.currency}` : ""}</p>
          <h2>{series.referenceNodeName}</h2>
          <p className="muted">{series.datasetName ?? "Uncatalogued dataset"} · {summary.points} observations · {series.expectedFrequency} on {series.expectedCalendarCode ?? "no declared calendar"}</p>
        </div>
        <strong>{formatMarketDataValue(summary.last, series.valueType)}</strong>
      </header>
      <div className="history-provenance"><Provenance series={series} /></div>
      <div className="chart-wrap"><Sparkline series={series} large /></div>
      <div className="history-range"><span>{observations[0]?.marketDate ?? "—"}</span><span>{observations.at(-1)?.marketDate ?? "—"}</span></div>
      <ObservationTable observations={observations} valueType={series.valueType} />
    </article>
  );
}

export default async function MarketDataPage({ searchParams }: { searchParams: Promise<{ fromDate?: string; toDate?: string; referenceNodeId?: string; offset?: string; observationOffset?: string }> }) {
  const query = await searchParams;
  const yesterday = new Date(); yesterday.setUTCDate(yesterday.getUTCDate() - 1);
  const beginning = new Date(yesterday); beginning.setUTCDate(beginning.getUTCDate() - 13);
  const fromDate = query.fromDate ?? beginning.toISOString().slice(0,10);
  const toDate = query.toDate ?? yesterday.toISOString().slice(0,10);
  const selectedNodeId = query.referenceNodeId;
  const parseOffset = (value?:string) => value && /^\d+$/.test(value) ? Math.min(Number(value),100000) : 0;
  const offset = parseOffset(query.offset), observationOffset = parseOffset(query.observationOffset);
  const limit = selectedNodeId ? 50 : 12, observationLimit = selectedNodeId ? 100 : 1000;
  let context, workspace;
  try { [context,workspace] = await Promise.all([getActiveTenantContext(),getActiveTenantWorkspace()]); }
  catch {redirect('/select-tenant');}
  let series: MarketDataSeries[] = [];
  let total = 0;
  let error = "";
  const moduleEnabled = workspace.moduleCodes.includes('MARKET_DATA');
  if (!moduleEnabled) {
    error = 'Market data is not enabled for this tenant. Contact your tenant administrator to review module access.';
  } else try {
    const payload = await getMarketDataSeries(context, { fromDate, toDate, referenceNodeId: selectedNodeId, limit, offset, observationLimit, observationOffset });
    series = payload.data; total = payload.meta.total ?? series.length;
  } catch (caught) {
    error = describeMvpError(caught, "Market data");
  }
  const selectedName = series[0]?.referenceNodeName;
  const personal = series.some(s=>s.providerCode === 'YAHOO_FINANCE_PERSONAL');
  const sourceLabel = !moduleEnabled ? 'ACCESS RESTRICTED' : error ? "API UNAVAILABLE" : personal ? "LIVE API · PERSONAL PROJECT" : "LIVE API · SOURCE LABELLED";
  const historyTotal = Math.max(0,...series.map(s=>s.observationTotal ?? s.observations.length));
  function pageLink(nextOffset:number,nextObservationOffset:number) {
    const params = new URLSearchParams({fromDate,toDate,offset:String(nextOffset),observationOffset:String(nextObservationOffset)});
    if(selectedNodeId)params.set('referenceNodeId',selectedNodeId);
    return `/market-data?${params}`;
  }
  return (
    <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}><main className="mvp-page">
      {moduleEnabled ? <nav aria-label="Market data configuration"><Link href="/market-data/policies">Pricing policies · configure and preview</Link> · <Link href="/market-data/calendars">Fund and strategy calendars</Link></nav> : null}
      <header className="mvp-header"><div><p className="eyebrow">MARKET DATA CATALOGUE</p><h1>{selectedNodeId ? `${selectedName ?? "Instrument"} history` : "Series & provenance"}</h1><p className="muted">{selectedNodeId ? "Persisted observations, charted and chronologically sorted by market date." : "Precise observables with their provider, dataset, licence and named cut."}</p></div><span className={`synthetic-badge ${error ? "source-unavailable" : ""}`}>{sourceLabel}</span></header>
      <form className="date-form" method="get"><label>From <input type="date" name="fromDate" defaultValue={fromDate} /></label><label>To <input type="date" name="toDate" defaultValue={toDate} /></label>{selectedNodeId ? <input type="hidden" name="referenceNodeId" value={selectedNodeId} /> : null}<button type="submit">Refresh window</button>{selectedNodeId ? <Link className="clear-link" href={`/market-data?fromDate=${encodeURIComponent(fromDate)}&toDate=${encodeURIComponent(toDate)}`}>Back to all series</Link> : null}</form>
      {personal ? <p className="muted">Yahoo personal-project history: Close is split adjusted; adjusted close includes the provider’s distribution adjustments. Neither is an official raw-price tape. Observed timestamps identify daily bars, not certified session closes. Personal-use declaration; no commercial or redistribution rights.</p> : null}
      {!error && selectedNodeId && !personal ? <MarketDataResolutionForm subjectReferenceNodeId={selectedNodeId} /> : null}
      {!error && selectedNodeId && historyTotal > observationLimit ? <nav aria-label="Observation history pages"><p>Showing a bounded history page; up to {observationLimit} points per series, starting at {observationOffset + 1}. Charts show this page only.</p>{observationOffset > 0 ? <Link href={pageLink(offset,Math.max(0,observationOffset-observationLimit))}>Previous history page</Link> : null}{observationOffset + observationLimit < historyTotal ? <Link href={pageLink(offset,observationOffset+observationLimit)}>Next history page</Link> : null}</nav> : null}
      {!error && !selectedNodeId ? <nav aria-label="Series catalogue pages"><p>{total ? `${offset+1}–${Math.min(offset+series.length,total)} of ${total} visible series` : 'No visible observations in this window. Choose another date range or check dataset access.'}</p>{offset > 0 ? <Link href={pageLink(Math.max(0,offset-limit),0)}>Previous series page</Link> : null}{offset+limit < total ? <Link href={pageLink(offset+limit,0)}>Next series page</Link> : null}</nav> : null}
      {error ? <div className="error-panel">{error}</div> : selectedNodeId ? <section className="history-grid">{series.length ? series.map((item) => <HistoryPanel key={item.seriesId} series={item} />) : <div className="error-panel">No market-data series was found for this instrument in the selected date window.</div>}</section> : <section className="series-grid">{series.map((item) => { const summary = summarizeSeries(item.observations); return <article className="series-card" key={item.seriesId}><div className="series-card-top"><div><p className="eyebrow">{item.seriesType} · {item.valueType}</p><h2>{item.referenceNodeName}</h2><p className="muted">{item.datasetName ?? "Uncatalogued dataset"} · Node <code>{item.referenceNodeId.slice(0, 12)}…</code>{item.currency ? ` · ${item.currency}` : ""}</p></div><Sparkline series={item} /></div><div className="metric-row"><span><small>Window</small><strong>{summary.points} pts</strong></span><span><small>Latest</small><strong>{formatMarketDataValue(summary.last, item.valueType)}</strong></span><span><small>Cut</small><strong>{item.valuationCut ?? "—"}</strong></span></div><Provenance series={item} /><Link className="detail-link" href={`/market-data?referenceNodeId=${encodeURIComponent(item.referenceNodeId)}&fromDate=${encodeURIComponent(fromDate)}&toDate=${encodeURIComponent(toDate)}`}>Inspect instrument history →</Link></article>; })}</section>}
    </main></WorkspaceShell>
  );
}
