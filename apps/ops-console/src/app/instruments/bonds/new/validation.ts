export type BondIdentityErrors = {
  canonicalName?: string;
  couponType?: string;
};

export function validateBondIdentity(canonicalName: string, couponType: string): BondIdentityErrors {
  return {
    ...(canonicalName.trim() ? {} : { canonicalName: "Enter the bond's official name." }),
    ...(couponType ? {} : { couponType: "Select fixed-rate, zero-coupon, or floating-rate." }),
  };
}
