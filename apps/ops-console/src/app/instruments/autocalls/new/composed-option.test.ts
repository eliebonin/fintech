import { describe, expect, it } from "vitest";

import { generateComposedOptionSchedule, type ComposedOptionLeg } from "./composed-option";

const UNDERLYING = {
  referenceNodeId: "00000000-0000-7000-8000-000000000101",
  label: "Demo equity",
  initialFixing: 100,
  participation: 1,
};

function leg(overrides: Partial<ComposedOptionLeg> = {}): ComposedOptionLeg {
  return {
    legId: "leg-1",
    referenceNodeId: UNDERLYING.referenceNodeId,
    underlyingLabel: UNDERLYING.label,
    initialFixing: UNDERLYING.initialFixing,
    optionType: "CALL",
    strikePercent: 100,
    participation: 1,
    payoutRate: null,
    ...overrides,
  };
}

function input(template: "VANILLA_SPREAD_KIP" | "VANILLA_KIP" | "DIGITAL_KIP", legs: ComposedOptionLeg[]) {
  return {
    template,
    startDate: "2027-01-01",
    maturityDate: "2028-01-01",
    paymentLagBusinessDays: 2,
    kipBarrier: 65,
    scope: "SINGLE" as const,
    underlyings: [UNDERLYING],
    legs,
  };
}

describe("composed option schedule projection", () => {
  it("creates a signed call spread and a separate KIP component", () => {
    const result = generateComposedOptionSchedule(input("VANILLA_SPREAD_KIP", [
      leg({ legId: "long-call", participation: 1, strikePercent: 100 }),
      leg({ legId: "short-call", participation: -1, strikePercent: 110 }),
    ]));

    expect(result.warnings).toEqual([]);
    expect(result.observationDates).toEqual(["2028-01-01"]);
    expect(result.rows).toHaveLength(3);
    expect(result.rows.filter((row) => row.conditionRole === "OPTION_PAYOFF")).toHaveLength(2);
    expect(result.rows.find((row) => row.rowId === "OPTION:short-call:2028-01-01")?.participation).toBe(-1);
    expect(result.rows.find((row) => row.groupCode === "CAPITAL_PROTECTION")?.conditionLevel).toBe(65);
    expect(result.rows.find((row) => row.groupCode === "CAPITAL_PROTECTION")?.observationStyle).toBe("CONTINUOUS");
    expect(result.rows.find((row) => row.groupCode === "CAPITAL_PROTECTION")?.paymentDate).toBe("2028-01-04");
  });

  it("creates one vanilla option payoff and a maturity KIP component", () => {
    const result = generateComposedOptionSchedule(input("VANILLA_KIP", [leg({ optionType: "PUT", strikePercent: 95, participation: 1 })]));

    expect(result.rows).toHaveLength(2);
    expect(result.rows[0]).toMatchObject({
      componentKind: "VANILLA_OPTION",
      optionType: "PUT",
      conditionRole: "OPTION_PAYOFF",
      conditionLevel: null,
      strikeValue: 95,
    });
    expect(result.rows[1]).toMatchObject({
      componentKind: "VANILLA_OPTION",
      optionType: "PUT",
      conditionRole: "CAPITAL_PROTECTION",
      participation: -1,
      strikePercent: 65,
      observationStyle: "CONTINUOUS",
    });
  });

  it("creates a digital payout with a configurable payout rate and KIP", () => {
    const result = generateComposedOptionSchedule(input("DIGITAL_KIP", [leg({
      optionType: "DIGITAL",
      payoutRate: 12.5,
    })]));

    expect(result.rows).toHaveLength(2);
    expect(result.rows[0]).toMatchObject({
      componentKind: "DIGITAL",
      optionType: "DIGITAL",
      conditionRole: "OPTION_PAYOFF",
      payoutRate: 12.5,
    });
    expect(result.rows[1].conditionRole).toBe("CAPITAL_PROTECTION");
  });

  it("fails closed for an incomplete digital payoff and an invalid single-underlying scope", () => {
    const result = generateComposedOptionSchedule({
      ...input("DIGITAL_KIP", [leg({ optionType: "DIGITAL", payoutRate: null })]),
      underlyings: [
        UNDERLYING,
        { ...UNDERLYING, referenceNodeId: "00000000-0000-7000-8000-000000000102", label: "Second equity" },
      ],
    });

    expect(result.rows).toEqual([]);
    expect(result.warnings).toEqual(expect.arrayContaining([
      "SINGLE scope requires exactly one underlying.",
      "Digital payoff requires a payout rate between 0 and 100 percent.",
    ]));
  });

  it("requires a genuine vertical spread shape", () => {
    const result = generateComposedOptionSchedule(input("VANILLA_SPREAD_KIP", [
      leg({ legId: "first", participation: 1, optionType: "CALL", strikePercent: 100 }),
      leg({ legId: "second", participation: 1, optionType: "PUT", strikePercent: 110 }),
    ]));

    expect(result.rows).toEqual([]);
    expect(result.warnings).toEqual(expect.arrayContaining([
      "A vanilla spread requires the two payoff legs to use the same option type.",
      "A vanilla spread requires one long and one short signed leg.",
    ]));
  });
});
