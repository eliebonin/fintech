/** UI affordances mirror API stewardship; the API remains authoritative. */
type AccessWorkspace={membershipRole:string;moduleCodes:readonly string[];permissionCodes?:readonly string[]};
export function canManageInstruments(workspace:AccessWorkspace):boolean {
  return workspace.moduleCodes.includes('SECURITY_MASTER')&&(workspace.permissionCodes
    ?workspace.permissionCodes.includes('REFERENCE_PROPOSE'):workspace.membershipRole==='TENANT_ADMIN');
}

export function canBookTrades(workspace:AccessWorkspace):boolean {
  return workspace.moduleCodes.includes('TRADING')&&(workspace.permissionCodes
    ?workspace.permissionCodes.includes('TRADE_WRITE'):workspace.membershipRole==='TENANT_ADMIN');
}

/** A UI guard only: upstream authorization is checked again for every write. */
export function writePageRequirement(path:string):'SECURITY_MASTER'|'TRADING'|undefined {
  if(path==='/trades/new')return 'TRADING';
  if(path==='/instruments/create'||path==='/instruments/future-families'
      || /^\/instruments\/(?:[^/]+\/)*new\/?$/.test(path)
      || /^\/instruments\/[^/]+\/booking-conventions\/?$/.test(path))return 'SECURITY_MASTER';
}
