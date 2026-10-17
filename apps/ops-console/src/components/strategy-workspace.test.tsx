import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {StrategyPositions,StrategyCalendars,StrategyNavigation} from './strategy-workspace';
import {StrategyConsole} from '@/app/strategies/strategy-console';

const strategy={strategyId:'s',strategyCode:'FUND_A',displayName:'Fund A',strategyType:'FUND',baseCurrencyCode:'GBP',status:'ACTIVE'};
const query=new URLSearchParams('view=positions&asOf=2026-09-30');
it('shows saved contract dates and explicit attention text without changing quantity',()=>{
 const row={positionId:'p',subjectId:'subject',instrumentId:'i',name:'Matured bond',instrumentType:'BOND',instrumentTypeLabel:'Bonds',currency:'GBP',quantity:'-20',quantityUnit:'NOMINAL',direction:'SHORT',tradeCount:3,unitMultiplier:'1',quoteFactor:'100',contractDate:'2026-09-29',contractDateLabel:'Maturity',attentionCode:'PAST_CONTRACT_DATE',attentionMessage:'Past maturity — position still open'};
 const html=renderToStaticMarkup(<StrategyPositions strategyId="s" query={query} data={{asOf:'2026-09-30',basis:'EXECUTED',informationCutoff:'2026-10-15T10:00:00Z',total:1,limit:25,offset:0,items:[row]}}/>);
 expect(html).toContain('Maturity / expiry');expect(html).toContain('2026-09-29');expect(html).toContain('Past maturity — position still open');expect(html).toContain('-20');expect(html).toContain('position=p');
});
it('groups positions by type and hides opaque subject IDs without losing drill-down',()=>{
 const row={positionId:'p',subjectId:'opaque-subject-uuid',instrumentId:'i',name:'Alpha equity',instrumentType:'EQUITY',instrumentTypeLabel:'Equities',currency:'GBP',quantity:'20',quantityUnit:'SHARES',direction:'LONG',tradeCount:3,unitMultiplier:'1',quoteFactor:'1'};
 const html=renderToStaticMarkup(<StrategyPositions strategyId="s" query={query} data={{asOf:'2026-09-30',basis:'EXECUTED',informationCutoff:'2026-10-15T10:00:00Z',total:3,limit:25,offset:0,items:[row,{...row,positionId:'p2',name:'Zebra equity'},{...row,positionId:'p3',name:'A swap',instrumentType:'SWAP',instrumentTypeLabel:'Swaps',quantityUnit:'UNITS'}]}}/>);
 expect(html).toContain('scope="rowgroup"');expect(html).toContain('Equities');expect(html).toContain('Swaps');
 expect(html.indexOf('Equities')).toBeLessThan(html.indexOf('Alpha equity'));expect(html.indexOf('Zebra equity')).toBeLessThan(html.indexOf('Swaps'));
 expect(html).not.toContain('opaque-subject-uuid');expect(html).toContain('/instruments/i');expect(html).toContain('position=p');expect(html).toContain('20');
});
it('uses a register with detail links and a separate permitted creation action',()=>{
 const html=renderToStaticMarkup(<StrategyConsole initialStrategies={[strategy]} canWrite/>);
 expect(html).toContain('/strategies/s');expect(html).toContain('/strategies/new');expect(html).not.toContain('name="strategyCode"');
 expect(renderToStaticMarkup(<StrategyConsole initialStrategies={[strategy]} canWrite={false}/>)).not.toContain('/strategies/new');
});
it('separates strategy navigation and keeps trade history scoped to its code',()=>{
 const html=renderToStaticMarkup(<StrategyNavigation strategy={strategy} view="positions" query={query}/>);
 expect(html).toContain('Overview');expect(html).toContain('Positions');expect(html).toContain('Calendars');expect(html).toContain('portfolioCode=FUND_A');
});
it('displays short/residual units with linked drill-down and no financial values',()=>{
 const html=renderToStaticMarkup(<StrategyPositions strategyId="s" query={query} data={{asOf:'2026-09-30',basis:'EXECUTED',informationCutoff:'2026-10-15T10:00:00Z',total:1,limit:25,offset:0,items:[{positionId:'p',subjectId:'n',instrumentId:'i',name:'Example contract',currency:'GBP',quantity:'-20',quantityUnit:'CONTRACTS',direction:'SHORT',tradeCount:3,unitMultiplier:'50',quoteFactor:'1'}]}}/>);
 expect(html).toContain('SHORT');expect(html).toContain('-20');expect(html).toContain('CONTRACTS');expect(html).toContain('position=p');expect(html).toContain('informationCutoff=');expect(html).not.toContain('Market value');
});
it('does not disguise unavailable holdings as an empty book',()=>{
 const html=renderToStaticMarkup(<StrategyPositions strategyId="s" query={query} error="Trade-read access is required."/>);
 expect(html).toContain('Trade-read access is required.');expect(html).not.toContain('No open positions');
});
it('renders the full-history chart beneath the paginated movement table',()=>{
 const html=renderToStaticMarkup(<StrategyPositions strategyId="s" query={query} movements={{asOf:'2026-09-30',basis:'EXECUTED',informationCutoff:'2026-10-15T10:00:00Z',total:2,closingQuantity:'30',limit:1,offset:0,items:[{movementId:'m',tradeId:'t',kind:'INVESTMENT',effectiveAt:'2026-09-01T10:00:00Z',quantity:'100',runningQuantity:'100',executionPrice:'1',source:'BOOKED_TRADE'}],chart:{quantityUnit:'SHARES',through:'2026-09-30T23:59:59Z',points:[{effectiveAt:'2026-09-01T10:00:00Z',buyQuantity:'100',sellQuantity:'0',runningQuantity:'100',tradeCount:1,splitQuantity:'0',splitRatios:[]},{effectiveAt:'2026-09-02T10:00:00Z',buyQuantity:'0',sellQuantity:'-70',runningQuantity:'30',tradeCount:1,splitQuantity:'0',splitRatios:[]}]}}}/>);
 expect(html).toContain('Sell quantity: -70');
 expect(html.indexOf('Position history')).toBeGreaterThan(html.indexOf('Movement pages'));
});
it('distinguishes direct calendar assignments from available policy references',()=>{
 const html=renderToStaticMarkup(<StrategyCalendars data={{asOf:'2026-09-30',assignments:[],indirectCalendars:[]}}/>);
 expect(html).toContain('No calendars are directly assigned');expect(html).toContain('Indirect calendar references');expect(html).toContain('not automatically the strategy');
});
it('explains composite closure rules and shows the source instead of an opaque calendar identifier',()=>{
 const html=renderToStaticMarkup(<StrategyCalendars data={{asOf:'2026-09-30',assignments:[{assignment:{assignmentId:'a',purpose:'VALUATION',validFrom:'2026-01-01',validTo:'2026-12-31',reason:'Administrator rule'},activeOnDate:true,statusOnDate:'OPEN',calendar:{calendarId:'c',calendarCode:'FUND',displayName:'Fund calendar',purpose:'VALUATION',timezoneName:'Europe/Dublin',versionNo:1,coverageFrom:'2026-01-01',coverageTo:'2026-12-31',configuration:{mode:'ALL_OPEN',sourceReference:'Fund administrator notice',baseCalendarIds:['uk','us']},components:[{calendarId:'uk',displayName:'UK calendar'},{calendarId:'us',displayName:'US calendar'}]}}],indirectCalendars:[]}}/>);
 expect(html).toContain('Open only when every component is open');expect(html).toContain('UK calendar');expect(html).toContain('Fund administrator notice');
});
