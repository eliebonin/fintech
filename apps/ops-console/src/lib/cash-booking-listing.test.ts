import {expect,it} from 'vitest';
import {isCashBookingListing} from './cash-booking-listing';
it('excludes derivatives requiring their own ticket',()=>{for(const instrumentType of ['OPTION','FX_FORWARD','FUTURE','SWAP'])expect(isCashBookingListing({status:'ACTIVE',isTradable:true,instrumentType})).toBe(false);});
it('retains active cash instruments but not inactive or nontradable listings',()=>{expect(isCashBookingListing({status:'ACTIVE',isTradable:true,instrumentType:'EQUITY'})).toBe(true);expect(isCashBookingListing({status:'INACTIVE',isTradable:true,instrumentType:'EQUITY'})).toBe(false);expect(isCashBookingListing({status:'ACTIVE',isTradable:false,instrumentType:'EQUITY'})).toBe(false);});
