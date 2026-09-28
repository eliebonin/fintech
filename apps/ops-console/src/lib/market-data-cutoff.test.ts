import { describe, expect, it } from "vitest";

import { FUND_CUTOFF_SCENARIOS } from "./market-data-cutoff";

describe("market-data cutoff fixture", () => {
  it("keeps the London and New York fund cut examples explicit", () => {
    expect(FUND_CUTOFF_SCENARIOS).toHaveLength(2);
    expect(FUND_CUTOFF_SCENARIOS).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          code: "UK_FUND_FX_1600_DEMO",
          timezone: "Europe/London",
          utcCut: "15:00 UTC",
          valueAtCut: "1.3560",
        }),
        expect.objectContaining({
          code: "US_FUND_FX_1600_DEMO",
          timezone: "America/New_York",
          utcCut: "20:00 UTC",
          valueAtCut: "1.3588",
        }),
      ]),
    );
  });
});
