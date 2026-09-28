export type IndexFamilyValidationErrors = {
  canonicalName?: string;
};

export function validateIndexFamily(canonicalName: string, _internalCode: string): IndexFamilyValidationErrors {
  if (!canonicalName.trim()) {
    return { canonicalName: "Canonical family name is required." };
  }
  return {};
}
