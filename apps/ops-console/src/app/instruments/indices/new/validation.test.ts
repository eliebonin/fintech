import { describe, expect, it } from "vitest";

import { validateIndexIdentity } from "./validation";

describe("validateIndexIdentity", () => {
  it("requires the canonical name and index kind", () => {
    expect(validateIndexIdentity("", "")).toEqual({
      canonicalName: expect.any(String),
      indexKind: expect.any(String),
    });
  });

  it("accepts a concrete public index variant", () => {
    expect(validateIndexIdentity("S&P 500 Price Return", "PUBLIC")).toEqual({});
  });
});
