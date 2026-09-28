export type ScheduleFrequency = "MONTHLY" | "QUARTERLY" | "SEMI_ANNUAL" | "ANNUAL";
export type ScheduleScope = "SINGLE" | "BEST_OF" | "WORST_OF" | "BASKET" | "EACH_UNDERLYING";

export type ScheduleUnderlying = {
  referenceNodeId: string;
  label: string;
  initialFixing: number;
  participation: number;
};

export type AutocallLegSide = "LONG" | "SHORT";

/**
 * The schedule stores a signed composition multiplier for arithmetic and
 * persistence compatibility. Autocall users should see the business side.
 */
export function autocallLegSide(participation: number | null): AutocallLegSide | null {
  if (participation === null || !Number.isFinite(participation)) return null;
  return participation < 0 ? "SHORT" : "LONG";
}

export type ScheduleGenerationInput = {
  startDate: string;
  maturityDate: string;
  /** First date on which a parent autocall/redemption test is permitted. */
  firstAutocallObservationDate?: string;
  frequency: ScheduleFrequency;
  /** Coupon eligibility/payment cadence. Defaults to `frequency`. */
  couponFrequency?: ScheduleFrequency;
  /** Parent autocall observation cadence. Defaults to `frequency`. */
  autocallFrequency?: ScheduleFrequency;
  paymentLagBusinessDays: number;
  couponRate: number;
  couponBarrier: number;
  /** Whether coupon eligibility inherits the autocall level in force. */
  couponBarrierFollowsAutocall?: boolean;
  autocallBarrierStart: number;
  autocallBarrierStep: number;
  autocallBarrierFloor: number;
  kipBarrier: number;
  /** Independent lower bound for a consolation range when no KIP component is included. */
  consolationLowerBarrier?: number;
  finalPayoffBarrier?: number;
  includeKip?: boolean;
  includeConsolation?: boolean;
  consolationRate?: number;
  scope: ScheduleScope;
  underlyings: ScheduleUnderlying[];
};

export type GeneratedScheduleRow = {
  rowId: string;
  rowKind: "COMPONENT" | "ACTION";
  groupCode: "COUPON_COMPONENT" | "PARENT_ACTION" | "CAPITAL_PROTECTION" | "CONSOLATION_ACTION" | "FINAL_REDEMPTION" | "OPTION_LEG";
  groupLabel: string;
  legId: number;
  componentKind: "DIGITAL" | "VANILLA_OPTION" | "PARENT_ACTION";
  optionType: "DIGITAL" | "CALL" | "PUT" | null;
  exerciseStyle: "EUROPEAN" | null;
  conditionRole: "COUPON_ELIGIBILITY" | "AUTOCALL" | "CAPITAL_PROTECTION" | "CONSOLATION" | "FINAL_REDEMPTION" | "OPTION_PAYOFF";
  observationStyle?: "CONTINUOUS" | "DISCRETE" | "FINAL_ONLY";
  conditionOperator: "GE" | "LE" | "RANGE";
  conditionScope: ScheduleScope;
  underlyingReferenceNodeId: string | null;
  underlyingLabel: string;
  participation: number | null;
  couponRate: number | null;
  strikeValue: number | null;
  strikePercent: number | null;
  observationDate: string;
  paymentDate: string;
  conditionLevel: number | null;
  conditionLowerLevel: number | null;
  conditionUpperLevel: number | null;
  conditionLowerInclusive?: boolean;
  conditionUpperInclusive?: boolean;
  conditionLevelBasis: "PCT_OF_INITIAL";
  payoutRate: number | null;
  actionCode: "PAY_COMPONENT" | "REDEEM_PARENT" | "PAY_CONSOLATION" | "FINAL_REDEMPTION";
  actionTarget: "COMPOSITION" | "PARENT";
};

export type ScheduleGenerationResult = {
  observationDates: string[];
  rows: GeneratedScheduleRow[];
  warnings: string[];
};

