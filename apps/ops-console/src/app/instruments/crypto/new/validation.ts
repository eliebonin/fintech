export function validateCryptoAssetIdentity(canonicalName: string, assetSubtype: string, nativeSymbol: string): {
  canonicalName?: string;
  assetSubtype?: string;
  nativeSymbol?: string;
} {
  const errors: { canonicalName?: string; assetSubtype?: string; nativeSymbol?: string } = {};
  if (!canonicalName.trim()) errors.canonicalName = "Canonical name is required.";
  if (!assetSubtype) errors.assetSubtype = "Choose a cryptoasset subtype.";
  if (!nativeSymbol.trim()) errors.nativeSymbol = "Native symbol is required.";
  return errors;
}
