export type FundCutoffScenario = {
  code: string;
  label: string;
  timezone: string;
  localCut: string;
  utcCut: string;
  fxPair: string;
  valueAtCut: string;
  laterValue: string;
  laterReceivedUtc: string;
};

/**
 * Small, explicitly synthetic fixture for the MVP cutoff callout. The source
 * of truth remains the database fixture and resolver; this DTO only gives the
 * UI a safe, readable summary until a dedicated cutoff endpoint is added.
 */
export const FUND_CUTOFF_SCENARIOS: FundCutoffScenario[] = [
  {
    code: "UK_FUND_FX_1600_DEMO",
    label: "UK fund",
    timezone: "Europe/London",
    localCut: "16:00 local",
    utcCut: "15:00 UTC",
    fxPair: "GBP/USD",
    valueAtCut: "1.3560",
    laterValue: "1.3570",
    laterReceivedUtc: "15:05 UTC",
  },
  {
    code: "US_FUND_FX_1600_DEMO",
    label: "US fund",
    timezone: "America/New_York",
    localCut: "16:00 local",
    utcCut: "20:00 UTC",
    fxPair: "GBP/USD",
    valueAtCut: "1.3588",
    laterValue: "1.3601",
    laterReceivedUtc: "20:05 UTC",
  },
];
