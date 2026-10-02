import "server-only";

import type { TenantContext } from "./tenant-types";
import type { MarketDataSeriesPayload } from "./market-data-series";
import type { PortfolioPnlPayload } from "./portfolio-pnl";
import type { TradeDetailPayload, TradePayload } from "./trades";
import type { InstrumentRecord } from "./instrument-data";

export type InstrumentDetailPayload = {
  data: InstrumentRecord;
  meta: { correlationId?: string; [key: string]: unknown };
};

export class MvpApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly code?: string,
    public readonly correlationId?: string,
  ) {
    super(message);
    this.name = "MvpApiError";
  }
}

export function describeMvpError(error: unknown, resource: string): string {
  if (error instanceof MvpApiError) {
    if (error.status === 404) return `${resource} was not found for the current tenant.`;
    if (error.status === 401 || error.status === 403) return `You are not authorised to view this ${resource.toLowerCase()}.`;
    if (error.status === 400 || error.status === 422) return `The requested ${resource.toLowerCase()} query is invalid.`;
    if (error.status === 409) return `The ${resource.toLowerCase()} is in a conflicting state.`;
    if (error.status >= 500) return `The ${resource.toLowerCase()} service is unavailable.`;
  }
  return `The ${resource.toLowerCase()} could not be loaded.`;
}

const apiBase = () => process.env.REFERENCE_API_URL ?? "http://localhost:8000";

async function getJson<T>(path: string, context: TenantContext, fetchImpl: typeof fetch = fetch): Promise<T> {
  const response = await fetchImpl(new URL(path, apiBase()), {
    cache: "no-store",
    headers: { Accept: "application/json", "X-Tenant-Id": context.tenantId, "X-User-Account-Id": context.userAccountId },
  });
  if (!response.ok) {
    let message = `Reference API returned HTTP ${response.status}`;
    let code: string | undefined;
    let correlationId = response.headers.get("X-Correlation-Id") ?? undefined;
    try {
      const body = await response.json() as Record<string, unknown>;
      const envelope = body.error && typeof body.error === "object" && !Array.isArray(body.error)
        ? body.error as Record<string, unknown>
        : body;
      if (typeof envelope.message === "string") message = envelope.message;
      else if (typeof body.detail === "string") message = body.detail;
      if (typeof envelope.code === "string") code = envelope.code;
      if (typeof envelope.correlationId === "string") correlationId = envelope.correlationId;
    } catch {
      // Keep the safe status-derived message for non-JSON responses.
    }
    throw new MvpApiError(response.status, message, code, correlationId);
  }
  return (await response.json()) as T;
}

export function getInstrument(context: TenantContext, instrumentId: string, fetchImpl: typeof fetch = fetch) {
  return getJson<InstrumentDetailPayload>(`/v1/instruments/${encodeURIComponent(instrumentId)}`, context, fetchImpl);
}

export function getMarketDataSeries(context: TenantContext, params: { fromDate?: string; toDate?: string; limit?: number; referenceNodeId?: string } = {}) {
  const query = new URLSearchParams();
  if (params.fromDate) query.set("fromDate", params.fromDate);
  if (params.toDate) query.set("toDate", params.toDate);
  if (params.referenceNodeId) query.set("referenceNodeId", params.referenceNodeId);
  query.set("limit", String(params.limit ?? 12));
  return getJson<MarketDataSeriesPayload>(`/v1/market-data/series?${query.toString()}`, context);
}

export function getPortfolioPnl(context: TenantContext, portfolioCode: string, asOfDate: string) {
  return getJson<PortfolioPnlPayload>(`/v1/portfolios/${encodeURIComponent(portfolioCode)}/pnl?asOfDate=${encodeURIComponent(asOfDate)}`, context);
}

export function getBookedTrades(context: TenantContext, params: { portfolioCode?: string; fromDate?: string; toDate?: string; q?: string; side?: string; lifecycleStatus?: string; limit?: number; offset?: number } = {}) {
  const query = new URLSearchParams();
  if (params.portfolioCode) query.set("portfolioCode", params.portfolioCode);
  if (params.fromDate) query.set("fromDate", params.fromDate);
  if (params.toDate) query.set("toDate", params.toDate);
  if (params.q) query.set("q", params.q);
  if (params.side) query.set("side", params.side);
  if (params.lifecycleStatus) query.set("lifecycleStatus", params.lifecycleStatus);
  query.set("offset", String(params.offset ?? 0));
  query.set("limit", String(params.limit ?? 50));
  return getJson<TradePayload>(`/v1/trades?${query.toString()}`, context);
}

export function getBookedTradeDetail(context: TenantContext, tradeId: string) {
  return getJson<TradeDetailPayload>(`/v1/trades/${encodeURIComponent(tradeId)}`, context);
}

export type HistoryStrategy = { strategyId: string; strategyCode: string; displayName: string; status: string };
export function getHistoryStrategies(context: TenantContext) {
  return getJson<{ data: HistoryStrategy[] }>("/v1/strategies", context);
}
