/** Yahoo provenance wording follows the stored observation basis, never source name alone. */
export function describeSeriesBasis(bases:string[]):string{
 const descriptions=[...new Set(bases)].map(basis=>basis==='RAW'?'Reconstructed unadjusted (RAW) prices use retained split-reversal evidence; this is not an exchange-certified raw tape.'
 :basis==='SPLIT_ADJUSTED'?'Close is split-adjusted to the provider’s share basis; inspect split coverage before valuation.'
 :basis==='VENDOR_ADJUSTED'?'Adjusted close includes provider split and distribution adjustments; it is not an unadjusted execution price.'
 :`Stored basis ${basis}: inspect its source evidence.`);
 return descriptions.join(' ')||'Inspect observations and source evidence to establish the stored price basis.';
}
