import { describe, expect, it } from "vitest";

import { fundOnboardingStages, validateFundDraft } from "./onboarding-model";

describe("fund onboarding model", () => {
  it("keeps the fund vehicle separate from the tradable share class and listing", () => {
    expect(fundOnboardingStages).toEqual([
      { key: "FUND", title: "Fund vehicle", tradable: false },
      { key: "SHARE_CLASS", title: "Share class", tradable: true },
      { key: "LISTING", title: "Venue listing", tradable: true },
    ]);
  });

  it("requires the fund vehicle name and domicile before a draft can continue", () => {
    expect(validateFundDraft({ canonicalName: "", domicileCountry: "" })).toEqual({
      canonicalName: "Enter the official fund or sub-fund name.",
      domicileCountry: "Select the fund domicile.",
    });
  });
});
