import type { ScheduleFrequency, ScheduleScope, ScheduleUnderlying } from "./schedule";
import type { ScheduleDraftRow } from "./draft";

/**
 * Governed structured-product archetypes. The composed-option values are
 * templates on the same parent instrument graph, not new node types.
 */
export type AutocallProductSubtype =
  | "AUTOCALL"
  | "AUTOCALL_CONSOLATION"
  | "PHOENIX"
  | "ATHENA"
  | "VANILLA_SPREAD_KIP"
  | "VANILLA_KIP"
  | "DIGITAL_KIP"
  | "RANGE_ACCRUAL"
  | "SUPERTRACKER";
export type InitialFixingBasis = "LEVEL" | "INDEX_POINTS" | "FX_RATE" | "PERCENT_OF_INITIAL";
export type FinalPaymentTreatment = "PAY_SEPARATELY" | "INCLUDE_IN_REDEMPTION" | "FORFEIT";
export type RangeObservationFrequency = "DAILY" | "WEEKLY" | "MONTHLY";
export type RangeAccrualBasis = "OBSERVATION_COUNT" | "CALENDAR_DAYS";
export type RangeNonBusinessDayRule = "BUSINESS_DAYS_ONLY" | "CARRY_FORWARD_PREVIOUS" | "CALENDAR_DAYS";

export type AutocallFormUnderlying = ScheduleUnderlying & {
  fixingBasis?: InitialFixingBasis;
  fixingDate?: string;
};

export type AutocallFormPayloadInput = {
  productName: string;
  internalCode: string;
  productType: AutocallProductSubtype;
  currencyId: string;
  issuerOrganisationId: string;
  guarantorOrganisationId: string;
  counterpartyOrganisationId: string;
  notional: string;
  scope: ScheduleScope;
  observationStyle: "DISCRETE" | "CONTINUOUS" | "FINAL_ONLY";
  memoryMode: "NONE" | "CONDITIONAL_CATCH_UP" | "ACCUMULATE_TO_REDEMPTION";
  finalPaymentTreatment?: FinalPaymentTreatment;
  calendarId: string;
  effectiveDate: string;
  startDate: string;
  maturityDate: string;
  firstAutocallObservationDate?: string;
  frequency: ScheduleFrequency;
  couponFrequency?: ScheduleFrequency;
  autocallFrequency?: ScheduleFrequency;
  paymentLagBusinessDays: string;
  couponRate: string;
  couponBarrier: string;
  couponBarrierFollowsAutocall?: boolean;
  autocallBarrierStart: string;
  autocallBarrierStep: string;
  autocallBarrierFloor: string;
  kipBarrier: string;
  finalPayoffBarrier: string;
  consolationLowerBarrier: string;
  includeKip: boolean;
  includeConsolation: boolean;
  consolationRate: string;
  rangeObservationFrequency?: RangeObservationFrequency;
  rangeAccrualBasis?: RangeAccrualBasis;
  rangeNonBusinessDayRule?: RangeNonBusinessDayRule;
  rangeLowerLevel?: string;
  rangeUpperLevel?: string;
  rangeCouponRatePerAnnum?: string;
  supertrackerParticipationRate?: string;
  supertrackerIncludeCap?: boolean;
  supertrackerCapReturn?: string;
  underlyings: AutocallFormUnderlying[];
  rows: ScheduleDraftRow[];
};

