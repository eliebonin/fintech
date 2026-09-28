import { describe, expect, it } from "vitest";

import { formatMarketDataValue, sortObservationsChronologically, summarizeSeries } from "./market-data-series";
import { formatPnl, formatRate, pnlTone } from "./portfolio-pnl";

describe("MVP market-data and P&L view helpers", () => {
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

  it("formats P&L and assigns a stable visual tone", () => {
    expect(formatPnl("1234.5", "USD")).toBe("$1,234.50");
    expect(formatRate("1.2750000000")).toBe("1.275000");
    expect(pnlTone("-1")).toBe("negative");
    expect(pnlTone("0")).toBe("neutral");
  });
});
