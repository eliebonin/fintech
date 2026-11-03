import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {beforeEach,expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({series:null as any,error:'',loading:false}));
vi.mock('./use-interest-data',()=>({useInterestData:(path:string|null)=>path?.startsWith('interest-options')?
 {data:{bonds:[{id:'bond',label:'Example bond',currency:'GBP',currencyId:'gbp'}],currencies:[],canWrite:false,strategyLabel:'Readable strategy'},loading:false,error:''}:
 path?.startsWith('balance-trades')?{data:{items:[],total:0},loading:false,error:''}:{data:h.series,loading:h.loading,error:h.error}}));
import {BalanceExplorer} from './balance-explorer';
const props={initialStrategy:'strategy',initialInstrument:'bond',initialFrom:'2026-08-01',initialTo:'2026-09-04'};
beforeEach(()=>{h.series={items:Array.from({length:35},(_,n)=>({history_id:String(n),instrument_id:'bond',instrument_name:'Example bond',currency_code:'GBP',value_date:new Date(Date.UTC(2026,7,n+1)).toISOString().slice(0,10),
 opening_balance:'1000',daily_earned:'10',trade_movements:'0',coupon_paid:'0',closing_balance:'1010.123456789012',basis:'DERIVED',source_status:'CURRENT',evidence:{}})),total:35};h.error='';h.loading=false;});
it('puts the full chart above a paginated exact table, with independent read-only filters',()=>{
 const html=renderToStaticMarkup(<BalanceExplorer {...props}/>);
 expect(html).toContain('From date');expect(html).toContain('To date');expect(html).toContain('Show history');
 expect(html).toContain('Readable strategy');expect(html).toContain('Example bond');expect(html).toContain('35 stored datapoints');
 expect(html.indexOf('<svg')).toBeLessThan(html.indexOf('<table'));
 expect(html).toContain('1–25 of 35');expect(html).toContain('1,010.123456789012');expect(html).toContain('value="all"');
 expect(html).not.toContain('Validate all');expect(html).not.toContain('Save &amp; check');
});
it('does not render stale chart data during loading or after a failed scope request',()=>{
 h.loading=true;let html=renderToStaticMarkup(<BalanceExplorer {...props}/>);
 expect(html).toContain('Loading the full balance history');expect(html).not.toContain('<svg');
 h.loading=false;h.error='Access denied';html=renderToStaticMarkup(<BalanceExplorer {...props}/>);
 expect(html).toContain('Access denied');expect(html).not.toContain('<svg');
});
it('invites instrument selection without requiring a validated daily review',()=>{
 const html=renderToStaticMarkup(<BalanceExplorer {...props} initialInstrument=""/>);
 expect(html).toContain('Choose a strategy, instrument and date range');expect(html).not.toContain('<svg');
});
