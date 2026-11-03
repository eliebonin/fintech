import {describe,expect,it} from 'vitest';
import {exactInterestAmount,interestRange,dailyInterestBody,closingBalanceBody,filterInterestRows} from './interest-model';
import type {DailyInterestInput,ClosingBalanceInput} from './interest-types';

describe('interest maintenance input contracts',()=>{
 it('keeps exact signed decimal values and accepts valid thousands grouping',()=>{
  expect(exactInterestAmount('1,234,567.123456789012')).toBe('1234567.123456789012');
  expect(exactInterestAmount('-0.000000000001')).toBe('-0.000000000001');
  expect(exactInterestAmount('0')).toBe('0');
  for(const value of ['1,23','1e3','NaN','1.0000000000001','1000000000000000000',''])expect(()=>exactInterestAmount(value)).toThrow();
 });
 it('validates complete calendar dates and the existing maintenance interval',()=>{
  expect(interestRange('2026-10-01','2026-10-20')).toBe('');
  expect(interestRange('2026-02-30','2026-03-01')).toMatch(/valid/i);
  expect(interestRange('2026-10-20','2026-10-01')).toMatch(/before/i);
  expect(interestRange('2024-01-01','2026-01-01')).toMatch(/366/);
 });
 it('preserves detailed reconciliation and eligibility when correcting daily sources',()=>{
  const row={input_id:'old',instrument_id:'bond',currency_id:'usd',value_date:'2026-10-20',daily_earned_interest:'2',revision:3,
   payload:{sourceReference:'proof',eligibleNominal:'1000000',eligibilityConvention:'settled nominal',policyId:'policy',cutId:'cut',reportingCurrencyId:'gbp',
    inputs:{openingBalance:'20',closingBalance:'22',balanceMovements:'0'}}} as DailyInterestInput;
  const body=dailyInterestBody('strategy',{instrumentId:'bond',currencyId:'usd',valueDate:'2026-10-20',amount:'3',source:'revised',openingBalance:'20',closingBalance:'23',balanceMovements:'0'},row);
  expect(body).toMatchObject({supersedesInputId:'old',dailyEarned:'3',openingBalance:'20',closingBalance:'23',balanceMovements:'0',policyId:'policy',cutId:'cut',reportingCurrencyId:'gbp',eligibleNominal:'1000000',eligibilityConvention:'settled nominal'});
  expect(body).not.toHaveProperty('fxEvidence');expect(body).not.toHaveProperty('inputs');
 });
 it('withdraws a closing input without requiring or sending a replacement amount',()=>{
  const row={input_id:'old',instrument_id:'bond',currency_id:'usd',value_date:'2026-10-20',closing_balance:'15',status:'ACTIVE',revision:1,source_reference:'statement'} as ClosingBalanceInput;
  expect(closingBalanceBody('strategy',{instrumentId:'bond',currencyId:'usd',valueDate:'2026-10-20',amount:'',source:'statement',reason:'Duplicate assessment'},row,true))
   .toMatchObject({closingBalance:null,status:'WITHDRAWN',supersedesInputId:'old',reason:'Duplicate assessment'});
 });
 it('rejects source corrections that attempt to change the retained identity',()=>{
  const row={input_id:'old',instrument_id:'bond',currency_id:'usd',value_date:'2026-10-20',payload:{}} as DailyInterestInput;
  expect(()=>dailyInterestBody('s',{instrumentId:'other',currencyId:'usd',valueDate:'2026-10-20',amount:'1',source:'x'},row)).toThrow(/identity/i);
 });
 it('filters the complete source collection before pagination',()=>{
  const rows=Array.from({length:60},(_,i)=>({instrument_id:i===55?'target':'other'}));
  expect(filterInterestRows(rows,'target')).toEqual([rows[55]]);
 });
});
