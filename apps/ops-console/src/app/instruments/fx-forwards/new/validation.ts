export type FxForwardIdentityErrors = {
  canonicalName?: string;
  baseCurrencyId?: string;
  quoteCurrencyId?: string;
  quoteConvention?: string;
  agreedForwardRate?: string;
  maturityDate?: string;
};

export function validateFxForwardIdentity(
  canonicalName: string,
  baseCurrencyId: string,
  quoteCurrencyId: string,
  quoteConvention: string,
  agreedForwardRate: string,
  maturityDate: string,
): FxForwardIdentityErrors {
  const errors: FxForwardIdentityErrors = {};
  if (!canonicalName.trim()) errors.canonicalName = "Enter a canonical name.";
  if (!baseCurrencyId) errors.baseCurrencyId = "Choose a base currency.";
  if (!quoteCurrencyId) errors.quoteCurrencyId = "Choose a quote currency.";
  if (baseCurrencyId && quoteCurrencyId && baseCurrencyId === quoteCurrencyId) {
    errors.quoteCurrencyId = "Base and quote currencies must be different.";
  }
  if (!quoteConvention.trim()) errors.quoteConvention = "Enter a quote convention, for example USD_PER_GBP.";
  else if (!/^[A-Z0-9_]+$/.test(quoteConvention.trim())) errors.quoteConvention = "Use uppercase letters, numbers, and underscores only.";
  const rate = Number(agreedForwardRate);
  if (!agreedForwardRate.trim() || !Number.isFinite(rate) || rate <= 0) errors.agreedForwardRate = "Enter a positive agreed forward rate.";
  if (!maturityDate) errors.maturityDate = "Choose the maturity date.";
  return errors;
}
