export type PortfolioPnlLine = {
  instrumentId: string;
  listingId: string | null;
  instrumentName: string;
  instrumentType: string;
  quantity: string;
  localCurrency: string | null;
  baseCurrency: string | null;
  openingPrice: string | null;
  closingPrice: string | null;
  openingFx: string;
  closingFx: string;
  localPricePnl: string;
  fxPnl: string;
  totalPnl: string;
  priceSeriesId: string | null;
  closingObservationId: string | null;
};

export type PortfolioPnlPayload = {
  data: {
    portfolioCode: string;
    portfolioName: string;
    asOfDate: string;
    baseCurrency: string;
    valuationCut: { cutCode: string | null; displayName: string | null; timezoneName: string | null; localTime: string | null };
    lines: PortfolioPnlLine[];
    totalPnl: string;
    methodology: string;
  };
  meta: { source: string; apiVersion: string; correlationId: string };
};

export function formatPnl(value: string, currency: string): string {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return value;
  return new Intl.NumberFormat("en-GB", { style: "currency", currency, currencyDisplay: "narrowSymbol", maximumFractionDigits: 2 }).format(parsed);
}

export function formatRate(value: string | null): string {
  if (value == null) return "—";
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return value;
  return parsed.toLocaleString("en-GB", { minimumFractionDigits: 6, maximumFractionDigits: 6 });
}

export function pnlTone(value: string): "positive" | "negative" | "neutral" {
  const parsed = Number(value);
  if (parsed > 0) return "positive";
  if (parsed < 0) return "negative";
  return "neutral";
}
