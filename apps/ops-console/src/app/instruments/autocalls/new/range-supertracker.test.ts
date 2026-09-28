import { describe, expect, it } from "vitest";

import { generateRangeAccrualSchedule, generateSupertrackerSchedule } from "./range-supertracker";

const underlying = {
  referenceNodeId: "00000000-0000-7000-8000-000000000101",
  label: "S&P 500",
  initialFixing: 5000,
  participation: 1,
};

describe("range-accrual schedule generation", () => {
  it("creates one bounded coupon component per period plus parent maturity redemption", () => {
    const result = generateRangeAccrualSchedule({
      startDate: "2027-01-01",
      maturityDate: "2028-01-01",
      couponFrequency: "QUARTERLY",
      paymentLagBusinessDays: 2,
      couponRatePerAnnum: 8,
      lowerLevel: 70,
      upperLevel: 130,
      observationFrequency: "DAILY",
      accrualBasis: "OBSERVATION_COUNT",
      nonBusinessDayRule: "BUSINESS_DAYS_ONLY",
      scope: "SINGLE",
      underlyings: [underlying],
    });

    expect(result.warnings).toEqual([]);
    expect(result.rangeObservationFrequency).toBe("DAILY");
    expect(result.rows.filter((row) => row.conditionRole === "COUPON_ELIGIBILITY")).toHaveLength(4);
    expect(result.rows.filter((row) => row.conditionRole === "COUPON_ELIGIBILITY").every((row) => row.conditionOperator === "RANGE" && row.conditionLowerLevel === 70 && row.conditionUpperLevel === 130 && row.couponRate === null)).toBe(true);
    expect(result.rows.at(-1)?.actionCode).toBe("FINAL_REDEMPTION");
  });

  it("fails closed when the range is not ordered", () => {
    const result = generateRangeAccrualSchedule({
      startDate: "2027-01-01",
      maturityDate: "2028-01-01",
      couponFrequency: "ANNUAL",
      paymentLagBusinessDays: 0,
      couponRatePerAnnum: 8,
      lowerLevel: 130,
      upperLevel: 70,
      observationFrequency: "DAILY",
      accrualBasis: "CALENDAR_DAYS",
      nonBusinessDayRule: "CALENDAR_DAYS",
      scope: "SINGLE",
      underlyings: [underlying],
    });

    expect(result.rows).toEqual([]);
    expect(result.warnings.some((warning) => warning.toLowerCase().includes("upper"))).toBe(true);
  });
});

describe("supertracker schedule generation", () => {
  it("represents leverage, cap, KIP, and maturity redemption as separate graph rows", () => {
    const result = generateSupertrackerSchedule({
      startDate: "2027-01-01",
      maturityDate: "2028-01-01",
      paymentLagBusinessDays: 2,
      participationRate: 135,
      includeCap: true,
      capReturn: 25,
      kipBarrier: 65,
      includeKip: true,
      kipObservationStyle: "CONTINUOUS",
      scope: "SINGLE",
      underlyings: [underlying],
    });

    expect(result.warnings).toEqual([]);
    const optionRows = result.rows.filter((row) => row.conditionRole === "OPTION_PAYOFF");
    expect(optionRows).toHaveLength(2);
    expect(optionRows.map((row) => row.participation)).toEqual([1.35, -1.35]);
    expect(optionRows.map((row) => row.strikePercent)).toEqual([100, 125]);
    expect(result.rows.find((row) => row.conditionRole === "CAPITAL_PROTECTION")?.participation).toBe(-1);
    expect(result.rows.find((row) => row.actionCode === "FINAL_REDEMPTION")).toBeDefined();
  });

  it("does not silently model a multi-underlying worst-of payoff", () => {
    const result = generateSupertrackerSchedule({
      startDate: "2027-01-01",
      maturityDate: "2028-01-01",
      paymentLagBusinessDays: 0,
      participationRate: 135,
      includeCap: false,
      kipBarrier: 65,
      scope: "WORST_OF",
      underlyings: [underlying, { ...underlying, referenceNodeId: "00000000-0000-7000-8000-000000000102", label: "EURO STOXX 50" }],
    });

    expect(result.rows).toEqual([]);
    expect(result.warnings.some((warning) => warning.includes("first supertracker slice"))).toBe(true);
  });
});
