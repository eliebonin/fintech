import {describe,expect,it} from 'vitest';
import {canManageInstruments,canBookTrades} from './instrument-authority';
describe('instrument stewardship',()=>{
  it('does not require TRADING',()=>expect(canManageInstruments({membershipRole:'TENANT_ADMIN',moduleCodes:['SECURITY_MASTER']})).toBe(true));
  it('does not substitute TRADING for SECURITY_MASTER',()=>expect(canManageInstruments({membershipRole:'TENANT_ADMIN',moduleCodes:['TRADING']})).toBe(false));
  it('requires the admin role',()=>expect(canManageInstruments({membershipRole:'READ_ONLY',moduleCodes:['SECURITY_MASTER']})).toBe(false));
});
// Group permissions, rather than group labels, control booking affordances.
it('allows a permitted trader without elevating them to tenant administrator',()=>{
 expect(canBookTrades({membershipRole:'MEMBER',moduleCodes:['TRADING'],permissionCodes:['TRADE_WRITE']})).toBe(true);
 expect(canManageInstruments({membershipRole:'MEMBER',moduleCodes:['SECURITY_MASTER'],permissionCodes:['REFERENCE_READ']})).toBe(false);
});
