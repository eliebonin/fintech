import {expect,it} from 'vitest';
import {isCashBookingListing} from './cash-booking-listing';
it('excludes derivatives requiring their own ticket',()=>{for(const instrumentType of ['OPTION','FX_FORWARD','FUTURE','SWAP'])expect(isCashBookingListing({status:'ACTIVE',isTradable:true,instrumentType})).toBe(false);});
it('retains active cash instruments but not inactive or nontradable listings',()=>{expect(isCashBookingListing({status:'ACTIVE',isTradable:true,instrumentType:'EQUITY'})).toBe(true);expect(isCashBookingListing({status:'INACTIVE',isTradable:true,instrumentType:'EQUITY'})).toBe(false);expect(isCashBookingListing({status:'ACTIVE',isTradable:false,instrumentType:'EQUITY'})).toBe(false);});
it('refuses unknown types and unsupported products rather than defaulting to cash',()=>{
  for(const instrumentType of [undefined,null,'','NEW_PRODUCT','FORWARD','WARRANT','CONVERTIBLE_BOND','REPO'])
    expect(isCashBookingListing({status:'ACTIVE',isTradable:true,instrumentType})).toBe(false);
});
it('retains the supported cash security and unit types',()=>{
  for(const instrumentType of ['ETF','ETC','ETN','ETV','ETI','DIGITAL_ASSET','FUND','FUND_SHARE_CLASS','EXCHANGE_TRADED_VEHICLE','EXCHANGE_TRADED_CERTIFICATE'])
    expect(isCashBookingListing({status:'ACTIVE',isTradable:true,instrumentType})).toBe(true);
});
