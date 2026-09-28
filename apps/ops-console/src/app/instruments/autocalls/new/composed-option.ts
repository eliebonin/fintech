import type { GeneratedScheduleRow, ScheduleScope, ScheduleUnderlying } from "./schedule";

export type ComposedOptionTemplate = "VANILLA_SPREAD_KIP" | "VANILLA_KIP" | "DIGITAL_KIP";

export type ComposedOptionLeg = {
  legId: string;
  referenceNodeId: string;
  underlyingLabel: string;
  initialFixing: number;
  optionType: "CALL" | "PUT" | "DIGITAL";
  strikePercent: number;
  participation: number;
  /** Percentage of notional paid when a digital payoff condition is met. */
  payoutRate: number | null;
};

export type ComposedOptionGenerationInput = {
  template: ComposedOptionTemplate;
  startDate: string;
  maturityDate: string;
  paymentLagBusinessDays: number;
  kipBarrier: number;
  includeKip?: boolean;
  /** KIP barriers are commonly continuously monitored; European-at-maturity is also supported. */
  kipObservationStyle?: "CONTINUOUS" | "FINAL_ONLY";
  scope: ScheduleScope;
  underlyings: ScheduleUnderlying[];
  legs: ComposedOptionLeg[];
};

export type ComposedOptionGenerationResult = {
  observationDates: string[];
  rows: GeneratedScheduleRow[];
  warnings: string[];
};

function parseIsoDate(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  return date.getUTCFullYear() === Number(match[1])
    && date.getUTCMonth() === Number(match[2]) - 1
    && date.getUTCDate() === Number(match[3])
    ? date
    : null;
}

function formatIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function addBusinessDays(date: Date, businessDays: number): Date {
  const result = new Date(date.getTime());
  let remaining = Math.max(0, Math.trunc(businessDays));
  while (remaining > 0) {
    result.setUTCDate(result.getUTCDate() + 1);
    const day = result.getUTCDay();
    if (day !== 0 && day !== 6) remaining -= 1;
  }
  return result;
}

function componentKind(optionType: ComposedOptionLeg["optionType"]): "DIGITAL" | "VANILLA_OPTION" {
  return optionType === "DIGITAL" ? "DIGITAL" : "VANILLA_OPTION";
}

function strikeValue(initialFixing: number, strikePercent: number): number {
  return initialFixing * strikePercent / 100;
}

/**
 * Project the three first composed-option templates into the same review
 * rows used by the structured-product builder. The parent has no artificial
 * autocall event here: ordinary option legs and the KIP leg are separate
 * composition components, all settled at maturity.
 */
