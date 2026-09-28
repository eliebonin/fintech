import { describe, expect, it } from "vitest";

import { generateAutocallSchedule, type ScheduleGenerationInput } from "./schedule";
import {
  applyDraftCommand,
  createScheduleDraft,
  validateScheduleDraft,
} from "./draft";

const input: ScheduleGenerationInput = {
  startDate: "2027-09-03",
  maturityDate: "2027-09-03",
  frequency: "ANNUAL",
  paymentLagBusinessDays: 2,
  couponRate: 6.5,
  couponBarrier: 100,
  autocallBarrierStart: 100,
  autocallBarrierStep: 0,
  autocallBarrierFloor: 0,
  kipBarrier: 65,
  scope: "WORST_OF",
  underlyings: [
    { referenceNodeId: "spx", label: "SPX Index", initialFixing: 100, participation: 1 },
  ],
};

describe("structured-product schedule drafts", () => {
  it("wraps generated rows with stable draft identity and baseline state", () => {
    const generated = generateAutocallSchedule(input);
    const draft = createScheduleDraft(generated.rows);

    expect(draft[0]).toMatchObject({
      draftRowId: `draft:${generated.rows[0].rowId}`,
      sourceRowId: generated.rows[0].rowId,
      rowState: "GENERATED",
      dirtyFields: [],
    });
  });

  it("updates an allowed cell without mutating the generated row", () => {
    const generated = generateAutocallSchedule(input);
    const draft = createScheduleDraft(generated.rows);
    const coupon = draft.find((row) => row.conditionRole === "COUPON_ELIGIBILITY");

    expect(coupon).toBeDefined();
    const updated = applyDraftCommand(draft, {
      type: "UPDATE_CELL",
      draftRowId: coupon!.draftRowId,
      field: "conditionLevel",
      value: 95,
    });

    expect(updated.find((row) => row.draftRowId === coupon!.draftRowId)).toMatchObject({
      conditionLevel: 95,
      rowState: "EDITED",
      dirtyFields: ["conditionLevel"],
    });
    expect(generated.rows.find((row) => row.rowId === coupon!.sourceRowId)?.conditionLevel).toBe(100);
  });

  it("validates parent action ownership and component action ownership", () => {
    const generated = generateAutocallSchedule(input);
    const draft = createScheduleDraft(generated.rows);

    expect(validateScheduleDraft(draft)).toEqual([]);
    expect(validateScheduleDraft(draft.map((row) => row.rowKind === "ACTION" ? { ...row, underlyingReferenceNodeId: "spx" } : row))).toContainEqual({
      draftRowId: "draft:ACTION:FINAL_REDEMPTION:2027-09-03",
      field: "underlyingReferenceNodeId",
      message: "Parent actions cannot carry an underlying reference.",
    });
  });

  it("validates a consolation range as one bounded condition", () => {
    const generated = generateAutocallSchedule({ ...input, includeConsolation: true, consolationRate: 50 });
    const draft = createScheduleDraft(generated.rows);

    expect(validateScheduleDraft(draft)).toEqual([]);
    expect(validateScheduleDraft(draft.map((row) => row.actionCode === "PAY_CONSOLATION" ? { ...row, conditionLowerLevel: row.conditionUpperLevel } : row))).toContainEqual({
      draftRowId: "draft:ACTION:PAY_CONSOLATION:2027-09-03",
      field: "conditionRange",
      message: "Range lower bound must be below upper bound.",
    });
  });

  it("allows settlement dates to be edited without allowing them before observation", () => {
    const generated = generateAutocallSchedule(input);
    const draft = createScheduleDraft(generated.rows);
    const coupon = draft.find((row) => row.conditionRole === "COUPON_ELIGIBILITY");

    expect(coupon).toBeDefined();
    const updated = applyDraftCommand(draft, {
      type: "UPDATE_CELL",
      draftRowId: coupon!.draftRowId,
      field: "paymentDate",
      value: "2027-09-08",
    });
    expect(updated.find((row) => row.draftRowId === coupon!.draftRowId)).toMatchObject({
      paymentDate: "2027-09-08",
      rowState: "EDITED",
      dirtyFields: ["paymentDate"],
    });
    expect(validateScheduleDraft(updated)).toEqual([]);

    const invalid = applyDraftCommand(draft, {
      type: "UPDATE_CELL",
      draftRowId: coupon!.draftRowId,
      field: "paymentDate",
      value: "2027-09-02",
    });
    expect(validateScheduleDraft(invalid)).toContainEqual({
      draftRowId: coupon!.draftRowId,
      field: "paymentDate",
      message: "Settlement date cannot precede the observation date.",
    });
  });
});
