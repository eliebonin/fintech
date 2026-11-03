import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {InterestRegister,BalanceHistoryTable,InterestSource} from './interest-register';

it('provides task tabs without calculation shortcuts or unscoped writes',()=>{
 const html=renderToStaticMarkup(<InterestRegister canWrite={false}/>);
 expect(html).toContain('Daily interest');expect(html).toContain('Closing balance inputs');expect(html).toContain('Accrued balances');
 expect(html).toContain('role="tablist"');expect(html).toContain('Apply filters');
 expect(html).not.toContain('href="/valuation"');expect(html).not.toContain('Calculate FX impact');
 expect(html).toContain('Choose a strategy');expect(html).not.toContain('Add daily interest</button>');
});

it('keeps long source identities behind a closed disclosure',()=>{
 const html=renderToStaticMarkup(<InterestSource reference="retained:long-source-proof"/>);
 expect(html).toContain('<summary>Source reference</summary>');
 expect(html).toContain('retained:long-source-proof');expect(html).not.toContain('open=');
});

it('keeps exact grouped amounts, missing balances and stale source status distinct',()=>{
 const html=renderToStaticMarkup(<BalanceHistoryTable rows={[{history_id:'history-proof',instrument_id:'bond-proof',instrument_name:'Example Treasury',currency_code:'USD',value_date:'2026-10-20',
  opening_balance:'1000000.125',daily_earned:'20',trade_movements:'0',coupon_paid:'1000000',closing_balance:null,basis:'DERIVED',source_status:'STALE',evidence:{}}]}/>);
 expect(html).toContain('1,000,000.125');expect(html).toContain('Not assessed');expect(html).toContain('Stale');
 expect(html).toContain('Coupon paid');expect(html).toContain('Example Treasury');
});
