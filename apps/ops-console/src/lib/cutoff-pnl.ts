import { FUND_CUTOFF_SCENARIOS, type FundCutoffScenario } from "./market-data-cutoff";

export type CutoffPnlScenario = FundCutoffScenario & {
  reportingCurrency: "GBP" | "USD";
  localCurrency: "GBP" | "USD";
  priorMarketDate: string;
  selectedMarketDate: string;
  holdingLabel: string;
  quantity: number;
  unitMultiplier: number;
  quoteFactor: number;
  priorLocalPrice: number;
  selectedLocalPrice: number;
  priorFxRate: number;
  selectedFxRate: number;
  fxConversion: "DIRECT" | "INVERSE";
  fxQuote: string;
};

const UK_CUTOFF = FUND_CUTOFF_SCENARIOS[0];
const US_CUTOFF = FUND_CUTOFF_SCENARIOS[1];

/**
 * Illustrative positions make the cutoff effect visible in the MVP. They are
 * not a second source of truth: production P&L will receive frozen position,
 * price, and FX input snapshot items from the API.
 */
export const CUTOFF_PNL_SCENARIOS = {
  UK: {
    ...UK_CUTOFF,
    reportingCurrency: "GBP",
    localCurrency: "USD",
    priorMarketDate: "2026-08-27",
    selectedMarketDate: "2026-08-28",
    holdingLabel: "USD cash balance",
    quantity: 100000,
    unitMultiplier: 1,
    quoteFactor: 1,
    priorLocalPrice: 1,
    selectedLocalPrice: 1,
    priorFxRate: 1.354,
    selectedFxRate: 1.356,
    fxConversion: "INVERSE",
    fxQuote: "USD per GBP",
  },
  US: {
    ...US_CUTOFF,
    reportingCurrency: "USD",
    localCurrency: "GBP",
    priorMarketDate: "2026-08-27",
    selectedMarketDate: "2026-08-28",
    holdingLabel: "HSBC XLON ordinary shares",
    quantity: 1000,
    unitMultiplier: 1,
    quoteFactor: 100,
    priorLocalPrice: 1015,
    selectedLocalPrice: 1023,
    priorFxRate: 1.3552,
    selectedFxRate: 1.3588,
    fxConversion: "DIRECT",
    fxQuote: "USD per GBP",
  },
} as const satisfies Record<"UK" | "US", CutoffPnlScenario>;

export type CutoffPnlResult = {
  openingLocalValue: number;
  closingLocalValue: number;
  openingReportingValue: number;
  closingReportingValue: number;
  pricePnl: number;
  fxPnl: number;
  totalPnl: number;
};

export function calculateCutoffPnl(scenario: CutoffPnlScenario): CutoffPnlResult {
  const openingLocalValue = (scenario.quantity * scenario.priorLocalPrice * scenario.unitMultiplier) / scenario.quoteFactor;
  const closingLocalValue = (scenario.quantity * scenario.selectedLocalPrice * scenario.unitMultiplier) / scenario.quoteFactor;
  const openingReportingValue = scenario.fxConversion === "DIRECT"
    ? openingLocalValue * scenario.priorFxRate
    : openingLocalValue / scenario.priorFxRate;
  const closingReportingValue = scenario.fxConversion === "DIRECT"
    ? closingLocalValue * scenario.selectedFxRate
    : closingLocalValue / scenario.selectedFxRate;
  const pricePnl = scenario.fxConversion === "DIRECT"
    ? (closingLocalValue - openingLocalValue) * scenario.selectedFxRate
    : 0;
  const fxPnl = scenario.fxConversion === "DIRECT"
    ? openingLocalValue * (scenario.selectedFxRate - scenario.priorFxRate)
    : closingReportingValue - openingReportingValue;

  return {
    openingLocalValue,
    closingLocalValue,
    openingReportingValue,
    closingReportingValue,
    pricePnl,
    fxPnl,
    totalPnl: closingReportingValue - openingReportingValue,
  };
}
