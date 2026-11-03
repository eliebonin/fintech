import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({error:'',items:[] as any[]}));
vi.mock('./use-interest-data',()=>({useInterestData:()=>({loading:false,error:h.error,data:{items:h.items,total:h.items.length}})}));
import {BalanceTradeTimeline,tradeMarkerGroups,validTradeEvents} from './balance-trade-timeline';
const event=(id:string,side:'BUY'|'SELL'='BUY')=>({tradeId:id,instrumentId:'bond',balanceDate:'2026-10-01',executionDatetime:'2026-09-30T10:00:00Z',settlementDate:'2026-10-02',
 side,signedQuantity:side==='BUY'?'1000000.123456789012':'-1000000',quantityUnit:'NOMINAL',tradeAccruedAmount:side==='BUY'?'1234.5':'-1234.5',currency:'GBP',counterparty:'Example bank',tradeType:'INVESTMENT'});
it('groups same-day same-side events without netting buys and sells or rounding quantities',()=>{
 const groups=tradeMarkerGroups([event('buy-2'),event('sell','SELL'),event('buy-1')],'2026-10-01','2026-10-20');
 expect(groups).toHaveLength(2);expect(groups[0].items).toHaveLength(2);expect(groups[1].items).toHaveLength(1);
 expect(groups[0].items[0].signedQuantity).toBe('1000000.123456789012');expect(groups[0].x).toBe(groups[1].x);
});
it('defaults Show trades on and provides labelled keyboard-selectable markers',()=>{
 h.error='';h.items=[event('buy-1'),event('buy-2'),event('sell','SELL')];
 const html=renderToStaticMarkup(<BalanceTradeTimeline strategyId="strategy" instrumentId="bond" from="2026-10-01" to="2026-10-20"/>);
 expect(html).toContain('Show trades');expect(html).toContain('checked=""');
 expect(html).toContain('2 buys');expect(html).toContain('1 sell');expect(html).toContain('role="button"');expect(html).toContain('tabindex="0"');
 expect(html).toContain('balance-impact date');expect(html).toContain('Example bank');
});
it('distinguishes failed trade access from no events and leaves the financial report separate',()=>{
 h.error='Trade details unavailable';h.items=[];
 const html=renderToStaticMarkup(<BalanceTradeTimeline strategyId="strategy" instrumentId="bond" from="2026-10-01" to="2026-10-20"/>);
 expect(html).toContain('Trade details unavailable');expect(html).not.toContain('No trades in this range');
 h.error='';
});
it('rejects partial, wrong-scope, duplicate and rounded trade responses',()=>{
 const scope={strategyId:'strategy',instrumentId:'bond',from:'2026-10-01',to:'2026-10-20'};
 const data={strategyId:'strategy',instrumentId:'bond',fromDate:scope.from,toDate:scope.to,items:[event('trade')],total:1};
 expect(validTradeEvents(data,scope)).toBe(true);
 for(const invalid of [{...data,total:2},{...data,strategyId:'other'},{...data,items:[event('trade'),event('trade')],total:2},
  {...data,items:[{...event('trade'),signedQuantity:1000000}]},{...data,items:[{...event('trade'),balanceDate:'2026-09-30'}]}])
  expect(validTradeEvents(invalid,scope)).toBe(false);
});
