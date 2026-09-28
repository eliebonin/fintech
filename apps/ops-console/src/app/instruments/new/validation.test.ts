import { describe, expect, it } from "vitest";

import { validateEquityIdentity } from "./validation";

describe("equity onboarding identity validation", () => {
  it("returns a field-specific canonical-name message instead of browser generic validation", () => {
    expect(validateEquityIdentity("", "")).toEqual({
      canonicalName: "Enter the official name of the economic security, for example Acme plc Ordinary Shares.",
    });
  });

  it("does not require an internal code", () => {
    expect(validateEquityIdentity("Acme plc Ordinary Shares", "")).toEqual({});
  });
});
