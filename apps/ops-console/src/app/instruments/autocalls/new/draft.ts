import type { GeneratedScheduleRow } from "./schedule";

export type DraftRowState = "GENERATED" | "ADDED" | "EDITED" | "DELETED";

export type DraftEditableField = "conditionLevel" | "couponRate" | "participation" | "paymentDate";

export type ScheduleDraftRow = GeneratedScheduleRow & {
  draftRowId: string;
  sourceRowId: string | null;
  rowState: DraftRowState;
  dirtyFields: DraftEditableField[];
};

export type DraftCommand = {
  type: "UPDATE_CELL";
  draftRowId: string;
  field: DraftEditableField;
  value: number | string | null;
};

export type DraftValidationIssue = {
  draftRowId: string;
  field: string;
  message: string;
};

export function createScheduleDraft(rows: GeneratedScheduleRow[]): ScheduleDraftRow[] {
  return rows.map((row) => ({
    ...row,
    draftRowId: `draft:${row.rowId}`,
    sourceRowId: row.rowId,
    rowState: "GENERATED",
    dirtyFields: [],
  }));
}

function canUpdateField(row: ScheduleDraftRow, field: DraftEditableField): boolean {
  if (row.rowState === "DELETED") return false;
  if (field === "couponRate") return row.rowKind === "COMPONENT" && row.conditionRole === "COUPON_ELIGIBILITY";
  if (field === "participation") return row.rowKind === "COMPONENT";
  return true;
}

export function applyDraftCommand(rows: ScheduleDraftRow[], command: DraftCommand): ScheduleDraftRow[] {
  if (command.type !== "UPDATE_CELL") return rows;

  return rows.map((row) => {
    if (row.draftRowId !== command.draftRowId || !canUpdateField(row, command.field)) return row;
    return {
      ...row,
      [command.field]: command.value,
      rowState: row.rowState === "GENERATED" ? "EDITED" : row.rowState,
      dirtyFields: row.dirtyFields.includes(command.field) ? row.dirtyFields : [...row.dirtyFields, command.field],
    };
  });
}

export function validateScheduleDraft(rows: ScheduleDraftRow[]): DraftValidationIssue[] {
  const issues: DraftValidationIssue[] = [];
  const seenDraftRowIds = new Set<string>();

  rows.forEach((row) => {
    if (seenDraftRowIds.has(row.draftRowId)) {
      issues.push({ draftRowId: row.draftRowId, field: "draftRowId", message: "Draft row IDs must be unique." });
    }
    seenDraftRowIds.add(row.draftRowId);

    if (row.rowKind === "ACTION" && row.underlyingReferenceNodeId !== null) {
      issues.push({ draftRowId: row.draftRowId, field: "underlyingReferenceNodeId", message: "Parent actions cannot carry an underlying reference." });
    }
    if (row.rowKind === "ACTION" && row.actionTarget !== "PARENT") {
      issues.push({ draftRowId: row.draftRowId, field: "actionTarget", message: "Parent actions must target the parent product." });
    }
    if (row.rowKind === "COMPONENT" && row.actionTarget !== "COMPOSITION") {
      issues.push({ draftRowId: row.draftRowId, field: "actionTarget", message: "Component payments must target a composition entry." });
    }
    if (row.rowKind === "COMPONENT" && row.underlyingReferenceNodeId === null) {
      issues.push({ draftRowId: row.draftRowId, field: "underlyingReferenceNodeId", message: "Component rows need a resolved underlying reference." });
    }
    if (row.conditionRole !== "OPTION_PAYOFF" && row.conditionOperator !== "RANGE" && (!Number.isFinite(row.conditionLevel) || row.conditionLevel === null || row.conditionLevel < 0)) {
      issues.push({ draftRowId: row.draftRowId, field: "conditionLevel", message: "Condition level must be a non-negative number." });
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(row.paymentDate) || row.paymentDate < row.observationDate) {
      issues.push({ draftRowId: row.draftRowId, field: "paymentDate", message: "Settlement date cannot precede the observation date." });
    }
    if (row.conditionOperator === "RANGE") {
      if (row.conditionLowerLevel === null || row.conditionUpperLevel === null || !Number.isFinite(row.conditionLowerLevel) || !Number.isFinite(row.conditionUpperLevel)) {
        issues.push({ draftRowId: row.draftRowId, field: "conditionRange", message: "Range bounds must be numeric when supplied." });
      } else if (row.conditionLowerLevel >= row.conditionUpperLevel) {
        issues.push({ draftRowId: row.draftRowId, field: "conditionRange", message: "Range lower bound must be below upper bound." });
      }
    }
    if (row.actionCode === "PAY_CONSOLATION" && (row.payoutRate === null || !Number.isFinite(row.payoutRate) || row.payoutRate < 0 || row.payoutRate > 100)) {
      issues.push({ draftRowId: row.draftRowId, field: "payoutRate", message: "Consolation rate must be between 0 and 100 percent." });
    }
    if (row.couponRate !== null && !Number.isFinite(row.couponRate)) {
      issues.push({ draftRowId: row.draftRowId, field: "couponRate", message: "Coupon rate must be numeric when supplied." });
    }
    if (row.participation !== null && !Number.isFinite(row.participation)) {
      issues.push({ draftRowId: row.draftRowId, field: "participation", message: "Signed leg multiplier must be numeric when supplied." });
    }
  });

  return issues;
}
