import { describe, expect, it } from "vitest";

import { validateEtpIdentity } from "./validation";

describe("validateEtpIdentity", () => {
  it("requires the economic identity and wrapper choices", () => {
    expect(validateEtpIdentity("", "", "", "")).toEqual({
      canonicalName: expect.any(String),
      etpKind: expect.any(String),
      legalForm: expect.any(String),
      redemptionModel: expect.any(String),
    });
  });

  it("accepts a physical accumulating UCITS ETF", () => {
    expect(validateEtpIdentity("Example World UCITS ETF", "ETF", "UCITS_FUND", "OPEN_ENDED")).toEqual({});
  });
});
