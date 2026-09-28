export type IndexIdentityErrors = {
  canonicalName?: string;
  indexKind?: string;
};

const CANONICAL_NAME_REQUIRED = "Enter the official name of the concrete index variant, for example S&P 500 Net Total Return.";
const INDEX_KIND_REQUIRED = "Choose the index kind so Operations can apply the correct onboarding semantics.";

export function validateIndexIdentity(canonicalName: string, indexKind: string): IndexIdentityErrors {
  return {
    ...(canonicalName.trim() ? {} : { canonicalName: CANONICAL_NAME_REQUIRED }),
    ...(indexKind.trim() ? {} : { indexKind: INDEX_KIND_REQUIRED }),
  };
}