export type ObservationSummary = {
  observationDate: string;
  paymentDate: string;
  conditionScope: ScheduleScope;
  couponBarrier: number | null;
  autocallBarrier: number | null;
  componentCount: number;
  actionCount: number;
  underlyingCount: number;
  hasCapitalProtection: boolean;
};

export type UnderlyingComponentGroup = {
  key: string;
  label: string;
  referenceNodeId: string | null;
  rows: GeneratedScheduleRow[];
};

/**
 * Creates a comparison-friendly summary without repeating parent actions for
 * every underlying. The full contractual rows remain available separately.
 */
export function summarizeObservations(rows: GeneratedScheduleRow[]): ObservationSummary[] {
  const grouped = new Map<string, GeneratedScheduleRow[]>();
  rows.forEach((row) => {
    const observationRows = grouped.get(row.observationDate) ?? [];
    observationRows.push(row);
    grouped.set(row.observationDate, observationRows);
  });

  return Array.from(grouped.entries()).map(([observationDate, observationRows]) => {
    const couponRow = observationRows.find((row) => row.conditionRole === "COUPON_ELIGIBILITY");
    const actionRow = observationRows.find((row) => row.actionCode === "REDEEM_PARENT");
    const underlyingIds = new Set(
      observationRows
        .filter((row) => row.rowKind === "COMPONENT")
        .map((row) => row.underlyingReferenceNodeId)
        .filter((referenceNodeId): referenceNodeId is string => Boolean(referenceNodeId)),
    );

    return {
      observationDate,
      paymentDate: observationRows[0]?.paymentDate ?? "",
      conditionScope: observationRows[0]?.conditionScope ?? "SINGLE",
      couponBarrier: couponRow?.conditionLevel ?? null,
      autocallBarrier: actionRow?.conditionLevel ?? null,
      componentCount: observationRows.filter((row) => row.rowKind === "COMPONENT").length,
      actionCount: observationRows.filter((row) => row.rowKind === "ACTION").length,
      underlyingCount: underlyingIds.size,
      hasCapitalProtection: observationRows.some((row) => row.groupCode === "CAPITAL_PROTECTION"),
    };
  });
}

/** Groups the selected observation's component rows into one compact row per underlying. */
export function groupComponentsByUnderlying(rows: GeneratedScheduleRow[]): UnderlyingComponentGroup[] {
  const groups = new Map<string, UnderlyingComponentGroup>();
  rows.filter((row) => row.rowKind === "COMPONENT").forEach((row) => {
    const key = row.underlyingReferenceNodeId ?? row.underlyingLabel;
    const existing = groups.get(key);
    if (existing) {
      existing.rows.push(row);
      return;
    }
    groups.set(key, {
      key,
      label: row.underlyingLabel,
      referenceNodeId: row.underlyingReferenceNodeId,
      rows: [row],
    });
  });
  return Array.from(groups.values());
}

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
  if (date.getUTCFullYear() !== Number(match[1]) || date.getUTCMonth() !== Number(match[2]) - 1 || date.getUTCDate() !== Number(match[3])) return null;
  return date;
}

function formatIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function addMonths(date: Date, months: number): Date {
  const targetMonth = date.getUTCMonth() + months;
  const year = date.getUTCFullYear() + Math.floor(targetMonth / 12);
  const month = ((targetMonth % 12) + 12) % 12;
  const lastDay = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
  return new Date(Date.UTC(year, month, Math.min(date.getUTCDate(), lastDay)));
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

function buildObservationDates(startDate: Date, maturityDate: Date, frequency: ScheduleFrequency): string[] {
  const dates: string[] = [];
  const intervalMonths = FREQUENCY_MONTHS[frequency];
  let current = new Date(startDate.getTime());
  for (let guard = 0; guard < 240 && current <= maturityDate; guard += 1) {
    dates.push(formatIsoDate(current));
    const next = addMonths(current, intervalMonths);
    if (next <= current) break;
    current = next;
  }
  const maturityText = formatIsoDate(maturityDate);
  if (dates.length && dates[dates.length - 1] !== maturityText) dates.push(maturityText);
  return dates;
}

function mergeObservationDates(...dateLists: string[][]): string[] {
  return Array.from(new Set(dateLists.flat())).sort();
}

export function generateAutocallSchedule(input: ScheduleGenerationInput): ScheduleGenerationResult {
  const warnings: string[] = [];
  const startDate = parseIsoDate(input.startDate);
  const maturityDate = parseIsoDate(input.maturityDate);

  if (!input.underlyings.length) warnings.push("Add at least one underlying before generating the schedule.");
  if (!startDate) warnings.push("Observation start date must be a valid ISO date.");
  if (!maturityDate) warnings.push("Maturity date must be a valid ISO date.");
  if (startDate && maturityDate && maturityDate < startDate) warnings.push("Maturity date must be on or after the observation start date.");
  const firstAutocallDate = parseIsoDate(input.firstAutocallObservationDate ?? input.startDate);
  if (input.firstAutocallObservationDate && !firstAutocallDate) warnings.push("First autocall observation must be a valid ISO date.");
  if (startDate && maturityDate && firstAutocallDate && (firstAutocallDate < startDate || firstAutocallDate > maturityDate)) warnings.push("First autocall observation must fall between the start and maturity dates.");
  if (input.autocallBarrierStep < 0 && input.autocallBarrierFloor > input.autocallBarrierStart) warnings.push("Autocall barrier floor cannot exceed the starting barrier when the step is negative.");
  if (input.underlyings.some((underlying) => !Number.isFinite(underlying.initialFixing) || underlying.initialFixing <= 0)) warnings.push("Each underlying needs a positive initial fixing.");
  if (input.includeConsolation && (!Number.isFinite(input.consolationRate ?? 50) || (input.consolationRate ?? 50) < 0 || (input.consolationRate ?? 50) > 100)) warnings.push("Consolation rate must be between 0 and 100 percent.");
  const consolationLowerBarrier = input.includeKip === false ? input.consolationLowerBarrier : input.kipBarrier;
  if (input.includeConsolation && input.includeKip === false && (!Number.isFinite(consolationLowerBarrier) || (consolationLowerBarrier ?? -1) < 0)) warnings.push("Consolation without a KIP component needs an explicit non-negative lower barrier.");
  if (input.includeConsolation && input.finalPayoffBarrier !== undefined && (!Number.isFinite(input.finalPayoffBarrier) || input.finalPayoffBarrier <= (consolationLowerBarrier ?? 0))) warnings.push("Final payoff barrier must be above the configured consolation lower barrier.");

  if (warnings.length || !startDate || !maturityDate || !firstAutocallDate) return { observationDates: [], rows: [], warnings };

  const maturityDateText = formatIsoDate(maturityDate);
  const couponObservationDates = buildObservationDates(startDate, maturityDate, input.couponFrequency ?? input.frequency);
  const rawAutocallObservationDates = buildObservationDates(startDate, maturityDate, input.autocallFrequency ?? input.frequency);
  const firstAutocallDateText = formatIsoDate(firstAutocallDate);
  const autocallLevelDates = rawAutocallObservationDates.filter((date) => date >= firstAutocallDateText);
  const autocallActionDates = autocallLevelDates.filter((date) => date !== maturityDateText);
  const observationDates = mergeObservationDates(couponObservationDates, autocallLevelDates, [maturityDateText]);
  const couponDateSet = new Set(couponObservationDates);
  const autocallDateSet = new Set(autocallActionDates);
  const couponIndexByDate = new Map(couponObservationDates.map((date, index) => [date, index]));
  const autocallIndexByDate = new Map(autocallLevelDates.map((date, index) => [date, index]));
  const rows: GeneratedScheduleRow[] = [];
  const paymentLag = Math.max(0, Math.trunc(input.paymentLagBusinessDays));
  let activeAutocallIndex = 0;

  observationDates.forEach((observationDate) => {
    const paymentDate = formatIsoDate(addBusinessDays(parseIsoDate(observationDate)!, paymentLag));
    const couponIndex = couponIndexByDate.get(observationDate);
    const autocallIndex = autocallIndexByDate.get(observationDate);
    if (autocallIndex !== undefined) activeAutocallIndex = autocallIndex;
    const rawAutocallBarrier = input.autocallBarrierStart + (input.autocallBarrierStep * activeAutocallIndex);
    const autocallBarrier = Math.max(input.autocallBarrierFloor, rawAutocallBarrier);
    if (couponDateSet.has(observationDate)) {
      input.underlyings.forEach((underlying) => {
        rows.push({
          rowId: `DIGITAL:${underlying.referenceNodeId}:${observationDate}`,
          rowKind: "COMPONENT",
          groupCode: "COUPON_COMPONENT",
          groupLabel: "Coupon components",
          legId: (couponIndex ?? 0) + 1,
          componentKind: "DIGITAL",
          optionType: "DIGITAL",
          exerciseStyle: "EUROPEAN",
          conditionRole: "COUPON_ELIGIBILITY",
          conditionOperator: "GE",
          conditionScope: input.scope,
          underlyingReferenceNodeId: underlying.referenceNodeId,
          underlyingLabel: underlying.label,
          participation: underlying.participation,
          couponRate: input.couponRate,
          strikeValue: underlying.initialFixing,
          strikePercent: 100,
          observationDate,
          paymentDate,
          conditionLevel: input.couponBarrierFollowsAutocall === false ? input.couponBarrier : autocallBarrier,
          conditionLowerLevel: null,
          conditionUpperLevel: null,
          conditionLevelBasis: "PCT_OF_INITIAL",
          payoutRate: null,
          actionCode: "PAY_COMPONENT",
          actionTarget: "COMPOSITION",
        });
      });
    }

    if (autocallDateSet.has(observationDate)) {
      rows.push({
        rowId: `ACTION:REDEEM_PARENT:${observationDate}`,
        rowKind: "ACTION",
        groupCode: "PARENT_ACTION",
        groupLabel: "Parent actions",
        legId: (autocallIndex ?? 0) + 1,
        componentKind: "PARENT_ACTION",
        optionType: null,
        exerciseStyle: null,
        conditionRole: "AUTOCALL",
        conditionOperator: "GE",
        conditionScope: input.scope,
        underlyingReferenceNodeId: null,
        underlyingLabel: `${input.scope} · ${input.underlyings.length} references`,
        participation: null,
        couponRate: null,
        strikeValue: null,
        strikePercent: null,
        observationDate,
        paymentDate,
        conditionLevel: autocallBarrier,
        conditionLowerLevel: null,
        conditionUpperLevel: null,
        conditionLevelBasis: "PCT_OF_INITIAL",
        payoutRate: null,
        actionCode: "REDEEM_PARENT",
        actionTarget: "PARENT",
      });
    }
  });

  if (input.includeConsolation) {
    const consolationRate = input.consolationRate ?? 50;
    const derivedFinalPayoffBarrier = Math.max(input.autocallBarrierFloor, input.autocallBarrierStart + (input.autocallBarrierStep * (autocallLevelDates.length - 1)));
    const finalPayoffBarrier = input.finalPayoffBarrier ?? derivedFinalPayoffBarrier;
    const lowerBarrier = input.includeKip === false ? input.consolationLowerBarrier : input.kipBarrier;
    if (lowerBarrier === undefined || !Number.isFinite(lowerBarrier) || lowerBarrier < 0) {
      warnings.push("Consolation without a KIP component needs an explicit non-negative lower barrier.");
    } else if (lowerBarrier >= finalPayoffBarrier) {
      warnings.push("Consolation upper barrier must be above the configured lower barrier.");
    } else {
      const paymentDate = formatIsoDate(addBusinessDays(maturityDate, paymentLag));
      rows.push({
        rowId: `ACTION:PAY_CONSOLATION:${maturityDateText}`,
        rowKind: "ACTION",
        groupCode: "CONSOLATION_ACTION",
        groupLabel: "Maturity consolation",
        legId: autocallLevelDates.length + 1,
        componentKind: "PARENT_ACTION",
        optionType: null,
        exerciseStyle: null,
        conditionRole: "CONSOLATION",
        conditionOperator: "RANGE",
        conditionScope: input.scope,
        underlyingReferenceNodeId: null,
        underlyingLabel: `${input.scope} · ${input.underlyings.length} references`,
        participation: null,
        couponRate: null,
        strikeValue: null,
        strikePercent: null,
        observationDate: maturityDateText,
        paymentDate,
        conditionLevel: finalPayoffBarrier,
        conditionLowerLevel: lowerBarrier,
        conditionUpperLevel: finalPayoffBarrier,
        conditionLowerInclusive: true,
        conditionUpperInclusive: false,
        conditionLevelBasis: "PCT_OF_INITIAL",
        payoutRate: consolationRate,
        actionCode: "PAY_CONSOLATION",
        actionTarget: "PARENT",
      });
    }
  }

  if (input.includeKip !== false) {
    const kipPaymentDate = formatIsoDate(addBusinessDays(maturityDate, paymentLag));
    input.underlyings.forEach((underlying) => {
      rows.push({
        rowId: `KIP:${underlying.referenceNodeId}:${maturityDateText}`,
        rowKind: "COMPONENT",
        groupCode: "CAPITAL_PROTECTION",
        groupLabel: "Capital protection",
        legId: autocallLevelDates.length + 2,
        componentKind: "VANILLA_OPTION",
        optionType: "PUT",
        exerciseStyle: "EUROPEAN",
        conditionRole: "CAPITAL_PROTECTION",
        conditionOperator: "LE",
        conditionScope: input.scope,
        underlyingReferenceNodeId: underlying.referenceNodeId,
        underlyingLabel: underlying.label,
        participation: -1,
        couponRate: null,
        strikeValue: underlying.initialFixing,
        strikePercent: 100,
        observationDate: maturityDateText,
        paymentDate: kipPaymentDate,
        conditionLevel: input.kipBarrier,
        conditionLowerLevel: null,
        conditionUpperLevel: null,
        conditionLevelBasis: "PCT_OF_INITIAL",
        payoutRate: null,
        actionCode: "PAY_COMPONENT",
        actionTarget: "COMPOSITION",
      });
    });
  }

  // Final redemption is a fallback maturity outcome. Keep it after other
  // maturity alternatives in the deterministic row order; lifecycle logic
  // still treats it as conditional on no earlier/mutually exclusive outcome.
  const finalPaymentDate = formatIsoDate(addBusinessDays(maturityDate, paymentLag));
  rows.push({
    rowId: `ACTION:FINAL_REDEMPTION:${maturityDateText}`,
    rowKind: "ACTION",
    groupCode: "FINAL_REDEMPTION",
    groupLabel: "Final redemption",
    legId: autocallLevelDates.length + 3,
    componentKind: "PARENT_ACTION",
    optionType: null,
    exerciseStyle: null,
    conditionRole: "FINAL_REDEMPTION",
    conditionOperator: "GE",
    conditionScope: input.scope,
    underlyingReferenceNodeId: null,
    underlyingLabel: `${input.scope} · maturity if not previously called`,
    participation: null,
    couponRate: null,
    strikeValue: null,
    strikePercent: null,
    observationDate: maturityDateText,
    paymentDate: finalPaymentDate,
    conditionLevel: 0,
    conditionLowerLevel: null,
    conditionUpperLevel: null,
    conditionLevelBasis: "PCT_OF_INITIAL",
    payoutRate: null,
    actionCode: "FINAL_REDEMPTION",
    actionTarget: "PARENT",
  });

  return { observationDates, rows, warnings };
}
