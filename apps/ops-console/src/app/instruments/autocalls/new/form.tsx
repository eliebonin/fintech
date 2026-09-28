"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  Chip,
  Divider,
  FormControlLabel,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";

import {
  flattenCurrencyGroups,
  createIdempotencyKey,
  listCurrenciesFromBff,
  listOrganisationsFromBff,
  searchReferenceNodesFromBff,
  submitStructuredProductProposalFromBff,
  BffApiError,
  type Currency,
  type OrganisationOption,
  type ReferenceNodeOption,
} from "@/lib/browser-api-client";
import {
  autocallLegSide,
  generateAutocallSchedule,
  groupComponentsByUnderlying,
  summarizeObservations,
  type GeneratedScheduleRow,
  type ScheduleFrequency,
  type ScheduleGenerationInput,
  type ScheduleScope,
  type ScheduleUnderlying,
} from "./schedule";
import { generateComposedOptionSchedule, type ComposedOptionLeg } from "./composed-option";
import { generateRangeAccrualSchedule, generateSupertrackerSchedule } from "./range-supertracker";
import {
  applyDraftCommand,
  createScheduleDraft,
  validateScheduleDraft,
  type DraftEditableField,
  type ScheduleDraftRow,
} from "./draft";
import { buildAutocallDraftPayload, type AutocallProductSubtype, type FinalPaymentTreatment } from "./payload";
import { isComposedOptionSubtype, isMaturityOnlySubtype, isRangeAccrualSubtype, isSupertrackerSubtype, productUiProfile, showsAutocallBarrierFloor, showsAutocallStepDownControls, showsMaturityConsolationControls } from "./product-profile";

type ReferenceLevel = "ANY" | "ECONOMIC" | "LISTING";

type UnderlyingDraft = ScheduleUnderlying & {
  nodeType: string;
  instrumentType: string | null;
  baseCurrency: string | null;
  fixingBasis: "LEVEL" | "INDEX_POINTS" | "FX_RATE" | "PERCENT_OF_INITIAL";
  fixingDate: string;
};

type ComposedLegDraft = ComposedOptionLeg & {
  strikePercentText: string;
  participationText: "1" | "-1";
  payoutRateText: string;
};

const PRODUCT_TYPES = [
  ["AUTOCALL", "Autocall standard"],
  ["AUTOCALL_CONSOLATION", "Autocall consolation"],
  ["PHOENIX", "Phoenix"],
  ["ATHENA", "Athena"],
  ["VANILLA_SPREAD_KIP", "Vanilla spread with KIP"],
  ["VANILLA_KIP", "Vanilla with KIP"],
  ["DIGITAL_KIP", "Digital with KIP"],
  ["RANGE_ACCRUAL", "Range accrual"],
  ["SUPERTRACKER", "Supertracker"],
] as const;

const CALENDAR_OPTIONS = [
  ["00000000-0000-7000-8000-000000000128", "London / Europe", "Europe/London"],
  ["00000000-0000-7000-8000-000000000129", "New York", "America/New_York"],
  ["00000000-0000-7000-8000-000000000130", "European composite", "Europe/Paris"],
  ["00000000-0000-7000-8000-000000000131", "FX global", "UTC"],
] as const;
const DEFAULT_CALENDAR_ID = CALENDAR_OPTIONS[0][0];

const FREQUENCIES: [ScheduleFrequency, string][] = [
  ["MONTHLY", "12 / year · Monthly"],
  ["QUARTERLY", "4 / year · Quarterly"],
  ["SEMI_ANNUAL", "2 / year · Semi-annual"],
  ["ANNUAL", "1 / year · Annual"],
];

const UNDERLYING_FILTERS: Record<string, { nodeType?: string[]; instrumentType?: string[]; listingEligible: boolean }> = {
  INDEX: { nodeType: ["INDEX"], listingEligible: false },
  EQUITY: { instrumentType: ["EQUITY"], listingEligible: true },
  ETP: { instrumentType: ["ETF", "ETC", "ETN", "EXCHANGE_TRADED_CERTIFICATE", "EXCHANGE_TRADED_VEHICLE", "ACTIVELY_MANAGED_CERTIFICATE"], listingEligible: true },
  FUND: { nodeType: ["FUND"], instrumentType: ["FUND", "FUND_SHARE_CLASS"], listingEligible: false },
  FX: { nodeType: ["FX_PAIR"], instrumentType: ["FX_FORWARD"], listingEligible: false },
  COMMODITY: { nodeType: ["COMMODITY"], listingEligible: false },
  CRYPTO: { instrumentType: ["DIGITAL_ASSET"], listingEligible: true },
  BOND: { instrumentType: ["BOND"], listingEligible: true },
  FUTURE: { instrumentType: ["FUTURE"], listingEligible: true },
  RATE_INDEX: { nodeType: ["RATE_INDEX"], listingEligible: false },
  CURRENCY: { nodeType: ["CURRENCY"], listingEligible: false },
};

const ASSET_TYPE_OPTIONS = [
  ["INDEX", "Index"],
  ["EQUITY", "Equity"],
  ["ETP", "ETF / ETP"],
  ["FUND", "Fund or share class"],
  ["FX", "FX pair / forward"],
  ["COMMODITY", "Commodity"],
  ["CRYPTO", "Cryptoasset"],
  ["BOND", "Bond"],
  ["FUTURE", "Future contract"],
  ["RATE_INDEX", "Rate index"],
  ["CURRENCY", "Currency"],
] as const;

const TECHNICAL_DETAILS_STORAGE_KEY = "ops-console.autocall.technical-details";

function isoYearsFromToday(years: number): string {
  const today = new Date();
  today.setUTCFullYear(today.getUTCFullYear() + years);
  return today.toISOString().slice(0, 10);
}

