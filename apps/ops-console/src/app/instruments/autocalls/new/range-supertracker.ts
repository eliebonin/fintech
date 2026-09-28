import type {
  RangeAccrualBasis,
  RangeNonBusinessDayRule,
  RangeObservationFrequency,
} from "./payload";
import type { GeneratedScheduleRow, ScheduleFrequency, ScheduleScope, ScheduleUnderlying } from "./schedule";

export type RangeAccrualGenerationInput = {
  startDate: string;
  maturityDate: string;
  couponFrequency: ScheduleFrequency;
  paymentLagBusinessDays: number;
  couponRatePerAnnum: number;
  lowerLevel: number;
  upperLevel: number;
  observationFrequency: RangeObservationFrequency;
  accrualBasis: RangeAccrualBasis;
  nonBusinessDayRule: RangeNonBusinessDayRule;
  scope: ScheduleScope;
  underlyings: ScheduleUnderlying[];
};

export type RangeAccrualGenerationResult = {
  observationDates: string[];
  rows: GeneratedScheduleRow[];
  warnings: string[];
  rangeObservationFrequency: RangeObservationFrequency;
  accrualBasis: RangeAccrualBasis;
  nonBusinessDayRule: RangeNonBusinessDayRule;
};

export type SupertrackerGenerationInput = {
  startDate: string;
  maturityDate: string;
  paymentLagBusinessDays: number;
  participationRate: number;
  includeCap?: boolean;
  capReturn?: number;
  kipBarrier: number;
  includeKip?: boolean;
  kipObservationStyle?: "CONTINUOUS" | "FINAL_ONLY";
  scope: ScheduleScope;
  underlyings: ScheduleUnderlying[];
};

export type SupertrackerGenerationResult = {
  observationDates: string[];
  rows: GeneratedScheduleRow[];
  warnings: string[];
};

