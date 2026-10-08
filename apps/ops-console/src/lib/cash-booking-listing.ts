/** Mirror the cash writer's product boundary; server validation remains authoritative. */
const cashTypes = new Set(['EQUITY','ETF','ETC','ETN','ETV','ETI','DIGITAL_ASSET','FUND','FUND_SHARE_CLASS','EXCHANGE_TRADED_VEHICLE','EXCHANGE_TRADED_CERTIFICATE']);
export function isCashBookingListing(candidate:{status:string;isTradable:boolean;instrumentType?:string|null}) {
  return candidate.status === 'ACTIVE' && candidate.isTradable && cashTypes.has(candidate.instrumentType ?? '');
}
