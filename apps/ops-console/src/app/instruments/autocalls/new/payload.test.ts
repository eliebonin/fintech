import { describe, expect, it } from "vitest";

import { buildAutocallDraftPayload, type AutocallFormPayloadInput } from "./payload";
import type { ScheduleDraftRow } from "./draft";

const CALENDAR_ID = "00000000-0000-7000-8000-000000000128";
const UNDERLYING_ID = "00000000-0000-7000-8000-000000000101";
const CURRENCY_ID = "00000000-0000-7000-8000-000000000201";

function row(overrides: Partial<ScheduleDraftRow> = {}): ScheduleDraftRow {
  return {
    rowId: "ACTION:PAY_CONSOLATION:2028-01-01",
    draftRowId: "draft:consolation",
    sourceRowId: "ACTION:PAY_CONSOLATION:2028-01-01",
    rowState: "GENERATED",
    dirtyFields: [],
    rowKind: "ACTION",
    groupCode: "CONSOLATION_ACTION",
    groupLabel: "Maturity consolation",
    legId: 2,
    componentKind: "PARENT_ACTION",
    optionType: null,
    exerciseStyle: null,
    conditionRole: "CONSOLATION",
    conditionOperator: "RANGE",
    conditionScope: "SINGLE",
    underlyingReferenceNodeId: null,
    underlyingLabel: "Single reference",
    participation: null,
    couponRate: null,
    strikeValue: null,
    strikePercent: null,
    observationDate: "2028-01-01",
    paymentDate: "2028-01-03",
    conditionLevel: 90,
    conditionLowerLevel: 65,
    conditionUpperLevel: 90,
    conditionLevelBasis: "PCT_OF_INITIAL",
    payoutRate: 50,
    actionCode: "PAY_CONSOLATION",
    actionTarget: "PARENT",
    ...overrides,
  };
}

function input(overrides: Partial<AutocallFormPayloadInput> = {}): AutocallFormPayloadInput {
  return {
    productName: "Demo consolation autocall",
    internalCode: "SP_DEMO_CONSOLATION",
    productType: "AUTOCALL_CONSOLATION",
    currencyId: CURRENCY_ID,
    issuerOrganisationId: "",
    guarantorOrganisationId: "",
    counterpartyOrganisationId: "",
    notional: "1000000",
    scope: "SINGLE",
    observationStyle: "DISCRETE",
    memoryMode: "NONE",
    calendarId: CALENDAR_ID,
    effectiveDate: "2026-01-01",
    startDate: "2027-01-01",
    maturityDate: "2028-01-01",
    frequency: "ANNUAL",
    paymentLagBusinessDays: "2",
    couponRate: "6.5",
    couponBarrier: "70",
    autocallBarrierStart: "100",
    autocallBarrierStep: "-10",
    autocallBarrierFloor: "70",
    kipBarrier: "65",
    finalPayoffBarrier: "",
    consolationLowerBarrier: "",
    includeKip: true,
    includeConsolation: false,
    consolationRate: "50",
    underlyings: [{
      referenceNodeId: UNDERLYING_ID,
      label: "Demo equity",
      initialFixing: 100,
      participation: 1,
      fixingBasis: "LEVEL",
    }],
    rows: [row()],
    ...overrides,
  };
}

