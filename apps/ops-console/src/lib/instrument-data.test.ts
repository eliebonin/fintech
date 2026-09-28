import { describe, expect, it } from "vitest";

import { searchInstruments } from "./instrument-data";

describe("instrument search contract", () => {
  it("finds the HSBC economic instrument and preserves listing context", () => {
    const results = searchInstruments("HSBC");

    expect(results).toHaveLength(1);
    expect(results[0]).toMatchObject({
      canonicalName: "HSBC Holdings plc ordinary shares",
      instrumentType: "EQUITY",
      listings: expect.arrayContaining([
        expect.objectContaining({ marketVenueMic: "XLON", tradingSymbol: "HSBA" }),
      ]),
    });
  });

  it("returns an empty result for an unknown identifier", () => {
    expect(searchInstruments("not-a-real-security")).toEqual([]);
  });
});
