import { describe, expect, it } from "vitest";

import { INSTRUMENT_CATALOGUE_COLUMNS } from "./instrument-catalogue-view";

describe("instrument catalogue overview", () => {
  it("keeps the collection scan focused on the five fields needed to identify an instrument", () => {
    expect(INSTRUMENT_CATALOGUE_COLUMNS.map((column) => column.key)).toEqual([
      "canonicalName",
      "instrumentType",
      "baseCurrency",
      "status",
      "listingCount",
    ]);
  });
});