describe("structured-product draft payload", () => {
  it("maps the consolation subtype and contract graph fields to the API shape", () => {
    const payload = buildAutocallDraftPayload(input());

    expect(payload.productSubtype).toBe("AUTOCALL_CONSOLATION");
    expect(payload.includeConsolation).toBe(true);
    expect(payload.finalPayoffBarrier).toBe(90);
    expect(payload.calendarId).toBe(CALENDAR_ID);
    expect(payload.effectiveFrom).toBe("2026-01-01");
    expect(payload.underlyings).toEqual([expect.objectContaining({
      referenceNodeId: UNDERLYING_ID,
      initialFixing: 100,
      fixingDate: "2027-01-01",
      fixingBasis: "LEVEL",
      fixingSource: "MANUAL",
    })]);
    expect(payload.rows[0]).toEqual(expect.objectContaining({
      rowId: "ACTION:PAY_CONSOLATION:2028-01-01",
      conditionOperator: "RANGE",
      conditionLowerInclusive: true,
      conditionUpperInclusive: false,
      actionCode: "PAY_CONSOLATION",
      actionTarget: "PARENT",
    }));
  });

  it("carries an independent consolation lower barrier when KIP is disabled", () => {
    const payload = buildAutocallDraftPayload(input({
      includeKip: false,
      kipBarrier: "0",
      consolationLowerBarrier: "72",
      finalPayoffBarrier: "90",
    }));

    expect(payload.consolationLowerBarrier).toBe(72);
    expect(payload.includeKip).toBe(false);
  });

  it("does not turn a blank no-KIP lower barrier into an implicit zero", () => {
    const payload = buildAutocallDraftPayload(input({
      includeKip: false,
      kipBarrier: "0",
      consolationLowerBarrier: "",
      rows: [],
    }));

    expect(Object.prototype.hasOwnProperty.call(payload, "consolationLowerBarrier")).toBe(false);
  });

  it("keeps a standard autocall without consolation when the subtype is standard", () => {
    const payload = buildAutocallDraftPayload(input({ productType: "AUTOCALL", includeConsolation: false }));

    expect(payload.productSubtype).toBe("AUTOCALL");
    expect(payload.includeConsolation).toBe(false);
    expect(payload.issuerOrganisationId).toBeUndefined();
    expect(payload.notionalAmount).toBe(1000000);
  });

  it("carries independent Phoenix coupon and autocall frequencies", () => {
    const payload = buildAutocallDraftPayload(input({
      productType: "PHOENIX",
      couponFrequency: "MONTHLY",
      autocallFrequency: "QUARTERLY",
    }));

    expect(payload.frequency).toBe("ANNUAL");
    expect(payload.couponFrequency).toBe("MONTHLY");
    expect(payload.autocallFrequency).toBe("QUARTERLY");
  });

  it("carries the coupon-barrier inheritance default and explicit override", () => {
    expect(buildAutocallDraftPayload(input()).couponBarrierFollowsAutocall).toBe(true);
    expect(buildAutocallDraftPayload(input({ couponBarrierFollowsAutocall: false })).couponBarrierFollowsAutocall).toBe(false);
  });

  it("carries the first eligible autocall date and final coupon treatment", () => {
    const payload = buildAutocallDraftPayload(input({
      productType: "PHOENIX",
      memoryMode: "CONDITIONAL_CATCH_UP",
      firstAutocallObservationDate: "2027-04-01",
      finalPaymentTreatment: "INCLUDE_IN_REDEMPTION",
    }));

    expect(payload.firstAutocallObservationDate).toBe("2027-04-01");
    expect(payload.finalPaymentTreatment).toBe("INCLUDE_IN_REDEMPTION");
  });

  it("treats final coupon treatment as inactive when memory is disabled", () => {
    const payload = buildAutocallDraftPayload(input({
      memoryMode: "NONE",
      finalPaymentTreatment: "INCLUDE_IN_REDEMPTION",
    }));

    expect(payload.finalPaymentTreatment).toBeNull();
  });

  it("preserves composed-option template rows and KIP observation convention", () => {
    const payload = buildAutocallDraftPayload(input({
      productType: "VANILLA_KIP",
      observationStyle: "FINAL_ONLY",
      rows: [
        row({
          rowId: "option-leg",
          draftRowId: "draft:option-leg",
          sourceRowId: "option-leg",
          rowKind: "COMPONENT",
          groupCode: "OPTION_LEG",
          groupLabel: "Option payoff legs",
          componentKind: "VANILLA_OPTION",
          optionType: "CALL",
          conditionRole: "OPTION_PAYOFF",
          conditionLevel: null,
          observationStyle: "FINAL_ONLY",
          actionCode: "PAY_COMPONENT",
          actionTarget: "COMPOSITION",
          underlyingReferenceNodeId: UNDERLYING_ID,
          underlyingLabel: "Demo equity",
          participation: 1,
          strikeValue: 100,
          strikePercent: 100,
          observationDate: "2028-01-01",
          paymentDate: "2028-01-03",
        }),
        row({
          rowId: "kip-leg",
          draftRowId: "draft:kip-leg",
          sourceRowId: "kip-leg",
          rowKind: "COMPONENT",
          groupCode: "CAPITAL_PROTECTION",
          groupLabel: "Knock-in put protection",
          componentKind: "VANILLA_OPTION",
          optionType: "PUT",
          conditionRole: "CAPITAL_PROTECTION",
          conditionLevel: 65,
          observationStyle: "CONTINUOUS",
          actionCode: "PAY_COMPONENT",
          actionTarget: "COMPOSITION",
          underlyingReferenceNodeId: UNDERLYING_ID,
          underlyingLabel: "Demo equity",
          participation: -1,
          strikeValue: 65,
          strikePercent: 65,
          observationDate: "2028-01-01",
          paymentDate: "2028-01-03",
        }),
      ],
    }));

    expect(payload.productSubtype).toBe("VANILLA_KIP");
    expect(payload.rows[0]).toEqual(expect.objectContaining({ conditionRole: "OPTION_PAYOFF", observationStyle: "FINAL_ONLY", conditionLevel: null }));
    expect(payload.rows[1]).toEqual(expect.objectContaining({ conditionRole: "CAPITAL_PROTECTION", observationStyle: "CONTINUOUS" }));
  });
});
