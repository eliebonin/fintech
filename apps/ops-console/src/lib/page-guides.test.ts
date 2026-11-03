import {expect,it} from 'vitest';
import {getPageGuide} from './page-guides';

it.each([
 ['/trades/new','Book a trade'],['/trades/lifecycle','Bond schedules and maturity processing'],['/trades/saved-trade','Trade history and corrections'],
 ['/strategies/new','Strategies'],['/strategies/saved-strategy','Strategy workspace'],
 ['/instruments/autocalls/new','Structured-product creation'],['/instruments/futures/new','Futures contract creation'],
 ['/instruments/future-families','Futures families'],['/instruments/options/new','Option creation'],
 ['/instruments/parent/listings/new','Create a listing'],['/instruments/listings/new','Create a listing'],
 ['/instruments/parent/booking-conventions','Booking conventions and schedules'],
 ['/reference-data/review/proposal','Reference review and operations'],['/instruments/crypto/review/proposal','Reference review and operations'],
 ['/market-data/policies/?view=preview','Pricing policies'],['/market-data/resolution-snapshots/snapshot','Market-data coverage and evidence'],
 ['/valuation/cash-balances','Cash balances'],['/tenant-profile/access','Users, groups and strategy access'],
 ['/valuation/interest/explorer?strategyId=example','Explore accrued balances'],
])('selects the specific guide rather than a generic detail: %s',(path,title)=>{
 expect(getPageGuide(path)?.title).toBe(title);
});

it.each(['/not-a-workflow','/instruments/not-supported/new','/instruments/constructor/new','/instruments/toString/new','/instruments/parent/unrelated','/api/valuation'])('omits guidance for unknown/unsupported paths: %s',path=>{
 expect(getPageGuide(path)).toBeUndefined();
});
