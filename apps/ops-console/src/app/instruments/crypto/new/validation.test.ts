import { describe, expect, it } from "vitest";

import { validateCryptoAssetIdentity } from "./validation";

describe("validateCryptoAssetIdentity", () => {
  it("requires the canonical name, subtype, and native symbol", () => {
    expect(validateCryptoAssetIdentity("", "", "")).toEqual({
      canonicalName: expect.any(String),
      assetSubtype: expect.any(String),
      nativeSymbol: expect.any(String),
    });
  });

  it("accepts a canonical token identity", () => {
    expect(validateCryptoAssetIdentity("Synthetic USD Coin", "STABLECOIN", "USDC")).toEqual({});
  });
});
