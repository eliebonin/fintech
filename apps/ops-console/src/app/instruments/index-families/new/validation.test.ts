import { describe, expect, it } from "vitest";

import { validateIndexFamily } from "./validation";

describe("validateIndexFamily", () => {
  it("requires a canonical family name", () => {
    expect(validateIndexFamily("", "")).toEqual({ canonicalName: expect.any(String) });
  });

  it("accepts a trimmed family name with an optional internal code", () => {
    expect(validateIndexFamily("  S&P 500  ", "SP500")).toEqual({});
  });
});
