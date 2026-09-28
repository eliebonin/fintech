import { describe, expect, it } from "vitest";

import { validateBondIdentity } from "./validation";

describe("bond identity validation", () => {
  it("requires only a canonical name and coupon structure", () => {
    expect(validateBondIdentity("", "")).toEqual({
      canonicalName: "Enter the bond's official name.",
      couponType: "Select fixed-rate, zero-coupon, or floating-rate.",
    });
    expect(validateBondIdentity("Issuer 2031 Note", "FIXED")).toEqual({});
  });
});
