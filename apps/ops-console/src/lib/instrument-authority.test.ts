import {describe,expect,it} from 'vitest';
import {canManageInstruments} from './instrument-authority';
describe('instrument stewardship',()=>{
  it('does not require TRADING',()=>expect(canManageInstruments({membershipRole:'TENANT_ADMIN',moduleCodes:['SECURITY_MASTER']})).toBe(true));
  it('does not substitute TRADING for SECURITY_MASTER',()=>expect(canManageInstruments({membershipRole:'TENANT_ADMIN',moduleCodes:['TRADING']})).toBe(false));
  it('requires the admin role',()=>expect(canManageInstruments({membershipRole:'READ_ONLY',moduleCodes:['SECURITY_MASTER']})).toBe(false));
});