export type StructuredProductDraftPayload = {
  canonicalName: string;
  internalCode?: string;
  effectiveFrom: string;
  productSubtype: AutocallProductSubtype;
  issueCurrencyId: string;
  issuerOrganisationId?: string;
  guarantorOrganisationId?: string;
  counterpartyOrganisationId?: string;
  notionalAmount?: number;
  scope: ScheduleScope;
  observationStyle: AutocallFormPayloadInput["observationStyle"];
  memoryMode: AutocallFormPayloadInput["memoryMode"];
  finalPaymentTreatment: FinalPaymentTreatment | null;
  calendarId: string;
  startDate: string;
  maturityDate: string;
  firstAutocallObservationDate: string;
  frequency: ScheduleFrequency;
  couponFrequency: ScheduleFrequency;
  autocallFrequency: ScheduleFrequency;
  paymentLagBusinessDays: number;
  couponRate: number;
  couponBarrier: number;
  couponBarrierFollowsAutocall: boolean;
  autocallBarrierStart: number;
  autocallBarrierStep: number;
  autocallBarrierFloor: number;
  kipBarrier: number;
  finalPayoffBarrier?: number;
  consolationLowerBarrier?: number;
  includeKip: boolean;
  includeConsolation: boolean;
  consolationRate?: number;
  rangeObservationFrequency?: RangeObservationFrequency;
  rangeAccrualBasis?: RangeAccrualBasis;
  rangeNonBusinessDayRule?: RangeNonBusinessDayRule;
  rangeLowerLevel?: number;
  rangeUpperLevel?: number;
  rangeCouponRatePerAnnum?: number;
  supertrackerParticipationRate?: number;
  supertrackerIncludeCap?: boolean;
  supertrackerCapReturn?: number;
  underlyings: Array<{
    referenceNodeId: string;
    initialFixing: number;
    fixingDate: string;
    fixingBasis: InitialFixingBasis;
    fixingSource: "MANUAL";
    label?: string;
  }>;
  rows: Array<{
    rowId: string;
    rowKind: ScheduleDraftRow["rowKind"];
    groupCode: string;
    componentKind: ScheduleDraftRow["componentKind"];
    optionType: ScheduleDraftRow["optionType"];
    exerciseStyle: ScheduleDraftRow["exerciseStyle"];
    conditionRole: ScheduleDraftRow["conditionRole"];
    observationStyle?: "CONTINUOUS" | "DISCRETE" | "FINAL_ONLY";
    conditionOperator: ScheduleDraftRow["conditionOperator"];
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
    conditionLowerInclusive: boolean;
    conditionUpperInclusive: boolean;
    conditionLevelBasis: ScheduleDraftRow["conditionLevelBasis"];
    payoutRate: number | null;
    actionCode: ScheduleDraftRow["actionCode"];
    actionTarget: ScheduleDraftRow["actionTarget"];
  }>;
  submissionMode: "MANUAL";
};

