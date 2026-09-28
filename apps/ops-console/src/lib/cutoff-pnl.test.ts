import { describe, expect, it } from "vitest";

import { CUTOFF_PNL_SCENARIOS, calculateCutoffPnl } from "./cutoff-pnl";

describe("cutoff P&L simulator", () => {
  it("converts a UK fund's USD cash balance using an inverse GBP/USD quote", () => {
    const result = calculateCutoffPnl(CUTOFF_PNL_SCENARIOS.UK);

    expect(result.openingReportingValue).toBeCloseTo(73855.24, 2);
    expect(result.closingReportingValue).toBeCloseTo(73746.31, 2);
    expect(result.pricePnl).toBe(0);
    expect(result.fxPnl).toBeCloseTo(-108.93, 2);
    expect(result.totalPnl).toBeCloseTo(-108.93, 2);
  });

  it("splits a US fund's GBP equity P&L into price and FX effects", () => {
    const result = calculateCutoffPnl(CUTOFF_PNL_SCENARIOS.US);

    expect(CUTOFF_PNL_SCENARIOS.US).toMatchObject({ priorMarketDate: "2026-08-27", selectedMarketDate: "2026-08-28" });
    expect(result.openingLocalValue).toBe(10150);
    expect(result.closingLocalValue).toBe(10230);
    expect(result.pricePnl).toBeCloseTo(108.704, 3);
    expect(result.fxPnl).toBeCloseTo(36.54, 2);
    expect(result.totalPnl).toBeCloseTo(145.244, 3);
  });
});
