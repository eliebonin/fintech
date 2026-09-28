import { describe, expect, it } from "vitest";

import { validateFxForwardIdentity } from "./validation";

describe("FX-forward identity validation", () => {
  it("requires the contractual identity and rate fields", () => {
    expect(validateFxForwardIdentity("", "", "", "", "", "")).toEqual({
      canonicalName: "Enter a canonical name.",
      baseCurrencyId: "Choose a base currency.",
      quoteCurrencyId: "Choose a quote currency.",
      quoteConvention: "Enter a quote convention, for example USD_PER_GBP.",
      agreedForwardRate: "Enter a positive agreed forward rate.",
      maturityDate: "Choose the maturity date.",
    });
  });

  it("does not allow a same-currency forward", () => {
    expect(validateFxForwardIdentity("GBP/USD forward", "gbp", "gbp", "GBP_PER_GBP", "1", "2026-12-08").quoteCurrencyId)
      .toBe("Base and quote currencies must be different.");
  });

  it("accepts a complete base/quote contract", () => {
    expect(validateFxForwardIdentity("GBP/USD forward", "gbp", "usd", "USD_PER_GBP", "1.34", "2026-12-08")).toEqual({});
  });
});