function numberOrZero(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function optionalNumber(value: string): number | undefined {
  const parsed = Number(value);
  return value.trim() !== "" && Number.isFinite(parsed) ? parsed : undefined;
}

/**
 * Convert the UI projection into the versioned server draft contract.
 * Technical fields such as group labels, leg ids and draft row state stay in
 * the UI; the API receives only contractual fields it can validate and store.
 */
export function buildAutocallDraftPayload(input: AutocallFormPayloadInput): StructuredProductDraftPayload {
  const includeConsolation = input.includeConsolation || input.productType === "AUTOCALL_CONSOLATION";
  const consolationRow = input.rows.find((row) => row.actionCode === "PAY_CONSOLATION");
  const configuredConsolationLowerBarrier = optionalNumber(input.consolationLowerBarrier)
    ?? consolationRow?.conditionLowerLevel
    ?? undefined;
  const couponFrequency = input.couponFrequency ?? input.frequency;
  const autocallFrequency = input.autocallFrequency ?? input.frequency;
  const couponBarrierFollowsAutocall = input.couponBarrierFollowsAutocall ?? true;
  const firstAutocallObservationDate = input.firstAutocallObservationDate ?? input.startDate;
  const payload: StructuredProductDraftPayload = {
    canonicalName: input.productName.trim(),
    effectiveFrom: input.effectiveDate,
    productSubtype: input.productType,
    issueCurrencyId: input.currencyId,
    scope: input.scope,
    observationStyle: input.observationStyle,
    memoryMode: input.memoryMode,
    // A final treatment has no economic meaning without coupon memory. Emit
    // NULL rather than a misleading contractual value in that case.
    finalPaymentTreatment: input.memoryMode === "NONE" ? null : (input.finalPaymentTreatment ?? "PAY_SEPARATELY"),
    calendarId: input.calendarId,
    startDate: input.startDate,
    maturityDate: input.maturityDate,
    firstAutocallObservationDate,
    frequency: input.frequency,
    couponFrequency,
    autocallFrequency,
    paymentLagBusinessDays: Math.max(0, Math.trunc(numberOrZero(input.paymentLagBusinessDays))),
    couponRate: numberOrZero(input.couponRate),
    couponBarrier: numberOrZero(input.couponBarrier),
    couponBarrierFollowsAutocall,
    autocallBarrierStart: numberOrZero(input.autocallBarrierStart),
    autocallBarrierStep: numberOrZero(input.autocallBarrierStep),
    autocallBarrierFloor: numberOrZero(input.autocallBarrierFloor),
    kipBarrier: numberOrZero(input.kipBarrier),
    ...(includeConsolation
      ? { finalPayoffBarrier: optionalNumber(input.finalPayoffBarrier) ?? consolationRow?.conditionUpperLevel ?? 0 }
      : {}),
    ...(includeConsolation && !input.includeKip && configuredConsolationLowerBarrier !== undefined
      ? { consolationLowerBarrier: configuredConsolationLowerBarrier }
      : {}),
    includeKip: input.includeKip,
    includeConsolation,
    underlyings: input.underlyings.map((underlying) => ({
      referenceNodeId: underlying.referenceNodeId,
      initialFixing: underlying.initialFixing,
      fixingDate: underlying.fixingDate ?? input.startDate,
      fixingBasis: underlying.fixingBasis ?? "LEVEL",
      fixingSource: "MANUAL",
      ...(underlying.label.trim() ? { label: underlying.label.trim() } : {}),
    })),
    rows: input.rows.map((row) => ({
      rowId: row.rowId,
      rowKind: row.rowKind,
      groupCode: row.groupCode,
      componentKind: row.componentKind,
      optionType: row.optionType,
      exerciseStyle: row.exerciseStyle,
      conditionRole: row.conditionRole,
      ...(row.observationStyle ? { observationStyle: row.observationStyle } : {}),
      conditionOperator: row.conditionOperator,
      conditionScope: row.conditionScope,
      underlyingReferenceNodeId: row.underlyingReferenceNodeId,
      underlyingLabel: row.underlyingLabel,
      participation: row.participation,
      couponRate: row.couponRate,
      strikeValue: row.strikeValue,
      strikePercent: row.strikePercent,
      observationDate: row.observationDate,
      paymentDate: row.paymentDate,
      conditionLevel: row.conditionLevel,
      conditionLowerLevel: row.conditionLowerLevel,
      conditionUpperLevel: row.conditionUpperLevel,
      conditionLowerInclusive: row.conditionLowerInclusive ?? true,
      conditionUpperInclusive: row.conditionUpperInclusive ?? (row.conditionOperator !== "RANGE"),
      conditionLevelBasis: row.conditionLevelBasis,
      payoutRate: row.payoutRate,
      actionCode: row.actionCode,
      actionTarget: row.actionTarget,
    })),
    submissionMode: "MANUAL",
  };

  const internalCode = input.internalCode.trim();
  if (internalCode) payload.internalCode = internalCode;
  const issuerOrganisationId = input.issuerOrganisationId.trim();
  if (issuerOrganisationId) payload.issuerOrganisationId = issuerOrganisationId;
  const guarantorOrganisationId = input.guarantorOrganisationId.trim();
  if (guarantorOrganisationId) payload.guarantorOrganisationId = guarantorOrganisationId;
  const counterpartyOrganisationId = input.counterpartyOrganisationId.trim();
  if (counterpartyOrganisationId) payload.counterpartyOrganisationId = counterpartyOrganisationId;
  const notionalAmount = optionalNumber(input.notional);
  if (notionalAmount !== undefined) payload.notionalAmount = notionalAmount;
  if (includeConsolation) payload.consolationRate = numberOrZero(input.consolationRate);

  if (input.productType === "RANGE_ACCRUAL") {
    payload.rangeObservationFrequency = input.rangeObservationFrequency ?? "DAILY";
    payload.rangeAccrualBasis = input.rangeAccrualBasis ?? "OBSERVATION_COUNT";
    payload.rangeNonBusinessDayRule = input.rangeNonBusinessDayRule ?? "BUSINESS_DAYS_ONLY";
    payload.rangeLowerLevel = optionalNumber(input.rangeLowerLevel ?? "") ?? 0;
    payload.rangeUpperLevel = optionalNumber(input.rangeUpperLevel ?? "") ?? 0;
    payload.rangeCouponRatePerAnnum = optionalNumber(input.rangeCouponRatePerAnnum ?? "") ?? 0;
  }
  if (input.productType === "SUPERTRACKER") {
    payload.supertrackerParticipationRate = (optionalNumber(input.supertrackerParticipationRate ?? "") ?? 0) / 100;
    payload.supertrackerIncludeCap = input.supertrackerIncludeCap ?? false;
    if (input.supertrackerIncludeCap) payload.supertrackerCapReturn = optionalNumber(input.supertrackerCapReturn ?? "") ?? 0;
  }

  return payload;
}
