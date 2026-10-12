import { resolveWorkspaceAccess } from "@/lib/server/workspace-access";
import { WorkspaceUnavailable } from "@/components/workspace-unavailable";
import Link from "next/link";
import type {ReactNode} from "react";
import {MarketDataHistoryChart} from "@/components/market-data-history-chart";
import {MarketDataNavigation} from "@/components/market-data-navigation";
import {redirect} from 'next/navigation';

import { describeMvpError, getMarketDataSeries } from "@/lib/mvp-api-client";
import {
  formatMarketDataValue,
  sortObservationsChronologically,
  summarizeSeries,
  type MarketDataObservation,
  type MarketDataSeries,
} from "@/lib/market-data-series";
import { WorkspaceShell } from "@/components/workspace-shell";
import { MarketDataResolutionForm } from "@/components/market-data-resolution-form";

export const dynamic = "force-dynamic";

function formatUtc(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toISOString().replace("T", " ").replace(".000Z", "Z");
}

function Provenance({ series }: { series: MarketDataSeries }) {
  return (
    <dl className="provenance">
      <dt>Provider</dt><dd>{series.providerName ?? series.providerCode ?? "—"}<code>{series.providerId?.slice(0, 10) ?? "—"}…</code></dd>
      <dt>Dataset</dt><dd>{series.datasetCode ?? "—"}<code>{series.datasetId?.slice(0, 10) ?? "—"}…</code></dd>
      <dt>Licence</dt><dd>{series.licenceName ?? series.licenceCode ?? "—"}<code>{series.licenceId?.slice(0, 10) ?? "—"}…</code></dd>
      <dt>Valuation cut</dt><dd>{series.valuationCut ?? "—"} · {series.timezoneName ?? "UTC"}</dd>
      {series.seriesType==='CLOSE'?<><dt>Closing method</dt><dd>{({EXCHANGE_OFFICIAL:'Exchange-official',LAST_TRADE:'Last trade',PROVIDER_DEFINED:'Provider-defined',UNKNOWN:'Unknown closing method'} as Record<string,string>)[series.closingMethod??'UNKNOWN']??series.closingMethod}</dd></>:null}
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

function HistoryPanel({ series, pagination }: { series: MarketDataSeries; pagination?: ReactNode }) {
  const observations = sortObservationsChronologically(series.chartPoints ?? series.observations);
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
      <div className="chart-wrap"><MarketDataHistoryChart key={`${series.seriesId}:${observations[0]?.marketDate}:${observations.at(-1)?.marketDate}:${observations.length}`} points={observations} currency={series.currency} valueType={series.valueType} seriesType={series.seriesType} /></div>
      <div className="history-range"><span>{observations[0]?.marketDate ?? "—"}</span><span>{observations.at(-1)?.marketDate ?? "—"}</span></div>
      {pagination}
      <ObservationTable observations={sortObservationsChronologically(series.observations)} valueType={series.valueType} />
    </article>
  );
}

export default async function MarketDataHistoryPage({ searchParams }: { searchParams: Promise<{ fromDate?: string; toDate?: string; referenceNodeId?: string; seriesId?: string; offset?: string; observationLimit?: string; observationOffset?: string }> }) {
  const query = await searchParams;
  if (!query.referenceNodeId) redirect("/market-data/explorer");
  const yesterday = query.toDate ? new Date(`${query.toDate}T00:00:00Z`) : new Date();
  if (!query.toDate) yesterday.setUTCDate(yesterday.getUTCDate() - 1);
  if (Number.isNaN(yesterday.getTime())) yesterday.setTime(Date.now());
  const beginning = new Date(yesterday); beginning.setUTCDate(beginning.getUTCDate() - 13);
  const fromDate = query.fromDate ?? beginning.toISOString().slice(0,10);
  const toDate = query.toDate ?? yesterday.toISOString().slice(0,10);
  const selectedNodeId = query.referenceNodeId;
  const selectedSeriesId = query.seriesId;
  const parseOffset = (value?:string) => value && /^\d+$/.test(value) ? Math.min(Number(value),100000) : 0;
  const offset = parseOffset(query.offset), observationOffset = parseOffset(query.observationOffset);
  const limit = selectedNodeId ? 50 : 12;
  const observationLimit = [25,50,100].includes(Number(query.observationLimit)) ? Number(query.observationLimit) : 25;
  let context, workspace;
  const access = await resolveWorkspaceAccess();
  if (access.kind === "session-required") redirect("/select-tenant");
  if (access.kind !== "ready") return <WorkspaceUnavailable forbidden={access.kind === "forbidden"} />;
  context = access.context; workspace = access.workspace;
  let series: MarketDataSeries[] = [];
  let total = 0;
  let error = "";
  const moduleEnabled = workspace.moduleCodes.includes('MARKET_DATA');
  if (!moduleEnabled) {
    error = 'Market data is not enabled for this tenant. Contact your tenant administrator to review module access.';
  } else try {
    const payload = await getMarketDataSeries(context, { fromDate, toDate, referenceNodeId: selectedNodeId, seriesId: selectedSeriesId, includeChart: true, limit, offset, observationLimit, observationOffset });
    series = payload.data; total = payload.meta.total ?? series.length;
  } catch (caught) {
    error = describeMvpError(caught, "Market data");
  }
  const selectedName = series[0]?.referenceNodeName;
  const personal = series.some(s=>s.providerCode === 'YAHOO_FINANCE_PERSONAL');
  const sourceLabel = !moduleEnabled ? 'ACCESS RESTRICTED' : error ? "API UNAVAILABLE" : personal ? "LIVE API · PERSONAL PROJECT" : "LIVE API · SOURCE LABELLED";
  const historyTotal = Math.max(0,...series.map(s=>s.observationTotal ?? s.observations.length));
  function pageLink(nextOffset:number,nextObservationOffset:number) {
    const params = new URLSearchParams({fromDate,toDate,offset:String(nextOffset),observationOffset:String(nextObservationOffset),observationLimit:String(observationLimit)});
    if(selectedNodeId)params.set('referenceNodeId',selectedNodeId);
    if(selectedSeriesId)params.set('seriesId',selectedSeriesId);
    return `/market-data/explorer?${params}`;
  }
  const pricePagination = !error && selectedNodeId ? <nav aria-label="Price table pages">
        <form className="date-form" method="get">
          <input type="hidden" name="referenceNodeId" value={selectedNodeId} />
          {selectedSeriesId ? <input type="hidden" name="seriesId" value={selectedSeriesId} /> : null}
          <input type="hidden" name="fromDate" value={fromDate} /><input type="hidden" name="toDate" value={toDate} />
          <label>Prices per page <select name="observationLimit" defaultValue={observationLimit}>{[25,50,100].map(size=><option key={size} value={size}>{size}</option>)}</select></label>
          <button type="submit">Apply page size</button>
        </form>
        <p>{historyTotal ? `${Math.min(observationOffset+1,historyTotal)}-${Math.min(observationOffset+observationLimit,historyTotal)} of ${historyTotal}` : "0 prices"} per series. Charts show the full selected period.</p>
        {observationOffset > 0 ? <Link href={pageLink(offset,Math.max(0,observationOffset-observationLimit))}>Previous prices</Link> : null}{' '}
        {observationOffset + observationLimit < historyTotal ? <Link href={pageLink(offset,observationOffset+observationLimit)}>Next prices</Link> : null}
      </nav> : null;
  return (
    <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}><main className="mvp-page">
      {moduleEnabled?<MarketDataNavigation active="explorer"/>:null}
      <header className="mvp-header"><div><p className="eyebrow">MARKET DATA CATALOGUE</p><h1>{selectedNodeId ? `${selectedName ?? "Instrument"} history` : "Series & provenance"}</h1><p className="muted">{selectedNodeId ? "Persisted observations, charted and chronologically sorted by market date." : "Precise observables with their provider, dataset, licence and named cut."}</p></div><span className={`synthetic-badge ${error ? "source-unavailable" : ""}`}>{sourceLabel}</span></header>
      <form className="date-form" method="get"><label>From <input type="date" name="fromDate" defaultValue={fromDate} /></label><label>To <input type="date" name="toDate" defaultValue={toDate} /></label>{selectedNodeId ? <input type="hidden" name="referenceNodeId" value={selectedNodeId} /> : null}{selectedSeriesId ? <input type="hidden" name="seriesId" value={selectedSeriesId} /> : null}<input type="hidden" name="observationLimit" value={observationLimit} /><button type="submit">Refresh window</button>{selectedNodeId ? <Link className="clear-link" href={`/market-data/explorer?fromDate=${encodeURIComponent(fromDate)}&toDate=${encodeURIComponent(toDate)}`}>Back to all series</Link> : null}</form>
      {personal ? <p className="muted">Yahoo personal-project history: Close is split adjusted; adjusted close includes the provider’s distribution adjustments. Neither is an official raw-price tape. Observed timestamps identify daily bars, not certified session closes. Personal-use declaration; no commercial or redistribution rights.</p> : null}
      {!error && selectedNodeId && !personal ? <MarketDataResolutionForm subjectReferenceNodeId={selectedNodeId} /> : null}

      {!error && !selectedNodeId ? <nav aria-label="Series catalogue pages"><p>{total ? `${offset+1}–${Math.min(offset+series.length,total)} of ${total} visible series` : 'No visible observations in this window. Choose another date range or check dataset access.'}</p>{offset > 0 ? <Link href={pageLink(Math.max(0,offset-limit),0)}>Previous series page</Link> : null}{offset+limit < total ? <Link href={pageLink(offset+limit,0)}>Next series page</Link> : null}</nav> : null}
      {error ? <div className="error-panel">{error}</div> : <section className="history-grid">{series.length ? series.map((item) => <HistoryPanel key={item.seriesId} series={item} pagination={pricePagination} />) : <div className="error-panel">No market-data series was found for this reference in the selected date window. This does not establish coverage outside this window.</div>}</section>}

    </main></WorkspaceShell>
  );
}