export function generateComposedOptionSchedule(input: ComposedOptionGenerationInput): ComposedOptionGenerationResult {
  const warnings: string[] = [];
  const startDate = parseIsoDate(input.startDate);
  const maturityDate = parseIsoDate(input.maturityDate);

  if (!startDate) warnings.push("Observation start date must be a valid ISO date.");
  if (!maturityDate) warnings.push("Maturity date must be a valid ISO date.");
  if (startDate && maturityDate && maturityDate < startDate) warnings.push("Maturity date must be on or after the observation start date.");
  if (!input.underlyings.length) warnings.push("Add at least one underlying before generating the schedule.");
  if (!input.legs.length) warnings.push("Add at least one option payoff leg before generating the schedule.");
  if (input.template === "VANILLA_SPREAD_KIP" && input.legs.length !== 2) warnings.push("A vanilla spread with KIP requires exactly two option payoff legs.");
  if (input.template !== "VANILLA_SPREAD_KIP" && input.legs.length !== 1) warnings.push("This composed-option template requires exactly one option payoff leg.");
  if (!Number.isFinite(input.kipBarrier) || input.kipBarrier <= 0 || input.kipBarrier > 100) warnings.push("KIP barrier must be above 0 and no greater than 100 percent of initial.");
  if (input.includeKip === false) warnings.push("Composed option templates require the KIP component.");

  const underlyingIds = new Set(input.underlyings.map((underlying) => underlying.referenceNodeId));
  if (input.scope === "SINGLE" && input.underlyings.length !== 1) warnings.push("SINGLE scope requires exactly one underlying.");
  if ((input.scope === "BEST_OF" || input.scope === "WORST_OF") && input.underlyings.length < 2) warnings.push("BEST_OF and WORST_OF scopes require at least two underlyings.");
  if (underlyingIds.size !== input.underlyings.length) warnings.push("Underlying reference nodes must be unique.");
  if (input.legs.some((leg) => !underlyingIds.has(leg.referenceNodeId))) warnings.push("Each option leg must reference an underlying in the draft.");
  if (input.legs.some((leg) => !Number.isFinite(leg.strikePercent) || leg.strikePercent <= 0)) warnings.push("Each option leg needs a positive strike percentage.");
  if (input.legs.some((leg) => !Number.isFinite(leg.participation) || leg.participation === 0)) warnings.push("Each option leg needs a non-zero signed participation.");
  if (input.template === "DIGITAL_KIP" && input.legs.some((leg) => leg.optionType !== "DIGITAL")) warnings.push("Digital with KIP requires a DIGITAL payoff leg.");
  if (input.template === "DIGITAL_KIP" && input.legs.some((leg) => !Number.isFinite(leg.payoutRate) || (leg.payoutRate as number) < 0 || (leg.payoutRate as number) > 100)) warnings.push("Digital payoff requires a payout rate between 0 and 100 percent.");
  if (input.template !== "DIGITAL_KIP" && input.legs.some((leg) => leg.optionType === "DIGITAL")) warnings.push("Vanilla templates require CALL or PUT payoff legs.");
  if (input.template === "VANILLA_SPREAD_KIP" && input.legs.length === 2) {
    if (input.legs[0].optionType !== input.legs[1].optionType) warnings.push("A vanilla spread requires the two payoff legs to use the same option type.");
    if (!(input.legs.some((leg) => leg.participation > 0) && input.legs.some((leg) => leg.participation < 0))) warnings.push("A vanilla spread requires one long and one short signed leg.");
  }

  if (warnings.length || !maturityDate) return { observationDates: [], rows: [], warnings };

  const maturityText = formatIsoDate(maturityDate);
  const paymentDate = formatIsoDate(addBusinessDays(maturityDate, input.paymentLagBusinessDays));
  const rows: GeneratedScheduleRow[] = [];

  input.legs.forEach((leg, index) => {
    rows.push({
      rowId: `OPTION:${leg.legId}:${maturityText}`,
      rowKind: "COMPONENT",
      groupCode: "OPTION_LEG",
      groupLabel: "Option payoff legs",
      legId: index + 1,
      componentKind: componentKind(leg.optionType),
      optionType: leg.optionType,
      exerciseStyle: "EUROPEAN",
      conditionRole: "OPTION_PAYOFF",
      observationStyle: "FINAL_ONLY",
      conditionOperator: "GE",
      conditionScope: input.scope,
      underlyingReferenceNodeId: leg.referenceNodeId,
      underlyingLabel: leg.underlyingLabel,
      participation: leg.participation,
      couponRate: null,
      strikeValue: strikeValue(leg.initialFixing, leg.strikePercent),
      strikePercent: leg.strikePercent,
      observationDate: maturityText,
      paymentDate,
      conditionLevel: null,
      conditionLowerLevel: null,
      conditionUpperLevel: null,
      conditionLevelBasis: "PCT_OF_INITIAL",
      payoutRate: leg.optionType === "DIGITAL" ? (leg.payoutRate ?? 0) : null,
      actionCode: "PAY_COMPONENT",
      actionTarget: "COMPOSITION",
    });
  });

  if (input.includeKip !== false) input.underlyings.forEach((underlying, index) => {
    rows.push({
      rowId: `KIP:${underlying.referenceNodeId}:${maturityText}`,
      rowKind: "COMPONENT",
      groupCode: "CAPITAL_PROTECTION",
      groupLabel: "Knock-in put protection",
      legId: input.legs.length + index + 1,
      componentKind: "VANILLA_OPTION",
      optionType: "PUT",
      exerciseStyle: "EUROPEAN",
      conditionRole: "CAPITAL_PROTECTION",
      observationStyle: input.kipObservationStyle ?? "CONTINUOUS",
      conditionOperator: "LE",
      conditionScope: input.scope,
      underlyingReferenceNodeId: underlying.referenceNodeId,
      underlyingLabel: underlying.label,
      participation: -1,
      couponRate: null,
      strikeValue: strikeValue(underlying.initialFixing, input.kipBarrier),
      strikePercent: input.kipBarrier,
      observationDate: maturityText,
      paymentDate,
      conditionLevel: input.kipBarrier,
      conditionLowerLevel: null,
      conditionUpperLevel: null,
      conditionLevelBasis: "PCT_OF_INITIAL",
      payoutRate: null,
      actionCode: "PAY_COMPONENT",
      actionTarget: "COMPOSITION",
    });
  });

  return { observationDates: [maturityText], rows, warnings };
}
