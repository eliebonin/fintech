import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {BalanceSeriesReport,BalanceHistoryViewer} from './balance-history-chart';
import type {BalanceHistoryRow} from './interest-types';
const rows:BalanceHistoryRow[]=Array.from({length:35},(_,i)=>({history_id:String(i),instrument_id:'bond',instrument_name:'Example Treasury',currency_code:'USD',value_date:new Date(Date.UTC(2026,7,i+1)).toISOString().slice(0,10),
 opening_balance:'1000000',daily_earned:'20',trade_movements:'0',coupon_paid:'0',closing_balance:i===1?null:'1000000.123456789012',basis:'DERIVED',source_status:i===2?'STALE':'CURRENT',evidence:{}}));

it('shows the full chart above an exact table defaulting to 25 datapoints',()=>{
 const html=renderToStaticMarkup(<BalanceSeriesReport rows={rows} from="2026-08-01" to="2026-09-04" currency="USD"/>);
 expect(html).toContain('Daily closing accrued-interest balance in USD');expect(html).toContain('35 stored datapoints');
 expect(html).toContain('1,000,000.123456789012');expect(html).toContain('Not assessed');expect(html).toContain('stale sources');
 expect(html.match(/<tbody><tr/g)).toHaveLength(1);expect(html.match(/<tr>/g)).toHaveLength(26);
 expect(html).toContain('<option value="all">All</option>');expect(html).toContain('1–25 of 35');
 expect(html.indexOf('<svg')).toBeLessThan(html.indexOf('<table'));
 expect(html).toContain('Chart type');expect(html).toContain('<option value="line" selected="">Line</option>');
 expect(html).toContain('<option value="bar">Bar</option>');
 expect(html).toContain('data-zero-reference="true"');
});
it('keeps the exact table available when values exceed safe chart coordinates',()=>{
 const html=renderToStaticMarkup(<BalanceSeriesReport rows={[{...rows[0],closing_balance:'9'.repeat(310)}]} from="2026-08-01" to="2026-08-01" currency="USD"/>);
 expect(html).toContain('could not be plotted safely');expect(html).toContain('<table');expect(html).not.toContain('<svg');
});
it('provides a native modal, named close control, bond selector and date-range form',()=>{
 const html=renderToStaticMarkup(<BalanceHistoryViewer strategyId="strategy" bonds={[{id:'bond',label:'Example Treasury',currency:'USD'}]} from="2026-08-01" to="2026-09-04" onClose={()=>{}}/>);
 expect(html).toContain('<dialog');expect(html).toContain('aria-label="Close balance chart"');
 expect(html).toContain('From date');expect(html).toContain('To date');expect(html).toContain('Example Treasury');
 expect(html).toContain('Show chart');
});
