import { describe, expect, it } from "vitest";

import { productUiProfile, showsAutocallBarrierFloor, showsAutocallStepDownControls, showsMaturityConsolationControls } from "./product-profile";

describe("structured-product UI profiles", () => {
  it("uses a constant autocall barrier for Athena", () => {
    expect(productUiProfile("ATHENA")).toMatchObject({
      autocallBarrierStep: "0",
      constantAutocallBarrier: true,
    });
  });

  it("leaves Phoenix memory disabled until explicitly selected", () => {
    expect(productUiProfile("PHOENIX")).toMatchObject({
      autocallBarrierStep: "-10",
      constantAutocallBarrier: false,
    });
    expect(productUiProfile("PHOENIX").helperText).toContain("term sheet");
  });

  it("shows maturity consolation controls only for the governed subtype", () => {
    expect(showsMaturityConsolationControls("AUTOCALL_CONSOLATION")).toBe(true);
    expect(showsMaturityConsolationControls("AUTOCALL")).toBe(false);
    expect(showsMaturityConsolationControls("PHOENIX")).toBe(false);
    expect(showsMaturityConsolationControls("ATHENA")).toBe(false);
  });

  it("hides step-down controls for Athena", () => {
    expect(showsAutocallStepDownControls("ATHENA")).toBe(false);
    expect(showsAutocallStepDownControls("AUTOCALL")).toBe(true);
    expect(showsAutocallStepDownControls("AUTOCALL_CONSOLATION")).toBe(true);
    expect(showsAutocallStepDownControls("PHOENIX")).toBe(true);
  });

  it("shows the barrier floor only when a non-zero step-down is active", () => {
    expect(showsAutocallBarrierFloor("AUTOCALL", "-10")).toBe(true);
    expect(showsAutocallBarrierFloor("AUTOCALL_CONSOLATION", 5)).toBe(true);
    expect(showsAutocallBarrierFloor("AUTOCALL", "0")).toBe(false);
    expect(showsAutocallBarrierFloor("ATHENA", "-10")).toBe(false);
  });

  it("treats the first composed-option templates as non-autocall profiles", () => {
    expect(showsAutocallStepDownControls("VANILLA_SPREAD_KIP")).toBe(false);
    expect(showsMaturityConsolationControls("VANILLA_KIP")).toBe(false);
    expect(productUiProfile("DIGITAL_KIP").helperText).toContain("digital payout");
  });
});
