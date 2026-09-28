export type EquityIdentityErrors = {
  canonicalName?: string;
};

const CANONICAL_NAME_REQUIRED = "Enter the official name of the economic security, for example Acme plc Ordinary Shares.";

export function validateEquityIdentity(canonicalName: string, _internalCode: string): EquityIdentityErrors {
  return canonicalName.trim() ? {} : { canonicalName: CANONICAL_NAME_REQUIRED };
}
