/** Mirror the cash writer's product boundary; server validation remains authoritative. */
export function isCashBookingListing(candidate:{status:string;isTradable:boolean;instrumentType?:string|null}) {
  return candidate.status === 'ACTIVE' && candidate.isTradable && !['OPTION','FX_FORWARD','FUTURE','SWAP','STRUCTURED_PRODUCT', 'BOND'].includes(candidate.instrumentType ?? '');
}
