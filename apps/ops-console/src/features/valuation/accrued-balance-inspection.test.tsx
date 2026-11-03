import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {AccruedBalanceInspection} from './accrued-balance-inspection';
import type {Item} from './types';
const day={balance:{value_date:'2026-10-01',opening:'1000',daily_earned:'20',trade_movements:'0',coupon_paid:'1000',closing:'20',basis:'DERIVED',warnings:[]},opening_fx:'0.75',closing_fx:'0.76',amount:'10',reason:null};
const item={evidence:{economicInputs:[{kind:'ACCRUED_BALANCE_FX',currencyId:'usd',days:[day]}]}} as Item;
it('shows the retained monetary bridge and FX inputs without re-calculating or exposing UUIDs',()=>{
 const html=renderToStaticMarkup(<AccruedBalanceInspection item={item} currencies={{usd:'USD'}} currency="GBP"/>);
 for(const text of ['Opening balance','Daily earned','Coupon received','Closing balance','0.75','0.76','1,000','USD','GBP','20'])expect(html).toContain(text);
 expect(html).not.toContain('uuid');expect(html).toContain('Opening accrued balance ×');
});
it('shows unavailable stock and FX as not calculated rather than zero',()=>{
 const missing={evidence:{economicInputs:[{kind:'ACCRUED_BALANCE_FX',currencyId:'usd',days:[{...day,balance:{...day.balance,opening:null,closing:null},opening_fx:null,closing_fx:null,amount:null,reason:'OPENING_ACCRUED_BALANCE_UNAVAILABLE'}]}]}} as Item;
 const html=renderToStaticMarkup(<AccruedBalanceInspection item={missing} currencies={{usd:'USD'}} currency="GBP"/>);
 expect(html).toContain('Not calculated');expect(html).toContain('Opening accrued balance unavailable');expect(html).toContain('Unknown');
});
it('recognises an evidenced zero stock regardless of its stored decimal scale',()=>{
 const zero={evidence:{economicInputs:[{kind:'ACCRUED_BALANCE_FX',currencyId:'usd',days:[{...day,balance:{...day.balance,opening:'0.000000000000'},opening_fx:null,closing_fx:null,amount:'0',reason:null}]}]}} as Item;
 const html=renderToStaticMarkup(<AccruedBalanceInspection item={zero} currencies={{usd:'USD'}} currency="GBP"/>);
 expect(html).toContain('Not needed · zero opening balance');expect(html).not.toContain('Not calculated');
});
it('keeps an unclassified note coupon portion distinct from a confirmed zero receipt',()=>{
 const note={evidence:{economicInputs:[{kind:'ACCRUED_BALANCE_FX',currencyId:'usd',days:[{...day,balance:{...day.balance,coupon_paid:null,basis:'STRUCTURED_NOTE_CLEAN_ASSESSED'}}]}]}} as Item;
 expect(renderToStaticMarkup(<AccruedBalanceInspection item={note} currencies={{usd:'USD'}} currency="GBP"/>)).toContain('Not separately classified · in movements');
});

it('shows independently available local and reporting stocks from server projection',()=>{
 const projected={...item,display:{interest:null,other:null,attention:[],accruedBalanceStocks:[{valueDate:'2026-10-01',currencyId:'usd',reportingCurrencyId:'gbp',openingReporting:'750.00',closingReporting:null,openingBasis:'FROZEN_FX',closingBasis:'FX_NOT_RECORDED'}]}};
 const html=renderToStaticMarkup(<AccruedBalanceInspection item={projected} currencies={{usd:'USD'}} currency="GBP"/>);
 expect(html).toContain('750');expect(html).toContain('GBP');expect(html).toContain('Reporting stock unavailable');
 expect(html).toContain('Daily movements and FX proof');
});
