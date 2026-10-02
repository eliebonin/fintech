import { describe, expect, it } from "vitest";

import { filterInstrumentCreationRequests } from "./instrument-requests";

describe("instrument request filtering", () => {
  it("keeps only pending economic-instrument creation proposals out of the cross-module queue", () => {
    const requests = filterInstrumentCreationRequests([
      { itemId: "reference:equity", category: "REFERENCE_DATA_REVIEW", status: "PENDING", proposalType: "CREATE" },
      { itemId: "reference:bond", category: "REFERENCE_DATA_REVIEW", status: "PENDING", proposalType: "CREATE_BOND" },
      { itemId: "reference:swap", category: "REFERENCE_DATA_REVIEW", status: "PENDING", proposalType: "CREATE_SWAP" },
      { itemId: "reference:listing", category: "REFERENCE_DATA_REVIEW", status: "PENDING", proposalType: "CREATE_LISTING" },
      { itemId: "reference:family", category: "REFERENCE_DATA_REVIEW", status: "PENDING", proposalType: "CREATE_INDEX_FAMILY" },
      { itemId: "mapping:one", category: "MAPPING_REVIEW", status: "PENDING" },
      { itemId: "nav:one", category: "NAV_REVIEW", status: "PENDING" },
    ]);

    expect(requests.map((request) => request.itemId)).toEqual(["reference:equity", "reference:bond", "reference:swap"]);
  });
});
