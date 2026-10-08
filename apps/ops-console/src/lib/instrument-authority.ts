/** UI affordances mirror API stewardship; the API remains authoritative. */
export function canManageInstruments(workspace:{membershipRole:string;moduleCodes:readonly string[]}):boolean {
  return workspace.membershipRole==='TENANT_ADMIN'&&workspace.moduleCodes.includes('SECURITY_MASTER');
}

export function canBookTrades(workspace:{membershipRole:string;moduleCodes:readonly string[]}):boolean {
  return workspace.membershipRole==='TENANT_ADMIN'&&workspace.moduleCodes.includes('TRADING');
}

/** A UI guard only: upstream authorization is checked again for every write. */
export function writePageRequirement(path:string):'SECURITY_MASTER'|'TRADING'|undefined {
  if(path==='/trades/new')return 'TRADING';
  if(path==='/instruments/create'||path==='/instruments/future-families'
      || /^\/instruments\/(?:[^/]+\/)*new\/?$/.test(path)
      || /^\/instruments\/[^/]+\/booking-conventions\/?$/.test(path))return 'SECURITY_MASTER';
}