const FREQUENCY_MONTHS: Record<ScheduleFrequency, number> = {
  MONTHLY: 1,
  QUARTERLY: 3,
  SEMI_ANNUAL: 6,
  ANNUAL: 12,
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

function addMonths(date: Date, months: number): Date {
  const target = new Date(date.getTime());
  const originalDay = target.getUTCDate();
  target.setUTCDate(1);
  target.setUTCMonth(target.getUTCMonth() + months);
  const lastDay = new Date(Date.UTC(target.getUTCFullYear(), target.getUTCMonth() + 1, 0)).getUTCDate();
  target.setUTCDate(Math.min(originalDay, lastDay));
  return target;
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

function buildPeriodDates(startDate: Date, maturityDate: Date, frequency: ScheduleFrequency): Date[] {
  const dates: Date[] = [];
  let current = addMonths(startDate, FREQUENCY_MONTHS[frequency]);
  while (current < maturityDate) {
    dates.push(current);
    current = addMonths(current, FREQUENCY_MONTHS[frequency]);
  }
  dates.push(maturityDate);
  return Array.from(new Set(dates.map(formatIsoDate))).map((value) => parseIsoDate(value) as Date);
}

function scopeWarnings(scope: ScheduleScope, underlyings: ScheduleUnderlying[]): string[] {
  if (scope === "SINGLE" && underlyings.length !== 1) return ["SINGLE scope requires exactly one underlying."];
  if ((scope === "BEST_OF" || scope === "WORST_OF") && underlyings.length < 2) return ["BEST_OF and WORST_OF scopes require at least two underlyings."];
  if (new Set(underlyings.map((underlying) => underlying.referenceNodeId)).size !== underlyings.length) return ["Underlying reference nodes must be unique."];
  return [];
}

/**
 * Generate one row per contractual coupon period, not one child option per
 * daily fixing. The range observation convention is returned as metadata and
 * is persisted by the range-specific terms table.
 */
export function generateRangeAccrualSchedule(input: RangeAccrualGenerationInput): RangeAccrualGenerationResult {
  const warnings: string[] = [];
  const startDate = parseIsoDate(input.startDate);
  const maturityDate = parseIsoDate(input.maturityDate);
  if (!startDate) warnings.push("Observation start date must be a valid ISO date.");
  if (!maturityDate) warnings.push("Maturity date must be a valid ISO date.");
  if (startDate && maturityDate && maturityDate < startDate) warnings.push("Maturity date must be on or after the observation start date.");
  if (!input.underlyings.length) warnings.push("Add at least one underlying before generating the schedule.");
  if (!Number.isFinite(input.couponRatePerAnnum) || input.couponRatePerAnnum < 0) warnings.push("Annual coupon rate must be a non-negative number.");
  if (!Number.isFinite(input.lowerLevel) || !Number.isFinite(input.upperLevel) || input.lowerLevel < 0 || input.upperLevel <= input.lowerLevel) warnings.push("Range lower and upper levels must be valid and the upper level must be above the lower level.");
  warnings.push(...scopeWarnings(input.scope, input.underlyings));
  if (warnings.length || !startDate || !maturityDate) {
    return { observationDates: [], rows: [], warnings, rangeObservationFrequency: input.observationFrequency, accrualBasis: input.accrualBasis, nonBusinessDayRule: input.nonBusinessDayRule };
  }

  const periods = buildPeriodDates(startDate, maturityDate, input.couponFrequency);
  const rows: GeneratedScheduleRow[] = [];
  periods.forEach((periodDate, periodIndex) => {
    const observationDate = formatIsoDate(periodDate);
    const paymentDate = formatIsoDate(addBusinessDays(periodDate, input.paymentLagBusinessDays));
    input.underlyings.forEach((underlying, underlyingIndex) => {
      rows.push({
        rowId: `RANGE_COUPON:${periodIndex + 1}:${underlying.referenceNodeId}:${observationDate}`,
        rowKind: "COMPONENT",
        groupCode: "COUPON_COMPONENT",
        groupLabel: "Range accrual coupon",
        legId: underlyingIndex + 1,
        componentKind: "DIGITAL",
        optionType: "DIGITAL",
        exerciseStyle: "EUROPEAN",
        conditionRole: "COUPON_ELIGIBILITY",
        observationStyle: "DISCRETE",
        conditionOperator: "RANGE",
        conditionScope: input.scope,
        underlyingReferenceNodeId: underlying.referenceNodeId,
        underlyingLabel: underlying.label,
        participation: 1,
        // The annualised rate belongs to the focused range-accrual terms
        // record, not to each coupon-period eligibility row.
        couponRate: null,
        strikeValue: null,
        strikePercent: null,
        observationDate,
        paymentDate,
        conditionLevel: null,
        conditionLowerLevel: input.lowerLevel,
        conditionUpperLevel: input.upperLevel,
        conditionLowerInclusive: true,
        conditionUpperInclusive: true,
        conditionLevelBasis: "PCT_OF_INITIAL",
        payoutRate: null,
        actionCode: "PAY_COMPONENT",
        actionTarget: "COMPOSITION",
      });
    });
  });

  const finalDate = formatIsoDate(maturityDate);
  const finalPaymentDate = formatIsoDate(addBusinessDays(maturityDate, input.paymentLagBusinessDays));
  rows.push({
    rowId: `RANGE_FINAL_REDEMPTION:${finalDate}`,
    rowKind: "ACTION",
    groupCode: "FINAL_REDEMPTION",
    groupLabel: "Range accrual maturity redemption",
    legId: 1,
    componentKind: "PARENT_ACTION",
    optionType: null,
    exerciseStyle: null,
    conditionRole: "FINAL_REDEMPTION",
    observationStyle: "FINAL_ONLY",
    conditionOperator: "GE",
    conditionScope: input.scope,
    underlyingReferenceNodeId: null,
    underlyingLabel: "Parent product",
    participation: null,
    couponRate: null,
    strikeValue: null,
    strikePercent: null,
    observationDate: finalDate,
    paymentDate: finalPaymentDate,
    conditionLevel: 0,
    conditionLowerLevel: null,
    conditionUpperLevel: null,
    conditionLowerInclusive: true,
    conditionUpperInclusive: true,
    conditionLevelBasis: "PCT_OF_INITIAL",
    payoutRate: null,
    actionCode: "FINAL_REDEMPTION",
    actionTarget: "PARENT",
  });

  return {
    observationDates: Array.from(new Set(rows.map((row) => row.observationDate))).sort(),
    rows,
    warnings,
    rangeObservationFrequency: input.observationFrequency,
    accrualBasis: input.accrualBasis,
    nonBusinessDayRule: input.nonBusinessDayRule,
  };
}

/**
 * Generate the first supertracker slice as a maturity-only parent graph. The
 * signed call pair is the cap: +participation at 100% and -participation at
 * 100% + cap return. The initial slice intentionally requires SINGLE scope;
 * a true worst-of payoff needs a dedicated basket/worst-of reference node.
 */
export function generateSupertrackerSchedule(input: SupertrackerGenerationInput): SupertrackerGenerationResult {
  const warnings: string[] = [];
  const startDate = parseIsoDate(input.startDate);
  const maturityDate = parseIsoDate(input.maturityDate);
  if (!startDate) warnings.push("Observation start date must be a valid ISO date.");
  if (!maturityDate) warnings.push("Maturity date must be a valid ISO date.");
  if (startDate && maturityDate && maturityDate < startDate) warnings.push("Maturity date must be on or after the observation start date.");
  if (!input.underlyings.length) warnings.push("Add at least one underlying before generating the schedule.");
  if (input.scope !== "SINGLE" || input.underlyings.length !== 1) warnings.push("The first supertracker slice requires one underlying with SINGLE scope; multi-underlying worst-of terms need a dedicated reference basket.");
  if (!Number.isFinite(input.participationRate) || input.participationRate <= 0) warnings.push("Upside participation rate must be greater than zero.");
  if (input.includeCap && (!Number.isFinite(input.capReturn) || (input.capReturn as number) <= 0)) warnings.push("An upside cap must specify a positive underlying return percentage.");
  if (input.includeKip && (!Number.isFinite(input.kipBarrier) || input.kipBarrier <= 0 || input.kipBarrier > 100)) warnings.push("KIP barrier must be above 0 and no greater than 100 percent of initial.");
  if (warnings.length || !maturityDate) return { observationDates: [], rows: [], warnings };

  const underlying = input.underlyings[0];
  const maturityText = formatIsoDate(maturityDate);
  const paymentDate = formatIsoDate(addBusinessDays(maturityDate, input.paymentLagBusinessDays));
  const participation = input.participationRate / 100;
  const rows: GeneratedScheduleRow[] = [];
  rows.push({
    rowId: `SUPERTRACKER:UPSIDE:${maturityText}`,
    rowKind: "COMPONENT",
    groupCode: "OPTION_LEG",
    groupLabel: "Leveraged upside",
    legId: 1,
    componentKind: "VANILLA_OPTION",
    optionType: "CALL",
    exerciseStyle: "EUROPEAN",
    conditionRole: "OPTION_PAYOFF",
    observationStyle: "FINAL_ONLY",
    conditionOperator: "GE",
    conditionScope: "SINGLE",
    underlyingReferenceNodeId: underlying.referenceNodeId,
    underlyingLabel: underlying.label,
    participation,
    couponRate: null,
    strikeValue: underlying.initialFixing,
    strikePercent: 100,
    observationDate: maturityText,
    paymentDate,
    conditionLevel: null,
    conditionLowerLevel: null,
    conditionUpperLevel: null,
    conditionLowerInclusive: true,
    conditionUpperInclusive: true,
    conditionLevelBasis: "PCT_OF_INITIAL",
    payoutRate: null,
    actionCode: "PAY_COMPONENT",
    actionTarget: "COMPOSITION",
  });

  if (input.includeCap) {
    rows.push({
      rowId: `SUPERTRACKER:CAP:${maturityText}`,
      rowKind: "COMPONENT",
      groupCode: "OPTION_LEG",
      groupLabel: "Leveraged upside cap",
      legId: 2,
      componentKind: "VANILLA_OPTION",
      optionType: "CALL",
      exerciseStyle: "EUROPEAN",
      conditionRole: "OPTION_PAYOFF",
      observationStyle: "FINAL_ONLY",
      conditionOperator: "GE",
      conditionScope: "SINGLE",
      underlyingReferenceNodeId: underlying.referenceNodeId,
      underlyingLabel: underlying.label,
      participation: -participation,
      couponRate: null,
      strikeValue: underlying.initialFixing * (100 + (input.capReturn as number)) / 100,
      strikePercent: 100 + (input.capReturn as number),
      observationDate: maturityText,
      paymentDate,
      conditionLevel: null,
      conditionLowerLevel: null,
      conditionUpperLevel: null,
      conditionLowerInclusive: true,
      conditionUpperInclusive: true,
      conditionLevelBasis: "PCT_OF_INITIAL",
      payoutRate: null,
      actionCode: "PAY_COMPONENT",
      actionTarget: "COMPOSITION",
    });
  }

  if (input.includeKip !== false) {
    rows.push({
      rowId: `SUPERTRACKER:KIP:${maturityText}`,
      rowKind: "COMPONENT",
      groupCode: "CAPITAL_PROTECTION",
      groupLabel: "Knock-in put downside",
      legId: input.includeCap ? 3 : 2,
      componentKind: "VANILLA_OPTION",
      optionType: "PUT",
      exerciseStyle: "EUROPEAN",
      conditionRole: "CAPITAL_PROTECTION",
      observationStyle: input.kipObservationStyle ?? "CONTINUOUS",
      conditionOperator: "LE",
      conditionScope: "SINGLE",
      underlyingReferenceNodeId: underlying.referenceNodeId,
      underlyingLabel: underlying.label,
      participation: -1,
      couponRate: null,
      strikeValue: underlying.initialFixing * input.kipBarrier / 100,
      strikePercent: input.kipBarrier,
      observationDate: maturityText,
      paymentDate,
      conditionLevel: input.kipBarrier,
      conditionLowerLevel: null,
      conditionUpperLevel: null,
      conditionLowerInclusive: true,
      conditionUpperInclusive: true,
      conditionLevelBasis: "PCT_OF_INITIAL",
      payoutRate: null,
      actionCode: "PAY_COMPONENT",
      actionTarget: "COMPOSITION",
    });
  }

  rows.push({
    rowId: `SUPERTRACKER:FINAL_REDEMPTION:${maturityText}`,
    rowKind: "ACTION",
    groupCode: "FINAL_REDEMPTION",
    groupLabel: "Supertracker maturity redemption",
    legId: 1,
    componentKind: "PARENT_ACTION",
    optionType: null,
    exerciseStyle: null,
    conditionRole: "FINAL_REDEMPTION",
    observationStyle: "FINAL_ONLY",
    conditionOperator: "GE",
    conditionScope: "SINGLE",
    underlyingReferenceNodeId: null,
    underlyingLabel: "Parent product",
    participation: null,
    couponRate: null,
    strikeValue: null,
    strikePercent: null,
    observationDate: maturityText,
    paymentDate,
    conditionLevel: 0,
    conditionLowerLevel: null,
    conditionUpperLevel: null,
    conditionLowerInclusive: true,
    conditionUpperInclusive: true,
    conditionLevelBasis: "PCT_OF_INITIAL",
    payoutRate: null,
    actionCode: "FINAL_REDEMPTION",
    actionTarget: "PARENT",
  });

  return { observationDates: [maturityText], rows, warnings };
}
