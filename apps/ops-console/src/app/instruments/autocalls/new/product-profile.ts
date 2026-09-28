import type { AutocallProductSubtype } from "./payload";

export type CouponMemoryMode = "NONE" | "CONDITIONAL_CATCH_UP" | "ACCUMULATE_TO_REDEMPTION";

export type StructuredProductUiProfile = {
  autocallBarrierStep: string;
  constantAutocallBarrier: boolean;
  helperText: string;
};

export function showsMaturityConsolationControls(productType: AutocallProductSubtype): boolean {
  return productType === "AUTOCALL_CONSOLATION";
}

export function isComposedOptionSubtype(productType: AutocallProductSubtype): boolean {
  return productType === "VANILLA_SPREAD_KIP" || productType === "VANILLA_KIP" || productType === "DIGITAL_KIP";
}

export function isRangeAccrualSubtype(productType: AutocallProductSubtype): boolean {
  return productType === "RANGE_ACCRUAL";
}

export function isSupertrackerSubtype(productType: AutocallProductSubtype): boolean {
  return productType === "SUPERTRACKER";
}

export function isMaturityOnlySubtype(productType: AutocallProductSubtype): boolean {
  return isComposedOptionSubtype(productType) || isSupertrackerSubtype(productType);
}

export function showsAutocallStepDownControls(productType: AutocallProductSubtype): boolean {
  return productType !== "ATHENA" && !isComposedOptionSubtype(productType) && !isRangeAccrualSubtype(productType) && !isSupertrackerSubtype(productType);
}

export function showsAutocallBarrierFloor(productType: AutocallProductSubtype, step: string | number): boolean {
  const numericStep = typeof step === "number" ? step : Number(step);
  return showsAutocallStepDownControls(productType) && Number.isFinite(numericStep) && numericStep !== 0;
}

/**
 * UI conventions for the shared structured-product builder.
 *
 * These defaults do not create a second product model: the submitted draft
 * still contains the ordinary barrier, schedule, and coupon-programme fields.
 * They only make commonly used product conventions visible and safer to enter.
 */
export function productUiProfile(productType: AutocallProductSubtype): StructuredProductUiProfile {
  if (productType === "ATHENA") {
    return {
      autocallBarrierStep: "0",
      constantAutocallBarrier: true,
      helperText: "Athena convention: the autocall barrier stays constant across observations.",
    };
  }

  if (productType === "PHOENIX") {
    return {
      autocallBarrierStep: "-10",
      constantAutocallBarrier: false,
      helperText: "Phoenix convention: conditional coupons can be paid while the product continues. Memory is common, but the term sheet decides whether missed coupons catch up.",
    };
  }

  if (productType === "AUTOCALL_CONSOLATION") {
    return {
      autocallBarrierStep: "-10",
      constantAutocallBarrier: false,
      helperText: "Consolation adds a bounded maturity action; the ordinary autocall schedule remains configurable.",
    };
  }

  if (productType === "VANILLA_SPREAD_KIP") {
    return {
      autocallBarrierStep: "0",
      constantAutocallBarrier: true,
      helperText: "Vanilla spread with KIP: two signed vanilla option legs plus a separate maturity knock-in put component.",
    };
  }

  if (productType === "VANILLA_KIP") {
    return {
      autocallBarrierStep: "0",
      constantAutocallBarrier: true,
      helperText: "Vanilla with KIP: one vanilla option payoff plus a separate maturity knock-in put component.",
    };
  }

  if (productType === "DIGITAL_KIP") {
    return {
      autocallBarrierStep: "0",
      constantAutocallBarrier: true,
      helperText: "Digital with KIP: one digital payout component plus a separate maturity knock-in put component.",
    };
  }

  if (productType === "RANGE_ACCRUAL") {
    return {
      autocallBarrierStep: "0",
      constantAutocallBarrier: true,
      helperText: "Range accrual: a periodic coupon is multiplied by the fraction of observations inside the stated lower and upper range.",
    };
  }

  if (productType === "SUPERTRACKER") {
    return {
      autocallBarrierStep: "0",
      constantAutocallBarrier: true,
      helperText: "Supertracker: maturity principal plus leveraged upside, optionally capped by a short call and protected by a separate KIP/downside component.",
    };
  }

  return {
    autocallBarrierStep: "-10",
    constantAutocallBarrier: false,
    helperText: "Standard autocall: the barrier can be flat or stepped down by observation.",
  };
}
