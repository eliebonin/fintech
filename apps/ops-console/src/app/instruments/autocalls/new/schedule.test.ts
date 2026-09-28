import { describe, expect, it } from "vitest";

import {
  autocallLegSide,
  generateAutocallSchedule,
  groupComponentsByUnderlying,
  summarizeObservations,
  type ScheduleGenerationInput,
} from "./schedule";

const baseInput: ScheduleGenerationInput = {
  startDate: "2027-09-03",
  maturityDate: "2028-09-03",
  frequency: "ANNUAL",
  paymentLagBusinessDays: 2,
  couponRate: 6.5,
  couponBarrier: 100,
  autocallBarrierStart: 100,
  autocallBarrierStep: -10,
  autocallBarrierFloor: 0,
  kipBarrier: 65,
  scope: "WORST_OF",
  underlyings: [
    { referenceNodeId: "spx", label: "SPX Index", initialFixing: 7747.71, participation: 1 },
    { referenceNodeId: "sx5e", label: "SX5E Index", initialFixing: 6382.59, participation: 1 },
  ],
};

describe("generateAutocallSchedule", () => {
  it("maps signed component multipliers to autocall leg sides", () => {
    expect(autocallLegSide(1)).toBe("LONG");
    expect(autocallLegSide(-1)).toBe("SHORT");
    expect(autocallLegSide(0)).toBe("LONG");
    expect(autocallLegSide(null)).toBeNull();
  });

  it("generates coupon components, parent autocall levels, and maturity KIPs", () => {
    const result = generateAutocallSchedule(baseInput);

    expect(result.warnings).toEqual([]);
    expect(result.observationDates).toEqual(["2027-09-03", "2028-09-03"]);
    expect(result.rows).toHaveLength(8);

    const firstCoupon = result.rows.find((row) => row.groupCode === "COUPON_COMPONENT" && row.underlyingReferenceNodeId === "spx" && row.observationDate === "2027-09-03");
    expect(firstCoupon).toMatchObject({
      rowKind: "COMPONENT",
      groupCode: "COUPON_COMPONENT",
      componentKind: "DIGITAL",
      actionCode: "PAY_COMPONENT",
      participation: 1,
      couponRate: 6.5,
      strikeValue: 7747.71,
      strikePercent: 100,
      conditionLevel: 100,
      actionTarget: "COMPOSITION",
      conditionScope: "WORST_OF",
    });

    const maturityRedemption = result.rows.find((row) => row.rowKind === "ACTION" && row.observationDate === "2028-09-03");
    expect(maturityRedemption).toMatchObject({
      groupCode: "FINAL_REDEMPTION",
      actionCode: "FINAL_REDEMPTION",
      actionTarget: "PARENT",
      underlyingReferenceNodeId: null,
      conditionRole: "FINAL_REDEMPTION",
      conditionLevel: 0,
      conditionScope: "WORST_OF",
    });

    const kip = result.rows.find((row) => row.groupCode === "CAPITAL_PROTECTION" && row.underlyingReferenceNodeId === "spx");
    expect(kip).toMatchObject({
      rowKind: "COMPONENT",
      componentKind: "VANILLA_OPTION",
      optionType: "PUT",
      actionCode: "PAY_COMPONENT",
      participation: -1,
      observationDate: "2028-09-03",
      conditionLevel: 65,
      actionTarget: "COMPOSITION",
    });

    expect(result.rows.filter((row) => row.actionCode === "REDEEM_PARENT")).toHaveLength(1);
    expect(result.rows.filter((row) => row.actionCode === "REDEEM_PARENT").every((row) => row.underlyingReferenceNodeId === null)).toBe(true);
    expect(result.rows.filter((row) => row.actionCode === "FINAL_REDEMPTION")).toHaveLength(1);
  });

  it("adds a maturity consolation action for the KIP-to-final-payoff range", () => {
    const result = generateAutocallSchedule({
      ...baseInput,
      includeConsolation: true,
      consolationRate: 50,
    });

    const consolation = result.rows.find((row) => row.actionCode === "PAY_CONSOLATION");
    expect(consolation).toMatchObject({
      rowKind: "ACTION",
      groupCode: "CONSOLATION_ACTION",
      conditionRole: "CONSOLATION",
      conditionOperator: "RANGE",
      conditionLowerLevel: 65,
      conditionUpperLevel: 90,
      conditionLowerInclusive: true,
      conditionUpperInclusive: false,
      conditionLevel: 90,
      payoutRate: 50,
      observationDate: "2028-09-03",
      actionTarget: "PARENT",
      underlyingReferenceNodeId: null,
    });
    expect(result.rows.filter((row) => row.actionCode === "PAY_CONSOLATION")).toHaveLength(1);
  });

  it("uses an explicit consolation lower barrier when no KIP component is included", () => {
    const result = generateAutocallSchedule({
      ...baseInput,
      includeKip: false,
      includeConsolation: true,
      consolationLowerBarrier: 72,
      consolationRate: 50,
      finalPayoffBarrier: 90,
    });

    expect(result.warnings).toEqual([]);
    expect(result.rows.some((row) => row.groupCode === "CAPITAL_PROTECTION")).toBe(false);
    expect(result.rows.find((row) => row.actionCode === "PAY_CONSOLATION")).toMatchObject({
      conditionLowerLevel: 72,
      conditionUpperLevel: 90,
    });
  });

  it("places the final redemption fallback after maturity alternatives", () => {
    const result = generateAutocallSchedule({
      ...baseInput,
      includeConsolation: true,
      consolationRate: 50,
      finalPayoffBarrier: 90,
    });
    const consolationIndex = result.rows.findIndex((row) => row.actionCode === "PAY_CONSOLATION");
    const finalIndex = result.rows.findIndex((row) => row.actionCode === "FINAL_REDEMPTION");

    expect(consolationIndex).toBeGreaterThanOrEqual(0);
    expect(finalIndex).toBeGreaterThan(consolationIndex);
  });

  it("rejects a consolation rate outside the percentage range", () => {
    const result = generateAutocallSchedule({
      ...baseInput,
      includeConsolation: true,
      consolationRate: 120,
    });

    expect(result.rows).toEqual([]);
    expect(result.warnings).toContain("Consolation rate must be between 0 and 100 percent.");
  });

  it("uses business-day payment lag for generated payment dates", () => {
    const result = generateAutocallSchedule({
      ...baseInput,
      maturityDate: "2027-09-03",
      underlyings: [baseInput.underlyings[0]],
    });

    expect(result.rows[0].paymentDate).toBe("2027-09-07");
    expect(result.rows.find((row) => row.actionCode === "FINAL_REDEMPTION")?.paymentDate).toBe("2027-09-07");
  });

  it("keeps an off-cycle maturity as the final observation date", () => {
    const result = generateAutocallSchedule({
      ...baseInput,
      maturityDate: "2028-10-03",
      underlyings: [baseInput.underlyings[0]],
    });

    expect(result.observationDates.at(-1)).toBe("2028-10-03");
    expect(result.rows.some((row) => row.observationDate === "2028-10-03" && row.groupCode === "COUPON_COMPONENT")).toBe(true);
  });

  it("supports independent Phoenix coupon and autocall observation cadences", () => {
    const result = generateAutocallSchedule({
      ...baseInput,
      startDate: "2027-01-01",
      maturityDate: "2027-07-01",
      frequency: "ANNUAL",
      couponFrequency: "MONTHLY",
      autocallFrequency: "QUARTERLY",
      includeKip: false,
      underlyings: [baseInput.underlyings[0]],
    });

    expect(result.observationDates).toEqual([
      "2027-01-01",
      "2027-02-01",
      "2027-03-01",
      "2027-04-01",
      "2027-05-01",
      "2027-06-01",
      "2027-07-01",
    ]);
    expect(result.rows.filter((row) => row.groupCode === "COUPON_COMPONENT").map((row) => row.observationDate)).toEqual([
      "2027-01-01",
      "2027-02-01",
      "2027-03-01",
      "2027-04-01",
      "2027-05-01",
      "2027-06-01",
      "2027-07-01",
    ]);
    expect(result.rows.filter((row) => row.actionCode === "REDEEM_PARENT").map((row) => row.observationDate)).toEqual([
      "2027-01-01",
      "2027-04-01",
    ]);
    expect(result.rows.filter((row) => row.actionCode === "FINAL_REDEMPTION").map((row) => row.observationDate)).toEqual(["2027-07-01"]);
    expect(result.rows.filter((row) => row.actionCode === "REDEEM_PARENT").map((row) => row.conditionLevel)).toEqual([100, 90]);
  });

  it("follows the autocall barrier for coupon eligibility by default", () => {
    const result = generateAutocallSchedule({
      ...baseInput,
      startDate: "2027-01-01",
      maturityDate: "2027-07-01",
      frequency: "ANNUAL",
      couponFrequency: "MONTHLY",
      autocallFrequency: "QUARTERLY",
      couponBarrier: 70,
      autocallBarrierStart: 100,
      autocallBarrierStep: -10,
      includeKip: false,
      underlyings: [baseInput.underlyings[0]],
    });

    expect(result.rows.filter((row) => row.groupCode === "COUPON_COMPONENT").map((row) => row.conditionLevel)).toEqual([
      100, 100, 100, 90, 90, 90, 80,
    ]);
  });

  it("allows a fixed coupon barrier when inheritance is disabled", () => {
    const result = generateAutocallSchedule({
      ...baseInput,
      couponBarrier: 70,
      couponBarrierFollowsAutocall: false,
      includeKip: false,
      underlyings: [baseInput.underlyings[0]],
    });

    expect(result.rows.filter((row) => row.groupCode === "COUPON_COMPONENT").map((row) => row.conditionLevel)).toEqual([70, 70]);
  });

  it("keeps coupons during a non-call period but omits early redemption actions", () => {
    const result = generateAutocallSchedule({
      ...baseInput,
      startDate: "2027-01-01",
      maturityDate: "2027-07-01",
      frequency: "MONTHLY",
      firstAutocallObservationDate: "2027-04-01",
      includeKip: false,
      underlyings: [baseInput.underlyings[0]],
    });

    expect(result.rows.filter((row) => row.groupCode === "COUPON_COMPONENT").map((row) => row.observationDate)).toEqual([
      "2027-01-01", "2027-02-01", "2027-03-01", "2027-04-01", "2027-05-01", "2027-06-01", "2027-07-01",
    ]);
    expect(result.rows.filter((row) => row.actionCode === "REDEEM_PARENT").map((row) => row.observationDate)).toEqual([
      "2027-04-01", "2027-05-01", "2027-06-01",
    ]);
    expect(result.rows.filter((row) => row.actionCode === "FINAL_REDEMPTION")).toHaveLength(1);
  });

  it("rejects a non-call date outside the product life", () => {
    const result = generateAutocallSchedule({
      ...baseInput,
      firstAutocallObservationDate: "2029-01-01",
    });

    expect(result.rows).toEqual([]);
    expect(result.warnings).toContain("First autocall observation must fall between the start and maturity dates.");
  });

  it("returns actionable warnings instead of generating an incomplete contract", () => {
    const result = generateAutocallSchedule({
      ...baseInput,
      underlyings: [],
      maturityDate: "2027-01-01",
    });

    expect(result.rows).toEqual([]);
    expect(result.warnings).toContain("Add at least one underlying before generating the schedule.");
    expect(result.warnings).toContain("Maturity date must be on or after the observation start date.");
  });

  it("summarizes each observation without duplicating the parent action per underlying", () => {
    const result = generateAutocallSchedule(baseInput);

    expect(summarizeObservations(result.rows)).toEqual([
      {
        observationDate: "2027-09-03",
        paymentDate: "2027-09-07",
        conditionScope: "WORST_OF",
        couponBarrier: 100,
        autocallBarrier: 100,
        componentCount: 2,
        actionCount: 1,
        underlyingCount: 2,
        hasCapitalProtection: false,
      },
      {
        observationDate: "2028-09-03",
        paymentDate: "2028-09-05",
        conditionScope: "WORST_OF",
        couponBarrier: 90,
        autocallBarrier: null,
        componentCount: 4,
        actionCount: 1,
        underlyingCount: 2,
        hasCapitalProtection: true,
      },
    ]);
  });

  it("groups selected observation components by underlying for a compact detail view", () => {
    const result = generateAutocallSchedule(baseInput);
    const rows = result.rows.filter((row) => row.observationDate === "2028-09-03" && row.rowKind === "COMPONENT");

    expect(groupComponentsByUnderlying(rows)).toEqual([
      {
        key: "spx",
        label: "SPX Index",
        referenceNodeId: "spx",
        rows: [rows[0], rows[2]],
      },
      {
        key: "sx5e",
        label: "SX5E Index",
        referenceNodeId: "sx5e",
        rows: [rows[1], rows[3]],
      },
    ]);
  });
});