function asNumber(value: string, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function fixingBasisForAssetType(assetType: string): UnderlyingDraft["fixingBasis"] {
  if (assetType === "FX") return "FX_RATE";
  if (assetType === "INDEX" || assetType === "RATE_INDEX") return "INDEX_POINTS";
  return "LEVEL";
}

function formatNumber(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return value.toLocaleString("en-GB", { maximumFractionDigits: 8 });
}

function formatAutocallLegSide(participation: number | null): string {
  const side = autocallLegSide(participation);
  if (side === "LONG") return "Long";
  if (side === "SHORT") return "Short";
  return "—";
}

function optionLabel(option: ReferenceNodeOption): string {
  if (option.nodeType === "LISTING") {
    return `${option.canonicalName} · ${option.marketVenueMic ?? "venue"}${option.tradingSymbol ? ` · ${option.tradingSymbol}` : ""}`;
  }
  const kind = option.instrumentType ? `${option.nodeType} · ${option.instrumentType}` : option.nodeType;
  return `${option.canonicalName} · ${kind}`;
}

function groupRowsByObservation<T extends GeneratedScheduleRow>(rows: T[]): Map<string, T[]> {
  const groups = new Map<string, T[]>();
  rows.forEach((row) => {
    const observationRows = groups.get(row.observationDate) ?? [];
    observationRows.push(row);
    groups.set(row.observationDate, observationRows);
  });
  return groups;
}

function conditionText(row: GeneratedScheduleRow): string {
  if (row.conditionRole === "FINAL_REDEMPTION") return "Final redemption · if no earlier autocall";
  if (row.conditionRole === "OPTION_PAYOFF") return "Option payoff · European maturity payoff";
  if (row.conditionOperator === "RANGE") {
    return `${row.conditionRole.replaceAll("_", " ")} · ${formatNumber(row.conditionLowerLevel)}% ≤ performance < ${formatNumber(row.conditionUpperLevel)}% initial`;
  }
  const operator = row.conditionOperator === "GE" ? "≥" : "≤";
  return `${row.conditionRole.replaceAll("_", " ")} · ${operator} ${formatNumber(row.conditionLevel)}% initial`;
}

function actionLabel(actionCode: GeneratedScheduleRow["actionCode"]): string {
  if (actionCode === "REDEEM_PARENT") return "Redeem parent";
  if (actionCode === "PAY_CONSOLATION") return "Pay consolation";
  if (actionCode === "FINAL_REDEMPTION") return "Final redemption";
  return "Pay component";
}

function composedLegLabel(leg: ComposedLegDraft, underlyings: UnderlyingDraft[]): string {
  return underlyings.find((underlying) => underlying.referenceNodeId === leg.referenceNodeId)?.label ?? "Unresolved underlying";
}

export default function AutocallForm() {
  const [productType, setProductType] = useState<AutocallProductSubtype>("AUTOCALL");
  const [productName, setProductName] = useState("");
  const [internalCode, setInternalCode] = useState("");
  const [currencyId, setCurrencyId] = useState("");
  const [issuerOrganisationId, setIssuerOrganisationId] = useState("");
  const [guarantorOrganisationId, setGuarantorOrganisationId] = useState("");
  const [counterpartyOrganisationId, setCounterpartyOrganisationId] = useState("");
  const [notional, setNotional] = useState("");
  const [scope, setScope] = useState<ScheduleScope>("WORST_OF");

  const [assetType, setAssetType] = useState("INDEX");
  const [referenceLevel, setReferenceLevel] = useState<ReferenceLevel>("ANY");
  const [underlyingSelection, setUnderlyingSelection] = useState("");
  const [underlyings, setUnderlyings] = useState<UnderlyingDraft[]>([]);
  const [composedLegs, setComposedLegs] = useState<ComposedLegDraft[]>([]);
  const [results, setResults] = useState<ReferenceNodeOption[]>([]);
  const [underlyingState, setUnderlyingState] = useState<"loading" | "ready" | "error">("loading");
  const [catalogueRefresh, setCatalogueRefresh] = useState(0);

  const [startDate, setStartDate] = useState(isoYearsFromToday(1));
  const [maturityDate, setMaturityDate] = useState(isoYearsFromToday(2));
  const [firstAutocallObservationDate, setFirstAutocallObservationDate] = useState(isoYearsFromToday(1));
  const [effectiveDate, setEffectiveDate] = useState(isoYearsFromToday(0));
  const [frequency, setFrequency] = useState<ScheduleFrequency>("ANNUAL");
  const [couponFrequency, setCouponFrequency] = useState<ScheduleFrequency>("ANNUAL");
  const [paymentLagBusinessDays, setPaymentLagBusinessDays] = useState("2");
  const [calendarId, setCalendarId] = useState<string>(DEFAULT_CALENDAR_ID);
  const [couponRate, setCouponRate] = useState("6.5");
  const [couponBarrier, setCouponBarrier] = useState("100");
  const [couponBarrierFollowsAutocall, setCouponBarrierFollowsAutocall] = useState(true);
  const [autocallBarrierStart, setAutocallBarrierStart] = useState("100");
  const [autocallBarrierStep, setAutocallBarrierStep] = useState("-10");
  const [autocallBarrierFloor, setAutocallBarrierFloor] = useState("0");
  const [kipBarrier, setKipBarrier] = useState("65");
  const [kipObservationStyle, setKipObservationStyle] = useState<"CONTINUOUS" | "FINAL_ONLY">("CONTINUOUS");
  const [finalPayoffBarrier, setFinalPayoffBarrier] = useState("90");
  const [consolationLowerBarrier, setConsolationLowerBarrier] = useState("65");
  const [includeKip, setIncludeKip] = useState(true);
  const [consolationRate, setConsolationRate] = useState("50");
  const [rangeObservationFrequency, setRangeObservationFrequency] = useState<"DAILY" | "WEEKLY" | "MONTHLY">("DAILY");
  const [rangeAccrualBasis, setRangeAccrualBasis] = useState<"OBSERVATION_COUNT" | "CALENDAR_DAYS">("OBSERVATION_COUNT");
  const [rangeNonBusinessDayRule, setRangeNonBusinessDayRule] = useState<"BUSINESS_DAYS_ONLY" | "CARRY_FORWARD_PREVIOUS" | "CALENDAR_DAYS">("BUSINESS_DAYS_ONLY");
  const [rangeLowerLevel, setRangeLowerLevel] = useState("70");
  const [rangeUpperLevel, setRangeUpperLevel] = useState("130");
  const [rangeCouponRatePerAnnum, setRangeCouponRatePerAnnum] = useState("8");
  const [supertrackerParticipationRate, setSupertrackerParticipationRate] = useState("135");
  const [supertrackerIncludeCap, setSupertrackerIncludeCap] = useState(true);
  const [supertrackerCapReturn, setSupertrackerCapReturn] = useState("25");
  const [observationStyle, setObservationStyle] = useState("DISCRETE");
  const [memoryMode, setMemoryMode] = useState("NONE");
  const [finalPaymentTreatment, setFinalPaymentTreatment] = useState<FinalPaymentTreatment>("PAY_SEPARATELY");
  const [showSchedule, setShowSchedule] = useState(false);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const [technicalPreferenceLoaded, setTechnicalPreferenceLoaded] = useState(false);
  const [selectedObservationDate, setSelectedObservationDate] = useState<string | null>(null);
  const [showAllObservations, setShowAllObservations] = useState(false);
  const [showContractRows, setShowContractRows] = useState(false);
  const [editSchedule, setEditSchedule] = useState(false);
  const [draftRows, setDraftRows] = useState<ScheduleDraftRow[]>([]);
  const [draftDirty, setDraftDirty] = useState(false);
  const [draftBaselineFingerprint, setDraftBaselineFingerprint] = useState<string | null>(null);
  const [baselineChanged, setBaselineChanged] = useState(false);
  const [submissionState, setSubmissionState] = useState<"idle" | "submitting" | "submitted" | "error">("idle");
  const [submissionMessage, setSubmissionMessage] = useState<string | null>(null);
  const [submittedProposalId, setSubmittedProposalId] = useState<string | null>(null);
  const idempotencyKey = useRef<string | null>(null);

  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [organisations, setOrganisations] = useState<OrganisationOption[]>([]);
  const [catalogueState, setCatalogueState] = useState<"loading" | "ready" | "error">("loading");

  const selectedFilter = UNDERLYING_FILTERS[assetType] ?? { listingEligible: false };
  const effectiveReferenceLevel: ReferenceLevel = selectedFilter.listingEligible ? referenceLevel : "ANY";
  const nativeSelect = { inputLabel: { shrink: true }, select: { native: true } } as const;
  const floatedInput = { inputLabel: { shrink: true } } as const;
  const productProfile = productUiProfile(productType);
  const composedOption = isComposedOptionSubtype(productType);
  const rangeAccrual = isRangeAccrualSubtype(productType);
  const supertracker = isSupertrackerSubtype(productType);
  const maturityOnly = isMaturityOnlySubtype(productType) || rangeAccrual;
  const maturityConsolationEnabled = showsMaturityConsolationControls(productType);
  const stepDownControlsVisible = showsAutocallStepDownControls(productType);
  const barrierFloorVisible = showsAutocallBarrierFloor(productType, autocallBarrierStep);

  useEffect(() => {
    if (!composedOption) {
      setComposedLegs([]);
      return;
    }
    if (!underlyings.length) {
      setComposedLegs([]);
      return;
    }
    setComposedLegs((current) => {
      const available = new Set(underlyings.map((underlying) => underlying.referenceNodeId));
      const retained = current.filter((leg) => available.has(leg.referenceNodeId));
      if (retained.length) return retained;
      const first = underlyings[0];
      const base = {
        referenceNodeId: first.referenceNodeId,
        underlyingLabel: first.label,
        initialFixing: first.initialFixing,
      };
      if (productType === "VANILLA_SPREAD_KIP") {
        return [
          { ...base, legId: "long-call", optionType: "CALL", strikePercent: 100, strikePercentText: "100", participation: 1, participationText: "1", payoutRate: null, payoutRateText: "" },
          { ...base, legId: "short-call", optionType: "CALL", strikePercent: 110, strikePercentText: "110", participation: -1, participationText: "-1", payoutRate: null, payoutRateText: "" },
        ];
      }
      if (productType === "DIGITAL_KIP") {
        return [{ ...base, legId: "digital-payoff", optionType: "DIGITAL", strikePercent: 100, strikePercentText: "100", participation: 1, participationText: "1", payoutRate: 6.5, payoutRateText: "6.5" }];
      }
      return [{ ...base, legId: "vanilla-payoff", optionType: "CALL", strikePercent: 100, strikePercentText: "100", participation: 1, participationText: "1", payoutRate: null, payoutRateText: "" }];
    });
  }, [composedOption, productType, underlyings]);

  useEffect(() => {
    let active = true;
    setCatalogueState("loading");
    Promise.all([listCurrenciesFromBff(fetch, ["REGULAR"]), listOrganisationsFromBff(fetch)])
      .then(([currencyPayload, organisationPayload]) => {
        if (!active) return;
        setCurrencies(flattenCurrencyGroups(currencyPayload.data));
        setOrganisations(organisationPayload.data);
        setCatalogueState("ready");
      })
      .catch(() => {
        if (active) setCatalogueState("error");
      });
    return () => {
      active = false;
    };
  }, [catalogueRefresh]);

  useEffect(() => {
    const storedPreference = window.localStorage.getItem(TECHNICAL_DETAILS_STORAGE_KEY);
    if (storedPreference === "true") setShowTechnicalDetails(true);
    setTechnicalPreferenceLoaded(true);
  }, []);

  useEffect(() => {
    if (technicalPreferenceLoaded) window.localStorage.setItem(TECHNICAL_DETAILS_STORAGE_KEY, String(showTechnicalDetails));
  }, [showTechnicalDetails, technicalPreferenceLoaded]);

  useEffect(() => {
    let active = true;
    setUnderlyingSelection("");
    setUnderlyingState("loading");
    setResults([]);
    searchReferenceNodesFromBff("", { ...selectedFilter, referenceLevel: effectiveReferenceLevel })
      .then((payload) => {
        if (!active) return;
        setResults(payload.data);
        setUnderlyingState("ready");
      })
      .catch(() => {
        if (active) setUnderlyingState("error");
      });
    return () => {
      active = false;
    };
  }, [assetType, effectiveReferenceLevel, catalogueRefresh]);

  useEffect(() => {
    if (!selectedFilter.listingEligible && referenceLevel === "LISTING") setReferenceLevel("ANY");
  }, [referenceLevel, selectedFilter.listingEligible]);

  const scheduleInput: ScheduleGenerationInput = useMemo(() => ({
    startDate,
    maturityDate,
    firstAutocallObservationDate,
    frequency,
    couponFrequency,
    autocallFrequency: frequency,
    paymentLagBusinessDays: asNumber(paymentLagBusinessDays, 0),
    couponRate: asNumber(couponRate, 0),
    couponBarrier: asNumber(couponBarrier, 0),
    couponBarrierFollowsAutocall,
    autocallBarrierStart: asNumber(autocallBarrierStart, 0),
    autocallBarrierStep: asNumber(autocallBarrierStep, 0),
    autocallBarrierFloor: asNumber(autocallBarrierFloor, 0),
    kipBarrier: asNumber(kipBarrier, 0),
    consolationLowerBarrier: asNumber(consolationLowerBarrier, Number.NaN),
    finalPayoffBarrier: asNumber(finalPayoffBarrier, Number.NaN),
    includeKip,
    includeConsolation: maturityConsolationEnabled,
    consolationRate: asNumber(consolationRate, 50),
    scope,
    underlyings,
  }), [autocallBarrierFloor, autocallBarrierStart, autocallBarrierStep, consolationLowerBarrier, consolationRate, couponBarrier, couponBarrierFollowsAutocall, couponFrequency, couponRate, finalPayoffBarrier, firstAutocallObservationDate, frequency, includeKip, kipBarrier, maturityConsolationEnabled, maturityDate, paymentLagBusinessDays, productType, scope, startDate, underlyings]);

  const composedScheduleInput = useMemo(() => ({
    template: productType as "VANILLA_SPREAD_KIP" | "VANILLA_KIP" | "DIGITAL_KIP",
    startDate,
    maturityDate,
    paymentLagBusinessDays: asNumber(paymentLagBusinessDays, 0),
    kipBarrier: asNumber(kipBarrier, 0),
    includeKip,
    kipObservationStyle,
    scope,
    underlyings,
    legs: composedLegs.map((leg) => ({
      legId: leg.legId,
      referenceNodeId: leg.referenceNodeId,
      underlyingLabel: composedLegLabel(leg, underlyings),
      initialFixing: underlyings.find((underlying) => underlying.referenceNodeId === leg.referenceNodeId)?.initialFixing ?? leg.initialFixing,
      optionType: leg.optionType,
      strikePercent: asNumber(leg.strikePercentText, leg.strikePercent),
      participation: asNumber(leg.participationText, leg.participation),
      payoutRate: leg.payoutRateText.trim() === "" ? null : asNumber(leg.payoutRateText, leg.payoutRate ?? 0),
    })),
  }), [composedLegs, includeKip, kipBarrier, kipObservationStyle, maturityDate, paymentLagBusinessDays, productType, scope, startDate, underlyings]);

  const rangeScheduleInput = useMemo(() => ({
    startDate,
    maturityDate,
    couponFrequency: frequency,
    paymentLagBusinessDays: asNumber(paymentLagBusinessDays, 0),
    couponRatePerAnnum: asNumber(rangeCouponRatePerAnnum, 0),
    lowerLevel: asNumber(rangeLowerLevel, Number.NaN),
    upperLevel: asNumber(rangeUpperLevel, Number.NaN),
    observationFrequency: rangeObservationFrequency,
    accrualBasis: rangeAccrualBasis,
    nonBusinessDayRule: rangeNonBusinessDayRule,
    scope,
    underlyings,
  }), [frequency, maturityDate, paymentLagBusinessDays, rangeAccrualBasis, rangeCouponRatePerAnnum, rangeLowerLevel, rangeNonBusinessDayRule, rangeObservationFrequency, rangeUpperLevel, scope, startDate, underlyings]);

  const supertrackerScheduleInput = useMemo(() => ({
    startDate,
    maturityDate,
    paymentLagBusinessDays: asNumber(paymentLagBusinessDays, 0),
    participationRate: asNumber(supertrackerParticipationRate, 0),
    includeCap: supertrackerIncludeCap,
    capReturn: asNumber(supertrackerCapReturn, Number.NaN),
    kipBarrier: asNumber(kipBarrier, 0),
    includeKip,
    kipObservationStyle,
    scope,
    underlyings,
  }), [includeKip, kipBarrier, kipObservationStyle, maturityDate, paymentLagBusinessDays, scope, startDate, supertrackerCapReturn, supertrackerIncludeCap, supertrackerParticipationRate, underlyings]);

  const generated = useMemo(
    () => composedOption
      ? generateComposedOptionSchedule(composedScheduleInput)
      : rangeAccrual
        ? generateRangeAccrualSchedule(rangeScheduleInput)
        : supertracker
          ? generateSupertrackerSchedule(supertrackerScheduleInput)
          : generateAutocallSchedule(scheduleInput),
    [composedOption, composedScheduleInput, rangeAccrual, rangeScheduleInput, scheduleInput, supertracker, supertrackerScheduleInput],
  );
  const generatedFingerprint = useMemo(() => JSON.stringify(generated.rows), [generated.rows]);
  const displayRows: ScheduleDraftRow[] = useMemo(() => draftRows.length ? draftRows : createScheduleDraft(generated.rows), [draftRows, generated.rows]);
  const observationGroups = useMemo(() => groupRowsByObservation(displayRows), [displayRows]);
  const observationSummaries = useMemo(() => summarizeObservations(displayRows), [displayRows]);
  const componentCount = displayRows.filter((row) => row.rowKind === "COMPONENT").length;
  const actionCount = displayRows.filter((row) => row.rowKind === "ACTION").length;
  const draftValidationIssues = useMemo(() => validateScheduleDraft(displayRows), [displayRows]);
  const dateWarnings = useMemo(() => {
    const warnings: string[] = [];
    if (effectiveDate && startDate && effectiveDate > startDate) {
      warnings.push("Terms effective date is after the observation start; confirm that this is intentional.");
    }
    return warnings;
  }, [effectiveDate, startDate]);
  const selectedCurrency = currencies.find((currency) => currency.currencyId === currencyId);
  const underlyingHelper = underlyingState === "loading"
    ? "Loading active reference nodes…"
    : underlyingState === "error"
      ? "Reference catalogue unavailable; refresh and try again."
      : results.length
        ? `${results.length} active reference nodes available.`
        : "No active reference nodes match this category.";
  const canSubmit = Boolean(
      productName.trim()
      && currencyId
      && calendarId
      && effectiveDate
      && underlyings.length
      && (!composedOption || composedLegs.length)
      && displayRows.length
      && !generated.warnings.length
      && !draftValidationIssues.length
      && !baselineChanged
      && catalogueState === "ready"
      && submissionState !== "submitting"
      && submissionState !== "submitted",
  );

  useEffect(() => {
    const firstObservation = generated.observationDates[0] ?? null;
    setSelectedObservationDate((current) => current && generated.observationDates.includes(current) ? current : firstObservation);
    setShowAllObservations(false);
  }, [generated.observationDates]);

  useEffect(() => {
    if (draftBaselineFingerprint === null) {
      setDraftRows(createScheduleDraft(generated.rows));
      setDraftBaselineFingerprint(generatedFingerprint);
      setDraftDirty(false);
      return;
    }
    if (generatedFingerprint !== draftBaselineFingerprint && draftDirty) {
      setBaselineChanged(true);
      return;
    }
    if (generatedFingerprint !== draftBaselineFingerprint && !draftDirty) {
      setDraftRows(createScheduleDraft(generated.rows));
      setDraftBaselineFingerprint(generatedFingerprint);
      setBaselineChanged(false);
      setEditSchedule(false);
    }
  }, [draftBaselineFingerprint, draftDirty, generated.rows, generatedFingerprint]);

  function addUnderlying() {
    const selected = results.find((item) => item.referenceNodeId === underlyingSelection);
    if (!selected || underlyings.some((item) => item.referenceNodeId === selected.referenceNodeId)) return;
    setUnderlyings((current) => [...current, {
      referenceNodeId: selected.referenceNodeId,
      label: selected.canonicalName,
      nodeType: selected.nodeType,
      instrumentType: selected.instrumentType ?? null,
      baseCurrency: selected.baseCurrency ?? selected.tradingCurrency ?? null,
       initialFixing: 100,
       participation: 1,
       fixingBasis: fixingBasisForAssetType(assetType),
       fixingDate: startDate,
     }]);
    setUnderlyingSelection("");
    setShowSchedule(false);
  }

  function addComposedLeg() {
    const first = underlyings[0];
    if (!first || !composedOption) return;
    const nextIndex = composedLegs.length + 1;
    const isDigital = productType === "DIGITAL_KIP";
    setComposedLegs((current) => [...current, {
      legId: `leg-${nextIndex}`,
      referenceNodeId: first.referenceNodeId,
      underlyingLabel: first.label,
      initialFixing: first.initialFixing,
      optionType: isDigital ? "DIGITAL" : "CALL",
      strikePercent: 100,
      strikePercentText: "100",
      participation: 1,
      participationText: "1",
      payoutRate: isDigital ? 6.5 : null,
      payoutRateText: isDigital ? "6.5" : "",
    }]);
    setShowSchedule(false);
  }

  function updateComposedLeg(index: number, field: "referenceNodeId" | "optionType" | "strikePercentText" | "participationText" | "payoutRateText", value: string) {
    setComposedLegs((current) => current.map((leg, legIndex) => {
      if (legIndex !== index) return leg;
      if (field === "referenceNodeId") {
        const underlying = underlyings.find((item) => item.referenceNodeId === value);
        return underlying ? { ...leg, referenceNodeId: value, underlyingLabel: underlying.label, initialFixing: underlying.initialFixing } : leg;
      }
      if (field === "optionType") return { ...leg, optionType: value as ComposedLegDraft["optionType"] };
      if (field === "participationText") return { ...leg, participationText: value as "1" | "-1", participation: Number(value) };
      if (field === "strikePercentText") return { ...leg, strikePercentText: value, strikePercent: asNumber(value, 0) };
      return { ...leg, payoutRateText: value, payoutRate: value.trim() === "" ? null : asNumber(value, 0) };
    }));
    setShowSchedule(false);
  }

  function changeProductType(nextProductType: AutocallProductSubtype) {
    const previousProductType = productType;
    setProductType(nextProductType);
    if (nextProductType !== "PHOENIX") setCouponFrequency(frequency);
    const nextProfile = productUiProfile(nextProductType);
    setComposedLegs([]);
    if (isComposedOptionSubtype(nextProductType)) {
      setIncludeKip(true);
      setObservationStyle("FINAL_ONLY");
      setMemoryMode("NONE");
      setScope("SINGLE");
    }
    if (nextProductType === "RANGE_ACCRUAL") {
      setIncludeKip(false);
      setObservationStyle("DISCRETE");
      setMemoryMode("NONE");
      setScope("SINGLE");
      setFrequency("QUARTERLY");
    }
    if (nextProductType === "SUPERTRACKER") {
      setIncludeKip(true);
      setObservationStyle("FINAL_ONLY");
      setMemoryMode("NONE");
      setScope("SINGLE");
    }

    // Athena is the flat-barrier autocall convention. The field is disabled
    // while selected, so leaving Athena can safely restore the standard UI
    // default when no custom step was possible.
    if (nextProductType === "ATHENA") {
      setAutocallBarrierStep(nextProfile.autocallBarrierStep);
      setAutocallBarrierFloor("0");
    } else if (previousProductType === "ATHENA" && autocallBarrierStep === "0") {
      setAutocallBarrierStep("-10");
      setAutocallBarrierFloor("0");
    }

    // Coupon memory is an explicit term-sheet choice for every subtype. Do
    // not silently turn it on when the product subtype changes.
  }

  function updateUnderlying(index: number, field: "initialFixing" | "fixingDate", value: string) {
    setUnderlyings((current) => current.map((item, itemIndex) => {
      if (itemIndex !== index) return item;
      return field === "initialFixing"
        ? { ...item, initialFixing: asNumber(value, 0) }
        : { ...item, fixingDate: value };
    }));
  }

  function changeStartDate(next: string) {
    if (firstAutocallObservationDate === startDate) setFirstAutocallObservationDate(next);
    setStartDate(next);
  }

  function reset() {
    setProductType("AUTOCALL");
    setProductName("");
    setInternalCode("");
    setCurrencyId("");
    setIssuerOrganisationId("");
    setGuarantorOrganisationId("");
    setCounterpartyOrganisationId("");
    setNotional("");
    setScope("WORST_OF");
    setCalendarId(DEFAULT_CALENDAR_ID);
    const defaultStartDate = isoYearsFromToday(1);
    setEffectiveDate(isoYearsFromToday(0));
    setStartDate(defaultStartDate);
    setMaturityDate(isoYearsFromToday(2));
    setFrequency("ANNUAL");
    setCouponFrequency("ANNUAL");
    setFirstAutocallObservationDate(defaultStartDate);
    setPaymentLagBusinessDays("2");
    setUnderlyings([]);
    setComposedLegs([]);
    setConsolationRate("50");
    setRangeObservationFrequency("DAILY");
    setRangeAccrualBasis("OBSERVATION_COUNT");
    setRangeNonBusinessDayRule("BUSINESS_DAYS_ONLY");
    setRangeLowerLevel("70");
    setRangeUpperLevel("130");
    setRangeCouponRatePerAnnum("8");
    setSupertrackerParticipationRate("135");
    setSupertrackerIncludeCap(true);
    setSupertrackerCapReturn("25");
    setAutocallBarrierStart("100");
    setAutocallBarrierStep("-10");
    setAutocallBarrierFloor("0");
    setKipObservationStyle("CONTINUOUS");
    setCouponBarrier("100");
    setCouponBarrierFollowsAutocall(true);
    setMemoryMode("NONE");
    setFinalPaymentTreatment("PAY_SEPARATELY");
    setFinalPayoffBarrier("90");
    setConsolationLowerBarrier("65");
    setShowSchedule(false);
    setSelectedObservationDate(null);
    setShowAllObservations(false);
    setShowContractRows(false);
    setEditSchedule(false);
    setDraftRows([]);
    setDraftDirty(false);
    setDraftBaselineFingerprint(null);
    setBaselineChanged(false);
    setSubmissionState("idle");
    setSubmissionMessage(null);
    setSubmittedProposalId(null);
    idempotencyKey.current = null;
  }

  function updateDraftCell(draftRowId: string, field: DraftEditableField, rawValue: string) {
    const value = rawValue === "" ? null : Number(rawValue);
    if (value !== null && !Number.isFinite(value)) return;
    setDraftRows((current) => applyDraftCommand(current, { type: "UPDATE_CELL", draftRowId, field, value }));
    setDraftDirty(true);
  }

  function updateDraftPaymentDate(draftRowId: string, value: string) {
    setDraftRows((current) => applyDraftCommand(current, {
      type: "UPDATE_CELL",
      draftRowId,
      field: "paymentDate",
      value,
    }));
    setDraftDirty(true);
  }

  function discardDraftChanges() {
    setDraftRows(createScheduleDraft(generated.rows));
    setDraftBaselineFingerprint(generatedFingerprint);
    setDraftDirty(false);
    setBaselineChanged(false);
    setEditSchedule(false);
  }

  async function submitDraft() {
    if (!canSubmit) return;
    setSubmissionState("submitting");
    setSubmissionMessage(null);
    try {
      const payload = buildAutocallDraftPayload({
        productName,
        internalCode,
        productType,
        currencyId,
        issuerOrganisationId,
        guarantorOrganisationId,
        counterpartyOrganisationId,
        notional,
        scope,
        observationStyle: observationStyle as "DISCRETE" | "CONTINUOUS" | "FINAL_ONLY",
         memoryMode: memoryMode as "NONE" | "CONDITIONAL_CATCH_UP" | "ACCUMULATE_TO_REDEMPTION",
         finalPaymentTreatment,
         calendarId,
         effectiveDate,
         startDate,
         maturityDate,
         firstAutocallObservationDate,
        frequency,
        couponFrequency,
        paymentLagBusinessDays,
        couponRate,
        couponBarrier,
        couponBarrierFollowsAutocall,
        autocallBarrierStart,
        autocallBarrierStep,
        autocallBarrierFloor,
          kipBarrier,
          consolationLowerBarrier,
          finalPayoffBarrier,
        includeKip,
        includeConsolation: maturityConsolationEnabled,
        consolationRate,
        rangeObservationFrequency,
        rangeAccrualBasis,
        rangeNonBusinessDayRule,
        rangeLowerLevel,
        rangeUpperLevel,
        rangeCouponRatePerAnnum,
        supertrackerParticipationRate,
        supertrackerIncludeCap,
        supertrackerCapReturn,
        underlyings,
        rows: displayRows,
      });
      const response = await submitStructuredProductProposalFromBff(payload, idempotencyKey.current ?? (idempotencyKey.current = createIdempotencyKey()));
      setSubmittedProposalId(response.data.proposalId);
      setSubmissionState("submitted");
      setSubmissionMessage("Draft proposal submitted for steward review. No canonical records are approved yet.");
    } catch (error: unknown) {
      setSubmissionState("error");
      setSubmissionMessage(error instanceof BffApiError ? error.message : "The structured-product proposal could not be submitted.");
    }
  }

  return (
    <Box sx={{ bgcolor: "#f3f6fb", minHeight: "100vh", p: { xs: 2, md: 4 } }}>
      <Box sx={{ maxWidth: 1500, mx: "auto" }}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.25} sx={{ mb: 2, alignItems: { md: "center" } }}>
          <Typography variant="h5" sx={{ fontWeight: 800, flex: 1 }}>New structured product</Typography>
          <Button size="small" onClick={reset}>↻ Reset</Button>
          <Button size="small" onClick={() => setCatalogueRefresh((value) => value + 1)}>↻ Refresh dropdowns</Button>
          <Button variant="contained" onClick={() => setShowSchedule(true)} disabled={!underlyings.length}>Generate schedule</Button>
          <Chip label="Draft / review only" color="warning" variant="outlined" />
          <FormControlLabel control={<Switch size="small" checked={showTechnicalDetails} onChange={(event) => setShowTechnicalDetails(event.target.checked)} />} label="Show reference IDs" sx={{ ml: { md: 1 }, mr: 0, whiteSpace: "nowrap" }} />
        </Stack>

        <Alert severity="info" sx={{ mb: 2 }}>This screen builds a draft contractual graph. Submit it for steward review; approval creates the parent instrument, fresh option components, schedules, conditions, actions, and fixing provenance. It does not price the product.</Alert>
        {productType === "AUTOCALL_CONSOLATION" && <Alert severity="info" sx={{ mb: 2 }}>Autocall consolation is a governed subtype of the structured-product instrument. Its maturity action pays the configured rate when final performance is between the KIP barrier and the final scheduled payoff barrier.</Alert>}
        {maturityConsolationEnabled && !includeKip && <Alert severity="warning" sx={{ mb: 2 }}>KIP is disabled. Enter an explicit consolation lower barrier below. This bounds the maturity consolation range but does not create a capital-protection leg.</Alert>}
        {(productType === "ATHENA" || productType === "PHOENIX" || rangeAccrual || supertracker) && <Alert severity="info" sx={{ mb: 2 }}>{productProfile.helperText}</Alert>}
        {composedOption && <Alert severity="info" sx={{ mb: 2 }}>{productProfile.helperText} The preview creates one fresh child option per payoff leg; the KIP is a separate conditional component on the parent graph.</Alert>}
        {submissionMessage && <Alert severity={submissionState === "error" ? "error" : "success"} sx={{ mb: 2 }}>{submissionMessage}{submittedProposalId && <Typography variant="caption" sx={{ display: "block", mt: 0.5, fontFamily: "monospace" }}>Proposal {submittedProposalId}</Typography>}</Alert>}
        {catalogueState === "error" && <Alert severity="warning" sx={{ mb: 2 }}>Currency and organisation catalogues could not be loaded. Refresh the dropdowns or continue with provider enrichment later.</Alert>}
        {!!dateWarnings.length && <Stack spacing={1} sx={{ mb: 2 }}>{dateWarnings.map((warning) => <Alert severity="warning" key={warning}>{warning}</Alert>)}</Stack>}

        <Stack spacing={2.5}>
          <Card sx={{ p: { xs: 2, md: 3 } }}>
            <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>1 · ECONOMIC IDENTITY AND PARTIES</Typography>
            <Typography variant="h6">What is the parent product?</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>These fields describe the structured-product instrument. Issuer, guarantor, and counterparty are separate party relationships.</Typography>
            <Stack spacing={2} sx={{ mt: 2 }}>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField label="Structure name" value={productName} onChange={(event) => setProductName(event.target.value)} required fullWidth slotProps={floatedInput} helperText="Canonical display name for this specific issued product." />
                <TextField label="Internal code (optional)" value={internalCode} onChange={(event) => setInternalCode(event.target.value)} fullWidth slotProps={floatedInput} helperText="Stable operational code; UUID remains the identity." />
                <TextField select label="Product subtype" value={productType} onChange={(event) => changeProductType(event.target.value as AutocallProductSubtype)} sx={{ minWidth: { md: 230 } }} slotProps={nativeSelect} helperText={productProfile.helperText}>
                  {PRODUCT_TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </TextField>
              </Stack>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField select label="Issue currency" value={currencyId} onChange={(event) => setCurrencyId(event.target.value)} fullWidth slotProps={nativeSelect} helperText={catalogueState === "loading" ? "Loading regular currencies…" : selectedCurrency ? selectedCurrency.displayName : "Choose the currency of issuance and principal terms."}>
                  <option value="">— Select currency —</option>
                  {currencies.map((currency) => <option key={currency.currencyId} value={currency.currencyId}>{currency.currencyCode} · {currency.displayName}</option>)}
                </TextField>
                 <TextField label="Issue notional (optional)" value={notional} onChange={(event) => setNotional(event.target.value)} type="number" fullWidth slotProps={floatedInput} helperText="Contractual issue amount, not a trade quantity." />
              </Stack>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField select label="Issuer organisation" value={issuerOrganisationId} onChange={(event) => setIssuerOrganisationId(event.target.value)} fullWidth slotProps={nativeSelect} helperText={catalogueState === "loading" ? "Loading active organisations…" : "Select the legal issuer; create or resolve it separately if missing."}>
                  <option value="">— Not specified —</option>
                  {organisations.map((organisation) => <option key={organisation.organisationId} value={organisation.organisationId}>{organisation.displayName}{organisation.legalName ? ` · ${organisation.legalName}` : ""}</option>)}
                </TextField>
                <TextField select label="Guarantor organisation (optional)" value={guarantorOrganisationId} onChange={(event) => setGuarantorOrganisationId(event.target.value)} fullWidth slotProps={nativeSelect} helperText="A guarantee is a party relationship, not an issuer replacement.">
                  <option value="">— No guarantor —</option>
                  {organisations.map((organisation) => <option key={organisation.organisationId} value={organisation.organisationId}>{organisation.displayName}</option>)}
                </TextField>
                <TextField select label="Counterparty / distributor (optional)" value={counterpartyOrganisationId} onChange={(event) => setCounterpartyOrganisationId(event.target.value)} fullWidth slotProps={nativeSelect} helperText="Operational trade context; not part of the economic instrument identity.">
                  <option value="">— Not specified —</option>
                  {organisations.map((organisation) => <option key={organisation.organisationId} value={organisation.organisationId}>{organisation.displayName}</option>)}
                </TextField>
              </Stack>
            </Stack>
          </Card>

          <Card sx={{ p: { xs: 2, md: 3 } }}>
            <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>2 · UNDERLYING REFERENCES</Typography>
            <Typography variant="h6">Which references drive the payoff?</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{composedOption ? "The stored value is the canonical reference-node UUID. Add the economic underlyings here; the signed option legs are configured separately and become fresh child instruments on approval." : "The stored value is the canonical reference-node UUID. Initial fixings are product-specific terms; standard autocall component sides are generated by the payoff template."}</Typography>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mt: 2, alignItems: "flex-start" }}>
              <TextField select label="Reference category" value={assetType} onChange={(event) => setAssetType(event.target.value)} sx={{ minWidth: { md: 190 } }} slotProps={nativeSelect} helperText="Determines which active reference nodes are offered.">
                {ASSET_TYPE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </TextField>
              <TextField select label="Reference level" value={effectiveReferenceLevel} onChange={(event) => setReferenceLevel(event.target.value as ReferenceLevel)} sx={{ minWidth: { md: 230 } }} slotProps={nativeSelect} helperText={selectedFilter.listingEligible ? "Any identity, economic node, or venue listing." : "Venue listing does not apply to this reference category."}>
                <option value="ANY">Any eligible reference</option><option value="ECONOMIC">Economic/reference node</option><option value="LISTING" disabled={!selectedFilter.listingEligible}>Venue listing only{selectedFilter.listingEligible ? "" : " (not applicable)"}</option>
              </TextField>
              <TextField select label="Canonical underlying" value={underlyingSelection} onChange={(event) => setUnderlyingSelection(event.target.value)} fullWidth disabled={underlyingState !== "ready" || !results.length} slotProps={nativeSelect} helperText={underlyingHelper}>
                <option value="">{underlyingState === "ready" && results.length ? "— Select a reference —" : underlyingHelper}</option>
                {results.map((result) => <option key={result.referenceNodeId} value={result.referenceNodeId}>{optionLabel(result)}</option>)}
              </TextField>
              <Button variant="outlined" onClick={addUnderlying} disabled={!underlyingSelection} sx={{ mt: { md: 1 } }}>Add</Button>
            </Stack>
            {!!underlyings.length && <TableContainer sx={{ mt: 2, border: "1px solid", borderColor: "divider", borderRadius: 1.5 }}>
               <Table size="small"><TableHead><TableRow><TableCell>Underlying</TableCell>{showTechnicalDetails && <TableCell>Reference node</TableCell>}<TableCell>Initial fixing</TableCell><TableCell>Fixing date</TableCell><TableCell>Base / quote context</TableCell><TableCell /></TableRow></TableHead>
                 <TableBody>{underlyings.map((underlying, index) => <TableRow key={underlying.referenceNodeId}>
                   <TableCell><Typography sx={{ fontWeight: 700 }}>{underlying.label}</Typography><Typography variant="caption" color="text.secondary">{underlying.nodeType}{underlying.instrumentType ? ` · ${underlying.instrumentType}` : ""}</Typography></TableCell>
                   {showTechnicalDetails && <TableCell><Typography variant="caption" sx={{ fontFamily: "monospace" }}>{underlying.referenceNodeId}</Typography></TableCell>}
                    <TableCell><TextField size="small" type="number" value={underlying.initialFixing} onChange={(event) => updateUnderlying(index, "initialFixing", event.target.value)} slotProps={{ ...floatedInput, htmlInput: { step: "any", min: "0" } }} /></TableCell>
                    <TableCell><TextField size="small" type="date" value={underlying.fixingDate} onChange={(event) => updateUnderlying(index, "fixingDate", event.target.value)} slotProps={nativeSelect} /></TableCell>
                  <TableCell>{underlying.baseCurrency ?? "—"}</TableCell>
                  <TableCell><Button color="error" size="small" onClick={() => { setUnderlyings((current) => current.filter((_, itemIndex) => itemIndex !== index)); setShowSchedule(false); }}>Remove</Button></TableCell>
                </TableRow>)}</TableBody>
              </Table>
            </TableContainer>}
            <Stack direction="row" spacing={1} sx={{ mt: 2, flexWrap: "wrap" }}><Chip label={`Scope · ${scope}`} color="primary" variant="outlined" /><Chip label={`${underlyings.length} underlying${underlyings.length === 1 ? "" : "s"}`} variant="outlined" /></Stack>
            {composedOption && <Box sx={{ mt: 2 }}>
              <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ alignItems: { md: "center" }, mb: 1 }}>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Option payoff legs</Typography>
                  <Typography variant="body2" color="text.secondary">These are the signed child options in the composition. A spread normally uses one long and one short leg; the KIP is generated separately below.</Typography>
                </Box>
                <Button size="small" variant="outlined" onClick={addComposedLeg} disabled={!underlyings.length}>Add payoff leg</Button>
              </Stack>
              {!composedLegs.length && <Alert severity="info">Add an underlying first, then add at least one payoff leg.</Alert>}
              {!!composedLegs.length && <TableContainer sx={{ border: "1px solid", borderColor: "divider", borderRadius: 1.5, overflowX: "auto" }}>
                <Table size="small" aria-label="Composed option payoff legs">
                  <TableHead><TableRow sx={{ bgcolor: "#f8fafc" }}>{["Underlying", "Option", "Strike (% initial)", "Side", "Digital payout (%)", ""].map((header) => <TableCell key={header} sx={{ fontWeight: 800, whiteSpace: "nowrap" }}>{header}</TableCell>)}</TableRow></TableHead>
                  <TableBody>{composedLegs.map((leg, index) => <TableRow key={leg.legId} hover>
                    <TableCell sx={{ minWidth: 180 }}><TextField select size="small" value={leg.referenceNodeId} onChange={(event) => updateComposedLeg(index, "referenceNodeId", event.target.value)} fullWidth slotProps={nativeSelect}>{underlyings.map((underlying) => <option key={underlying.referenceNodeId} value={underlying.referenceNodeId}>{underlying.label}</option>)}</TextField></TableCell>
                    <TableCell sx={{ minWidth: 130 }}><TextField select size="small" value={leg.optionType} onChange={(event) => updateComposedLeg(index, "optionType", event.target.value)} fullWidth slotProps={nativeSelect}><option value="CALL">Call</option><option value="PUT">Put</option>{productType === "DIGITAL_KIP" && <option value="DIGITAL">Digital</option>}</TextField></TableCell>
                    <TableCell sx={{ minWidth: 150 }}><TextField size="small" type="number" value={leg.strikePercentText} onChange={(event) => updateComposedLeg(index, "strikePercentText", event.target.value)} fullWidth slotProps={{ ...floatedInput, htmlInput: { step: "any", min: "0" } }} /></TableCell>
                    <TableCell sx={{ minWidth: 110 }}><TextField select size="small" value={leg.participationText} onChange={(event) => updateComposedLeg(index, "participationText", event.target.value)} fullWidth slotProps={nativeSelect}><option value="1">Long</option><option value="-1">Short</option></TextField></TableCell>
                    <TableCell sx={{ minWidth: 150 }}>{leg.optionType === "DIGITAL" ? <TextField size="small" type="number" value={leg.payoutRateText} onChange={(event) => updateComposedLeg(index, "payoutRateText", event.target.value)} fullWidth slotProps={{ ...floatedInput, htmlInput: { step: "any", min: "0", max: "100" } }} /> : <Typography variant="body2" color="text.secondary">Not applicable</Typography>}</TableCell>
                    <TableCell><Button color="error" size="small" onClick={() => { setComposedLegs((current) => current.filter((_, legIndex) => legIndex !== index)); setShowSchedule(false); }}>Remove</Button></TableCell>
                  </TableRow>)}</TableBody>
                </Table>
              </TableContainer>}
            </Box>}
          </Card>

          <Card sx={{ p: { xs: 2, md: 3 } }}>
            <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>3 · SCHEDULE AND PAYOFF PARAMETERS</Typography>
            <Typography variant="h6">How should the contract observe and pay?</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>These inputs generate explicit schedule events, component terms, condition groups, and parent actions. The generated grid is a review projection of that graph.</Typography>
            <Stack spacing={2} sx={{ mt: 2 }}>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField label="Terms effective date" type="date" value={effectiveDate} onChange={(event) => setEffectiveDate(event.target.value)} fullWidth slotProps={nativeSelect} helperText="Date on which this contractual terms version becomes effective. It is separate from the first observation date." />
                <TextField label="Observation start" type="date" value={startDate} onChange={(event) => changeStartDate(event.target.value)} fullWidth slotProps={nativeSelect} helperText="First scheduled observation date." />
                <TextField label="Maturity date" type="date" value={maturityDate} onChange={(event) => setMaturityDate(event.target.value)} fullWidth slotProps={nativeSelect} helperText="Final valuation/maturity date." />
                {composedOption || supertracker ? <Alert severity="info" sx={{ width: "100%" }}>This template has a single final valuation event. Components and parent redemption settle on the maturity date.</Alert> : rangeAccrual ? <TextField select label="Coupon period frequency" value={frequency} onChange={(event) => { const next = event.target.value as ScheduleFrequency; setFrequency(next); setCouponFrequency(next); }} fullWidth slotProps={nativeSelect} helperText="How often the range-accrual coupon is paid. The in-range observation cadence is configured separately below.">{FREQUENCIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</TextField> : productType === "PHOENIX" ? <>
                  <TextField select label="Coupon frequency" value={couponFrequency} onChange={(event) => setCouponFrequency(event.target.value as ScheduleFrequency)} fullWidth slotProps={nativeSelect} helperText="Coupon eligibility/payment cadence — choose N coupon periods per year independently of autocall observations.">{FREQUENCIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</TextField>
                  <TextField select label="Autocall observation frequency" value={frequency} onChange={(event) => { const next = event.target.value as ScheduleFrequency; setFrequency(next); }} fullWidth slotProps={nativeSelect} helperText="Parent redemption test cadence — choose M autocall observations per year.">{FREQUENCIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</TextField>
                </> : <TextField select label="Observation frequency" value={frequency} onChange={(event) => { const next = event.target.value as ScheduleFrequency; setFrequency(next); setCouponFrequency(next); }} fullWidth slotProps={nativeSelect} helperText="For this product, coupon and autocall observations use the same cadence.">{FREQUENCIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</TextField>}
              </Stack>
              {rangeAccrual && <Card variant="outlined" sx={{ p: 2, bgcolor: "#fbfdff" }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Range-accrual coupon convention</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>The coupon is annualised and multiplied by the qualifying observation fraction. The preview remains at coupon-period level; detailed fixings are evaluated later from the persisted convention.</Typography>
                <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mt: 1.5 }}>
                  <TextField label="Coupon rate per annum (%)" type="number" value={rangeCouponRatePerAnnum} onChange={(event) => setRangeCouponRatePerAnnum(event.target.value)} fullWidth slotProps={{ ...floatedInput, htmlInput: { step: "any", min: "0" } }} helperText="Annual rate before the in-range accrual fraction is applied." />
                  <TextField label="Lower range (% initial)" type="number" value={rangeLowerLevel} onChange={(event) => setRangeLowerLevel(event.target.value)} fullWidth slotProps={{ ...floatedInput, htmlInput: { step: "any", min: "0" } }} />
                  <TextField label="Upper range (% initial)" type="number" value={rangeUpperLevel} onChange={(event) => setRangeUpperLevel(event.target.value)} fullWidth slotProps={{ ...floatedInput, htmlInput: { step: "any", min: "0" } }} />
                </Stack>
                <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mt: 1.5 }}>
                  <TextField select label="In-range observation frequency" value={rangeObservationFrequency} onChange={(event) => setRangeObservationFrequency(event.target.value as "DAILY" | "WEEKLY" | "MONTHLY")} fullWidth slotProps={nativeSelect} helperText="How often the underlying is tested inside each coupon period."><option value="DAILY">Daily</option><option value="WEEKLY">Weekly</option><option value="MONTHLY">Monthly</option></TextField>
                  <TextField select label="Accrual denominator" value={rangeAccrualBasis} onChange={(event) => setRangeAccrualBasis(event.target.value as "OBSERVATION_COUNT" | "CALENDAR_DAYS")} fullWidth slotProps={nativeSelect} helperText="Observation count divides qualifying fixings by scheduled fixings; calendar days divides qualifying days by calendar days."><option value="OBSERVATION_COUNT">Observation count</option><option value="CALENDAR_DAYS">Calendar days</option></TextField>
                  <TextField select label="Non-business-day rule" value={rangeNonBusinessDayRule} onChange={(event) => setRangeNonBusinessDayRule(event.target.value as "BUSINESS_DAYS_ONLY" | "CARRY_FORWARD_PREVIOUS" | "CALENDAR_DAYS")} fullWidth slotProps={nativeSelect} helperText="Keep this explicit; final holiday and fixing calendars are governed outside this preview."><option value="BUSINESS_DAYS_ONLY">Business days only</option><option value="CARRY_FORWARD_PREVIOUS">Carry forward previous fixing</option><option value="CALENDAR_DAYS">Calendar days</option></TextField>
                </Stack>
              </Card>}
              {supertracker && <Card variant="outlined" sx={{ p: 2, bgcolor: "#fbfdff" }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Supertracker maturity payoff</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>The positive participation is stored as a signed composition multiplier. A cap is a short call struck at 100% plus the entered underlying return cap.</Typography>
                <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mt: 1.5, alignItems: { md: "center" } }}>
                  <TextField label="Upside participation (%)" type="number" value={supertrackerParticipationRate} onChange={(event) => setSupertrackerParticipationRate(event.target.value)} fullWidth slotProps={{ ...floatedInput, htmlInput: { step: "any", min: "0" } }} helperText="135 means 1.35× exposure to positive underlying return." />
                  <FormControlLabel control={<Switch checked={supertrackerIncludeCap} onChange={(event) => setSupertrackerIncludeCap(event.target.checked)} />} label="Cap leveraged upside" sx={{ minWidth: { md: 230 } }} />
                  {supertrackerIncludeCap && <TextField label="Underlying cap return (%)" type="number" value={supertrackerCapReturn} onChange={(event) => setSupertrackerCapReturn(event.target.value)} fullWidth slotProps={{ ...floatedInput, htmlInput: { step: "any", min: "0" } }} helperText="25 means the leveraged upside flattens once underlying return reaches +25%." />}
                </Stack>
              </Card>}
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                {!maturityOnly && !rangeAccrual && <TextField label="First autocall observation" type="date" value={firstAutocallObservationDate} onChange={(event) => setFirstAutocallObservationDate(event.target.value)} fullWidth slotProps={nativeSelect} helperText="Earliest date on which the parent may redeem early. Coupons before this date can still be observed; defaults to the observation start." />}
                <TextField label="Payment lag (business days)" type="number" value={paymentLagBusinessDays} onChange={(event) => setPaymentLagBusinessDays(event.target.value)} fullWidth slotProps={floatedInput} helperText="Preview skips weekends; production uses the governed calendar." />
                {!composedOption && !rangeAccrual && !supertracker && memoryMode !== "NONE" && <Tooltip
                  arrow
                  placement="top"
                  title="Controls what happens to unpaid accrued coupon memory at maturity. Pay separately creates a separate coupon cashflow; include in redemption rolls the memory into the maturity redemption; forfeit cancels unpaid memory. This does not decide whether a coupon is earned."
                >
                  <Box sx={{ width: "100%" }}>
                    <TextField select label="Final coupon treatment" value={finalPaymentTreatment} onChange={(event) => setFinalPaymentTreatment(event.target.value as FinalPaymentTreatment)} fullWidth slotProps={nativeSelect} helperText="If coupon memory is accrued at maturity: pay separately, include in redemption, or forfeit it.">
                      <option value="PAY_SEPARATELY">Pay separately</option>
                      <option value="INCLUDE_IN_REDEMPTION">Include in redemption</option>
                      <option value="FORFEIT">Forfeit unpaid memory</option>
                    </TextField>
                  </Box>
                </Tooltip>}
              </Stack>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField select label="Underlying scope" value={scope} onChange={(event) => setScope(event.target.value as ScheduleScope)} fullWidth slotProps={nativeSelect} helperText={supertracker ? "The first supertracker slice uses one underlying." : "Best-of uses the maximum underlying performance; worst-of uses the minimum. Weighted baskets and per-underlying outcomes are not enabled in this slice."}><option value="SINGLE">Single underlying</option><option value="BEST_OF">Best-of (maximum)</option><option value="WORST_OF">Worst-of (minimum)</option></TextField>
                <TextField select label="Observation style" value={observationStyle} onChange={(event) => setObservationStyle(event.target.value)} fullWidth disabled={composedOption || rangeAccrual || supertracker} slotProps={nativeSelect} helperText={composedOption ? includeKip ? "Payoff components are final-only; the KIP observation can be selected separately below." : "Payoff components are final-only; no KIP component is included." : rangeAccrual ? "Range coupons use discrete period observations; the in-range cadence is configured above." : supertracker ? "Supertracker components are final-only." : undefined}><option value="DISCRETE">Discrete scheduled</option><option value="CONTINUOUS">Continuous</option><option value="FINAL_ONLY">Final only</option></TextField>
                {!composedOption && !rangeAccrual && !supertracker && <TextField select label="Coupon memory" value={memoryMode} onChange={(event) => { const next = event.target.value; setMemoryMode(next); if (next === "NONE") setFinalPaymentTreatment("PAY_SEPARATELY"); }} fullWidth slotProps={nativeSelect} helperText={productType === "PHOENIX" ? "Memory is off by default; enable it only when the term sheet provides catch-up or maturity arrears." : "Stored in the coupon programme; choose only when the term sheet provides memory."}><option value="NONE">No memory</option><option value="CONDITIONAL_CATCH_UP">Conditional catch-up</option><option value="ACCUMULATE_TO_REDEMPTION">Accumulate to redemption</option></TextField>}
                {!composedOption && !rangeAccrual && !supertracker && <TextField label="Coupon rate per period (%)" type="number" value={couponRate} onChange={(event) => setCouponRate(event.target.value)} fullWidth slotProps={{ ...floatedInput, htmlInput: { step: "any" } }} />}
              </Stack>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField select label="Schedule calendar" value={calendarId} onChange={(event) => setCalendarId(event.target.value)} fullWidth slotProps={nativeSelect} helperText="Governed calendar used for business-day payment lag and session rules.">
                  {CALENDAR_OPTIONS.map(([value, label, timezone]) => <option key={value} value={value}>{label} · {timezone}</option>)}
                </TextField>
              </Stack>
              {!composedOption && !rangeAccrual && !supertracker && <>
                <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                   <TextField label="Coupon payoff barrier (% initial)" type="number" value={couponBarrier} onChange={(event) => setCouponBarrier(event.target.value)} fullWidth disabled={couponBarrierFollowsAutocall} slotProps={{ ...floatedInput, htmlInput: { step: "any" } }} helperText={couponBarrierFollowsAutocall ? "Default: follows the autocall barrier in force at each coupon date." : "Explicit fixed coupon barrier; use only when the term sheet differs from the autocall barrier."} />
                   <TextField label="Autocall barrier start (% initial)" type="number" value={autocallBarrierStart} onChange={(event) => setAutocallBarrierStart(event.target.value)} fullWidth slotProps={{ ...floatedInput, htmlInput: { step: "any" } }} />
                   {stepDownControlsVisible && <TextField label="Autocall barrier step (percentage points)" type="number" value={autocallBarrierStep} onChange={(event) => setAutocallBarrierStep(event.target.value)} fullWidth slotProps={{ ...floatedInput, htmlInput: { step: "any" } }} helperText="Negative values create a step-down schedule; zero keeps the barrier flat." />}
                   {barrierFloorVisible && <Tooltip arrow placement="top" title="Lower bound for the step-down autocall schedule. Each autocall observation applies the configured step until the barrier reaches this floor; it does not alter the coupon or capital-protection barriers."><Box sx={{ width: "100%" }}><TextField label="Autocall barrier floor (% initial)" type="number" value={autocallBarrierFloor} onChange={(event) => setAutocallBarrierFloor(event.target.value)} fullWidth slotProps={{ ...floatedInput, htmlInput: { step: "any" } }} helperText="Lower bound applied when the step-down reaches it." /></Box></Tooltip>}
                   {maturityConsolationEnabled && <Tooltip arrow placement="top" title="Upper bound of the maturity consolation range. If final performance is at or above the KIP barrier and below this level, the consolation payout applies. It normally equals the last autocall barrier, but the term sheet may set it separately."><Box sx={{ width: "100%" }}><TextField label="Final payoff barrier (% initial)" type="number" value={finalPayoffBarrier} onChange={(event) => setFinalPayoffBarrier(event.target.value)} fullWidth slotProps={{ ...floatedInput, htmlInput: { step: "any" } }} helperText="Upper bound for the maturity consolation range." /></Box></Tooltip>}
                </Stack>
                <FormControlLabel control={<Switch checked={couponBarrierFollowsAutocall} onChange={(event) => setCouponBarrierFollowsAutocall(event.target.checked)} />} label="Coupon barrier follows autocall barrier (default)" />
              </>}
               {!rangeAccrual && <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ alignItems: { md: "center" } }}>
                 <FormControlLabel control={<Switch checked={includeKip} onChange={(event) => { const checked = event.target.checked; setIncludeKip(checked); if (!checked && maturityConsolationEnabled && !consolationLowerBarrier.trim()) setConsolationLowerBarrier(kipBarrier); }} />} label={composedOption ? "Include KIP component" : supertracker ? "Include KIP / downside component" : "Include maturity knock-in put / capital-protection component"} sx={{ minWidth: { md: 430 } }} />
                 {includeKip && <TextField label="Knock-in put barrier (% initial)" type="number" value={kipBarrier} onChange={(event) => setKipBarrier(event.target.value)} fullWidth slotProps={{ ...floatedInput, htmlInput: { step: "any" } }} helperText={composedOption || supertracker ? "A KIP is a separate barrier component. Choose whether the barrier is continuously monitored or checked only at maturity." : undefined} />}
                 {maturityConsolationEnabled && !includeKip && <TextField label="Consolation lower barrier (% initial)" type="number" value={consolationLowerBarrier} onChange={(event) => setConsolationLowerBarrier(event.target.value)} fullWidth slotProps={{ ...floatedInput, htmlInput: { step: "any", min: "0" } }} helperText="Independent lower bound for the maturity consolation range. It does not create a KIP or capital-protection payoff." />}
               </Stack>}
               {composedOption && includeKip && <TextField select label="KIP observation convention" value={kipObservationStyle} onChange={(event) => setKipObservationStyle(event.target.value as "CONTINUOUS" | "FINAL_ONLY")} fullWidth slotProps={nativeSelect} helperText="Continuous means the barrier can trigger during the life of the option; European / maturity only checks the underlying on the final valuation date."><option value="CONTINUOUS">Continuous / life-of-option</option><option value="FINAL_ONLY">European / maturity only</option></TextField>}
               {supertracker && includeKip && <TextField select label="KIP observation convention" value={kipObservationStyle} onChange={(event) => setKipObservationStyle(event.target.value as "CONTINUOUS" | "FINAL_ONLY")} fullWidth slotProps={nativeSelect} helperText="Continuous means the downside barrier can trigger during the life of the product; final-only checks it at maturity."><option value="CONTINUOUS">Continuous / life-of-option</option><option value="FINAL_ONLY">European / maturity only</option></TextField>}
              {maturityConsolationEnabled && <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ alignItems: { md: "center" } }}>
                <TextField label="Consolation rate (% of max payoff)" type="number" value={consolationRate} onChange={(event) => setConsolationRate(event.target.value)} fullWidth slotProps={{ ...floatedInput, htmlInput: { step: "any", min: "0", max: "100" } }} helperText="Paid when final performance is at/above the KIP barrier and below the final scheduled payoff barrier. This branch is enabled by the Autocall consolation subtype." />
              </Stack>}
            </Stack>
          </Card>

          {showSchedule && <Card sx={{ p: { xs: 2, md: 3 } }}>
            <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ alignItems: { md: "center" } }}>
              <Box sx={{ flex: 1 }}>
                <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>4 · CONTRACT EVENTS</Typography>
                <Typography variant="h6">Observation schedule</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{composedOption ? "The maturity preview separates each option payoff component from the KIP barrier component. Continuous KIP remains a condition group without a scheduled observation event." : rangeAccrual ? "The preview shows one range condition per coupon period. The detailed daily/weekly/monthly fixing convention is stored separately and evaluated by the lifecycle service." : supertracker ? "The maturity preview separates the leveraged call, optional cap call, optional KIP/downside component, and parent redemption action." : "Each observation is an event. Component rows describe contractual composition; parent actions are shown once and are never repeated per underlying."}</Typography>
              </Box>
              <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
                <Chip label={`${generated.observationDates.length} observations`} variant="outlined" />
                <Chip label={`${componentCount} components`} variant="outlined" />
                <Chip label={`${actionCount} parent actions`} color="primary" variant="outlined" />
              </Stack>
            </Stack>
            <Divider sx={{ my: 2 }} />
             {!!generated.warnings.length && <Stack spacing={1} sx={{ mb: 2 }}>{generated.warnings.map((warning) => <Alert severity="warning" key={warning}>{warning}</Alert>)}</Stack>}
             {!!generated.rows.length && <Alert severity="info" sx={{ mb: 2 }}>Payment dates shown here are provisional weekend-only previews. The governed calendar and holiday resolver will recalculate them during approval.</Alert>}
            {draftDirty && <Alert severity="info" sx={{ mb: 2 }}>Local schedule edits are marked and will be included in the submitted draft proposal.</Alert>}
            {baselineChanged && <Alert severity="warning" sx={{ mb: 2 }} action={<Button color="inherit" size="small" onClick={discardDraftChanges}>Discard manual changes</Button>}>High-level schedule inputs changed while this draft had manual edits. Review the current draft or discard it to use the regenerated baseline.</Alert>}
            {!!draftValidationIssues.length && <Alert severity="error" sx={{ mb: 2 }}>{draftValidationIssues.length} draft validation issue{draftValidationIssues.length === 1 ? "" : "s"} must be resolved before submission.</Alert>}
            {!generated.rows.length && !generated.warnings.length && <Alert severity="info">Add at least one underlying and generate the schedule.</Alert>}
            {!!generated.rows.length && <Stack spacing={2}>
              <Box>
                <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ alignItems: { md: "center" }, mb: 1 }}>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 800 }}>Observation overview</Typography>
                    <Typography variant="body2" color="text.secondary">Compare the schedule here; open one observation to inspect its underlying components and parent action.</Typography>
                  </Box>
                  <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
                    <Button size="small" variant={editSchedule ? "contained" : "outlined"} onClick={() => { setEditSchedule((current) => !current); setShowContractRows(true); }} sx={{ textTransform: "none" }}>
                      {editSchedule ? "Exit edit mode" : "Edit selected observation"}
                    </Button>
                    <Button size="small" variant="outlined" onClick={() => setShowAllObservations((current) => !current)} sx={{ textTransform: "none" }}>
                      {showAllObservations ? "Show one observation" : "Show all observations"}
                    </Button>
                    <Button size="small" variant={showContractRows ? "contained" : "text"} onClick={() => setShowContractRows((current) => !current)} sx={{ textTransform: "none" }}>
                      {showContractRows ? "Hide contractual rows" : "Show contractual rows"}
                    </Button>
                  </Stack>
                </Stack>
                <TableContainer sx={{ border: "1px solid", borderColor: "divider", borderRadius: 1.5, overflowX: "auto" }}>
                  <Table size="small" aria-label="Observation overview">
                    <TableHead><TableRow sx={{ bgcolor: "#f8fafc" }}>{["Observation", "Payment", "Scope", "Coupon", "Autocall", "Components", "Parent actions", ""].map((header) => <TableCell key={header} align={header === "Coupon" || header === "Autocall" || header === "Components" || header === "Parent actions" ? "right" : "left"} sx={{ fontWeight: 800, whiteSpace: "nowrap" }}>{header}</TableCell>)}</TableRow></TableHead>
                    <TableBody>{observationSummaries.map((summary) => {
                      const detailId = `observation-detail-${summary.observationDate}`;
                      const selected = selectedObservationDate === summary.observationDate && !showAllObservations;
                      return <TableRow key={summary.observationDate} hover selected={selected}>
                        <TableCell><Typography sx={{ fontWeight: 800 }}>{summary.observationDate}</Typography><Typography variant="caption" color="text.secondary">{summary.underlyingCount} underlying{summary.underlyingCount === 1 ? "" : "s"}</Typography></TableCell>
                        <TableCell>{summary.paymentDate}</TableCell>
                        <TableCell>{summary.conditionScope.replaceAll("_", " ")}</TableCell>
                        <TableCell align="right">{summary.couponBarrier === null ? "—" : `${formatNumber(summary.couponBarrier)}%`}</TableCell>
                        <TableCell align="right">{summary.autocallBarrier === null ? "—" : `${formatNumber(summary.autocallBarrier)}%`}</TableCell>
                        <TableCell align="right"><Chip size="small" label={summary.componentCount} variant="outlined" /></TableCell>
                        <TableCell align="right"><Chip size="small" label={summary.actionCount ? `${summary.actionCount} action${summary.actionCount === 1 ? "" : "s"}` : "—"} color={summary.actionCount ? "primary" : "default"} variant="outlined" /></TableCell>
                        <TableCell align="right"><Button size="small" onClick={() => { setSelectedObservationDate(summary.observationDate); setShowAllObservations(false); }} aria-expanded={showAllObservations || selected} aria-controls={detailId} sx={{ textTransform: "none", whiteSpace: "nowrap" }}>{selected ? "Selected" : "Open"}</Button></TableCell>
                      </TableRow>;
                    })}</TableBody>
                  </Table>
                </TableContainer>
              </Box>

              <Stack spacing={1.5}>
                {observationSummaries.filter((summary) => showAllObservations || summary.observationDate === selectedObservationDate).map((summary) => {
                  const rows = observationGroups.get(summary.observationDate) ?? [];
                  const components = rows.filter((row) => row.rowKind === "COMPONENT");
                  const actions = rows.filter((row) => row.rowKind === "ACTION");
                  const underlyingGroups = groupComponentsByUnderlying(components);
                  const detailId = `observation-detail-${summary.observationDate}`;
                  return <Card id={detailId} key={summary.observationDate} variant="outlined" sx={{ p: { xs: 1.5, md: 2 }, bgcolor: "#fbfdff", scrollMarginTop: 16 }}>
                    <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ alignItems: { md: "center" } }}>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>Observation {summary.observationDate}</Typography>
                        <Typography variant="body2" color="text.secondary">Payment {summary.paymentDate} · {summary.conditionScope.replaceAll("_", " ")} · coupon {summary.couponBarrier === null ? "—" : `${formatNumber(summary.couponBarrier)}%`} · autocall {summary.autocallBarrier === null ? "—" : `${formatNumber(summary.autocallBarrier)}%`}</Typography>
                      </Box>
                      <Chip label={`${summary.componentCount} component${summary.componentCount === 1 ? "" : "s"}`} size="small" variant="outlined" />
                      <Chip label={`${summary.actionCount} parent action${summary.actionCount === 1 ? "" : "s"}`} size="small" color={summary.actionCount ? "primary" : "default"} variant="outlined" />
                    </Stack>

                    <Box sx={{ mt: 2 }}>
                      <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 800 }}>Underlying components</Typography>
                      <TableContainer sx={{ mt: 0.5, border: "1px solid", borderColor: "divider", borderRadius: 1.5, overflowX: "auto" }}>
                        <Table size="small" aria-label={`Underlying components for ${summary.observationDate}`}>
                          <TableHead><TableRow sx={{ bgcolor: "#f8fafc" }}>{["Underlying", "Components", "Conditions", "Payoff terms", "Technical"].map((header) => <TableCell key={header} sx={{ fontWeight: 800, whiteSpace: "nowrap" }}>{header}</TableCell>)}</TableRow></TableHead>
                          <TableBody>{underlyingGroups.map((group) => <TableRow key={group.key} hover>
                            <TableCell sx={{ minWidth: 180 }}><Typography sx={{ fontWeight: 700 }}>{group.label}</Typography>{showTechnicalDetails && group.referenceNodeId && <Typography variant="caption" color="text.secondary" sx={{ display: "block", fontFamily: "monospace" }}>{group.referenceNodeId}</Typography>}</TableCell>
                            <TableCell sx={{ minWidth: 165 }}><Stack direction="row" spacing={0.5} sx={{ flexWrap: "wrap", gap: 0.5 }}>{group.rows.map((row) => <Chip key={row.rowId} size="small" label={row.conditionRole === "CAPITAL_PROTECTION" ? "Knock-in put" : row.componentKind === "DIGITAL" ? "Digital payoff" : `${row.optionType ?? "Option"} payoff`} variant="outlined" />)}</Stack></TableCell>
                            <TableCell sx={{ minWidth: 205 }}>{group.rows.map((row) => <Typography key={row.rowId} variant="body2">{conditionText(row)}</Typography>)}</TableCell>
                            <TableCell sx={{ minWidth: 180 }}>{group.rows.map((row) => <Typography key={row.rowId} variant="body2">{row.payoutRate !== null ? `${formatNumber(row.payoutRate)}% digital payout · ${formatAutocallLegSide(row.participation)}` : row.couponRate === null ? `${row.optionType ?? "Option"} · ${formatAutocallLegSide(row.participation)}` : `${formatNumber(row.couponRate)}% coupon · ${formatAutocallLegSide(row.participation)}`}</Typography>)}</TableCell>
                            <TableCell>{showTechnicalDetails ? <Stack spacing={0.25}>{group.rows.map((row) => <Typography key={row.rowId} variant="caption" sx={{ fontFamily: "monospace" }}>{row.rowId}</Typography>)}</Stack> : <Typography variant="caption" color="text.secondary">Hidden</Typography>}</TableCell>
                          </TableRow>)}</TableBody>
                        </Table>
                      </TableContainer>
                    </Box>

                    {showContractRows && <Box sx={{ mt: 2 }}>
                      <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 800 }}>Contractual component rows</Typography>
                      <TableContainer sx={{ mt: 0.5, border: "1px solid", borderColor: "divider", borderRadius: 1.5, overflowX: "auto" }}>
                        <Table size="small" aria-label={`Contractual rows for ${summary.observationDate}`}><TableHead><TableRow sx={{ bgcolor: "#f8fafc" }}>{["Reference", "Component", "Condition", "Strike", "Coupon", "Leg side", "Settlement date", "Outcome"].map((header) => <TableCell key={header} sx={{ fontWeight: 800, whiteSpace: "nowrap" }}>{header}</TableCell>)}</TableRow></TableHead>
                          <TableBody>{components.map((row) => <TableRow key={row.rowId} hover>
                            <TableCell sx={{ minWidth: 190 }}><Typography sx={{ fontWeight: 700 }}>{row.underlyingLabel}</Typography>{showTechnicalDetails && <Typography variant="caption" color="text.secondary" sx={{ display: "block", fontFamily: "monospace" }}>{row.underlyingReferenceNodeId}</Typography>}</TableCell>
                            <TableCell sx={{ whiteSpace: "nowrap" }}>{row.componentKind === "VANILLA_OPTION" ? `${row.optionType} · ${row.exerciseStyle}` : `${row.componentKind} · ${row.exerciseStyle}`}<Typography variant="caption" sx={{ display: "block" }} color="text.secondary">Leg {row.legId} · {row.groupLabel}</Typography></TableCell>
                            <TableCell sx={{ minWidth: 205 }}>{editSchedule && row.conditionRole !== "OPTION_PAYOFF" ? <Stack spacing={0.5}><Typography variant="caption" color="text.secondary">{row.conditionRole.replaceAll("_", " ")}</Typography><TextField size="small" type="number" value={row.conditionLevel ?? ""} onChange={(event) => updateDraftCell(row.draftRowId, "conditionLevel", event.target.value)} slotProps={{ ...floatedInput, htmlInput: { step: "any", min: "0", "aria-label": `Condition level for ${row.underlyingLabel}` } }} /></Stack> : conditionText(row)}<Typography variant="caption" sx={{ display: "block" }} color="text.secondary">{row.conditionLevelBasis}</Typography></TableCell>
                            <TableCell>{formatNumber(row.strikeValue)}<Typography variant="caption" sx={{ display: "block" }} color="text.secondary">{row.strikePercent === null ? "—" : `${formatNumber(row.strikePercent)}% initial`}</Typography></TableCell>
                            <TableCell>{row.couponRate === null ? "—" : editSchedule ? <TextField size="small" type="number" value={row.couponRate ?? ""} onChange={(event) => updateDraftCell(row.draftRowId, "couponRate", event.target.value)} slotProps={{ ...floatedInput, htmlInput: { step: "any", "aria-label": `Coupon rate for ${row.underlyingLabel}` } }} /> : `${formatNumber(row.couponRate)}%`}</TableCell>
                            <TableCell>{editSchedule ? <TextField select size="small" value={row.participation === null ? "" : row.participation < 0 ? "-1" : "1"} onChange={(event) => updateDraftCell(row.draftRowId, "participation", event.target.value)} slotProps={{ ...nativeSelect, htmlInput: { "aria-label": `Leg side for ${row.underlyingLabel}` } }}><option value="1">Long</option><option value="-1">Short</option></TextField> : formatAutocallLegSide(row.participation)}</TableCell>
                            <TableCell>{editSchedule ? <TextField size="small" type="date" value={row.paymentDate} onChange={(event) => updateDraftPaymentDate(row.draftRowId, event.target.value)} slotProps={{ ...nativeSelect, htmlInput: { "aria-label": `Settlement date for ${row.underlyingLabel}` } }} /> : row.paymentDate}</TableCell>
                            <TableCell><Chip size="small" label={`${row.actionCode} → ${row.actionTarget}`} variant="outlined" /></TableCell>
                          </TableRow>)}</TableBody>
                        </Table>
                      </TableContainer>
                    </Box>}

                    {!!actions.length && <Box sx={{ mt: 2 }}>
                      <Typography variant="overline" color="primary.main" sx={{ fontWeight: 800 }}>Parent actions</Typography>
                      <TableContainer sx={{ mt: 0.5, border: "1px solid", borderColor: "primary.100", borderRadius: 1.5, overflowX: "auto" }}>
                        <Table size="small" aria-label={`Parent actions for ${summary.observationDate}`}><TableHead><TableRow sx={{ bgcolor: "#eef4ff" }}>{["Action", "Trigger", "Scope", "Target", "Settlement date", "Execution"].map((header) => <TableCell key={header} sx={{ fontWeight: 800, whiteSpace: "nowrap" }}>{header}</TableCell>)}</TableRow></TableHead>
                          <TableBody>{actions.map((row) => <TableRow key={row.rowId} hover>
                            <TableCell><Chip size="small" color={row.actionCode === "PAY_CONSOLATION" ? "secondary" : "primary"} label={actionLabel(row.actionCode)} /></TableCell>
                            <TableCell>{editSchedule && row.conditionOperator !== "RANGE" ? <Stack spacing={0.5}><Typography variant="caption" color="text.secondary">{row.conditionRole.replaceAll("_", " ")}</Typography><TextField size="small" type="number" value={row.conditionLevel ?? ""} onChange={(event) => updateDraftCell(row.draftRowId, "conditionLevel", event.target.value)} slotProps={{ ...floatedInput, htmlInput: { step: "any", min: "0", "aria-label": `Condition level for parent action ${summary.observationDate}` } }} /></Stack> : conditionText(row)}{showTechnicalDetails && <Typography variant="caption" sx={{ display: "block" }} color="text.secondary">{row.rowId}</Typography>}</TableCell>
                            <TableCell>{row.conditionScope.replaceAll("_", " ")}</TableCell>
                            <TableCell>{row.actionTarget === "PARENT" ? "Parent product" : row.actionTarget}</TableCell>
                            <TableCell>{editSchedule ? <TextField size="small" type="date" value={row.paymentDate} onChange={(event) => updateDraftPaymentDate(row.draftRowId, event.target.value)} slotProps={{ ...nativeSelect, htmlInput: { "aria-label": `Settlement date for ${actionLabel(row.actionCode)}` } }} /> : row.paymentDate}</TableCell>
                            <TableCell>{row.actionCode === "PAY_CONSOLATION" ? `Pay ${formatNumber(row.payoutRate)}% of max payoff` : row.actionCode === "FINAL_REDEMPTION" ? "Principal redemption at maturity if not previously called" : "Once per condition group"}</TableCell>
                          </TableRow>)}</TableBody>
                        </Table>
                      </TableContainer>
                    </Box>}
                  </Card>;
                })}
              </Stack>
            </Stack>}
            <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ mt: 2 }}>
              <Button variant="outlined" onClick={() => setShowSchedule(false)}>Hide schedule</Button>
              <Button variant="contained" onClick={submitDraft} disabled={!canSubmit}>{submissionState === "submitting" ? "Submitting…" : submissionState === "submitted" ? "Proposal submitted" : "Submit draft proposal"}</Button>
              <Typography variant="caption" color="text.secondary" sx={{ alignSelf: "center" }}>Approval materializes the versioned terms graph; submission alone creates no approved security.</Typography>
            </Stack>
          </Card>}
        </Stack>
      </Box>
    </Box>
  );
}
