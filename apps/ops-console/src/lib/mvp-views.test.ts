import { describe, expect, it } from "vitest";

import { formatMarketDataValue, sortObservationsChronologically, summarizeSeries } from "./market-data-series";

describe("market-data view helpers", () => {
  it("formats a market-data value and summarizes a series", () => {
    expect(formatMarketDataValue("1.27500000", "RATE")).toBe("1.275000");
    expect(summarizeSeries([{ marketDate: "2026-08-27", value: "1.2" }, { marketDate: "2026-08-28", value: "1.3" }])).toEqual({ first: "1.2", last: "1.3", points: 2 });
  });

  it("sorts a selected instrument's observations by market date", () => {
    const sorted = sortObservationsChronologically([
      { marketDate: "2026-08-28", value: "2" },
      { marketDate: "2026-08-26", value: "1" },
      { marketDate: "2026-08-27", value: "1.5" },
    ]);
    expect(sorted.map((item) => item.marketDate)).toEqual(["2026-08-26", "2026-08-27", "2026-08-28"]);
  });

});
