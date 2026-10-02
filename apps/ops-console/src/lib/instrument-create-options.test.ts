import { describe, expect, it } from "vitest";

import { INSTRUMENT_CREATE_GROUPS } from "./instrument-create-options";

describe("instrument create options", () => {
  it("provides one instrument-focused launchpad without listing or index-family setup", () => {
    const paths = INSTRUMENT_CREATE_GROUPS.flatMap((group) => group.options.map((option) => option.href));

    expect(paths).toContain("/instruments/new");
    expect(paths).toContain("/instruments/swaps/new");
    expect(paths).toContain("/instruments/bonds/new");
    expect(paths).toContain("/instruments/funds/new");
    expect(paths).toContain("/instruments/indices/new");
    expect(paths).not.toContain("/instruments/listings/new");
    expect(paths).not.toContain("/instruments/index-families/new");
  });
});
