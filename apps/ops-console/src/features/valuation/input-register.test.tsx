import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {it,expect} from 'vitest';
import {InputRegister} from './input-register';
it('accepts daily interest with currency and no balance reconciliation',()=>{
 const html=renderToStaticMarkup(<InputRegister strategyId="strategy" policyId="" cutId="" reportingCurrencyId=""/>);
 expect(html).toMatch(/<input[^>]*required=""[^>]*name="currencyId"/);
 expect(html).toMatch(/<input[^>]*required=""[^>]*name="dailyEarned"/);
 expect(html).not.toContain('name="openingBalance"');
});
it('balance reconciliation is an explicit optional mode',()=>{
 const html=renderToStaticMarkup(<InputRegister strategyId="strategy" policyId="policy" cutId="cut" reportingCurrencyId="GBP"/>);
 expect(html).toContain('Include balance reconciliation');
 expect(html).not.toContain('name="balanceMovements"');
});
it('uses exact local daily/balance inputs and server-selected FX',()=>{
 const html=renderToStaticMarkup(<InputRegister strategyId="strategy" policyId="policy" cutId="cut" reportingCurrencyId="GBP"/>);
 expect(html).toContain('Daily earned interest');expect(html).toContain('Include balance reconciliation');
 expect(html).toContain('Source reference');expect(html).toContain('Eligibility convention');
 expect(html).not.toContain('name="openingFx"');expect(html).not.toContain('name="closingFx"');
});
it('requires explicit tenant strategy and policy scope before source entry',()=>{
 const html=renderToStaticMarkup(<InputRegister strategyId="" policyId="" cutId="" reportingCurrencyId=""/>);
 expect(html).toContain('Select strategy');expect(html).not.toContain('Record assessed input');
});
