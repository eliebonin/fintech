import { describe, expect, it } from "vitest";

import { getCataloguePage } from "./instrument-catalogue-pagination";

describe("instrument catalogue pagination", () => {
  it("derives an API offset and stable page bounds from the total result count", () => {
    expect(getCataloguePage({ page: 3, pageSize: 25, total: 87 })).toEqual({
      offset: 50,
      pageCount: 4,
      firstResult: 51,
      lastResult: 75,
    });
  });

  it("keeps an empty result set on its first page", () => {
    expect(getCataloguePage({ page: 1, pageSize: 25, total: 0 })).toEqual({
      offset: 0,
      pageCount: 1,
      firstResult: 0,
      lastResult: 0,
    });
  });
});
