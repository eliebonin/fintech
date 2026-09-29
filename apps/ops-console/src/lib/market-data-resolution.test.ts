import { describe, expect, it } from "vitest";

import { formatResolutionTimestamp, resolutionStatusLabel } from "./market-data-resolution";

describe("market-data resolution evidence formatting", () => {
  it("labels frozen outcomes without evaluating live data", () => {
    expect(resolutionStatusLabel("DENIED")).toBe("Denied");
    expect(resolutionStatusLabel("SELECTED")).toBe("Selected");
  });

  it("formats frozen UTC timestamps and null evidence safely", () => {
    expect(formatResolutionTimestamp(null)).toBe("—");
    expect(formatResolutionTimestamp("2026-08-28T16:00:00Z")).toBe("2026-08-28 16:00:00Z");
  });
});
