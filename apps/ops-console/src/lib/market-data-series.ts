export type MarketDataObservation = {
  observationId: string;
  marketDate: string | null;
  observedAt: string;
  receivedAt: string;
  value: string;
  valueBasis: string;
  qualityStatus: string;
  providerId: string | null;
  providerCode: string | null;
  datasetId: string;
  datasetCode: string;
  licenceId: string | null;
  licenceCode: string | null;
  vintageId: string | null;
  vintageKey: string | null;
  sourcePublishedAt: string | null;
  sourceObservationKey: string | null;
};

export type MarketDataSeries = {
  seriesId: string;
  referenceNodeId: string;
  referenceNodeName: string;
  seriesType: string;
  valueType: string;
  currency: string | null;
  providerId: string | null;
  providerCode: string | null;
  providerName: string | null;
  datasetId: string | null;
  datasetCode: string | null;
  datasetName: string | null;
  licenceId: string | null;
  licenceCode: string | null;
  licenceName: string | null;
  valuationCut: string | null;
  timezoneName: string | null;
  expectedFrequency: string;
  expectedCalendarId: string | null;
  expectedCalendarCode: string | null;
  coverageStartDate: string | null;
  coverageEndDate: string | null;
  observations: MarketDataObservation[];
  observationTotal?: number;
  observationLimit?: number;
  observationOffset?: number;
};

export type MarketDataSeriesPayload = {
  data: MarketDataSeries[];
  meta: { source: string; apiVersion: string; correlationId: string; total?: number };
};

export function formatMarketDataValue(value: string, valueType: string): string {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return value;
  return parsed.toLocaleString("en-GB", { minimumFractionDigits: valueType === "RATE" ? 6 : 0, maximumFractionDigits: valueType === "RATE" ? 6 : 4 });
}

export function summarizeSeries(observations: Array<Pick<MarketDataObservation, "marketDate" | "value">>) {
  return { first: observations[0]?.value ?? "—", last: observations.at(-1)?.value ?? "—", points: observations.length };
}

export function sortObservationsChronologically<T extends Pick<MarketDataObservation, "marketDate">>(observations: T[]): T[] {
  return [...observations].sort((left, right) => (left.marketDate ?? "").localeCompare(right.marketDate ?? ""));
}
