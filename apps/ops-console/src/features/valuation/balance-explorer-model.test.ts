import {expect,it} from 'vitest';
import {validBalanceSeries} from './balance-explorer-model';
const scope={instrument:'bond',from:'2026-10-01',to:'2026-10-20'};
const row={history_id:'history',instrument_id:'bond',instrument_name:'Example bond',currency_code:'GBP',value_date:'2026-10-20',
 opening_balance:'999.123456789012',daily_earned:'1',trade_movements:'0',coupon_paid:'0',closing_balance:'1000.123456789012',basis:'DERIVED',source_status:'CURRENT',evidence:{}};
it('accepts an exact complete series and an empty window',()=>{
 expect(validBalanceSeries({items:[row],total:1},scope)).toBe(true);
 expect(validBalanceSeries({items:[],total:0},scope)).toBe(true);
});
it('rejects truncation, wrong instruments, out-of-window days, duplicate rows and float amounts',()=>{
 for(const result of [{items:[row],total:2},{items:[{...row,instrument_id:'other'}],total:1},
  {items:[{...row,value_date:'2026-09-30'}],total:1},{items:[row,row],total:2},
  {items:[{...row,closing_balance:1000.1}],total:1},{items:[{...row,value_date:'2026-02-30'}],total:1}])
  expect(validBalanceSeries(result,scope)).toBe(false);
});
