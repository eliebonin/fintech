import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {BondCashflowScheduleTable,ScheduleEditor} from './bond-cashflow-schedule';

const cashflows=[
 {cashflow_id:'c',cashflow_key:'Final coupon',cashflow_type:'COUPON' as const,accrual_start:'2026-04-15',accrual_end:'2026-10-15',payment_date:'2026-10-15',coupon_rate:null,amount_per_100:null,amount_formula:'SOFR + spread'},
 {cashflow_id:'p',cashflow_key:'Redemption',cashflow_type:'PRINCIPAL' as const,accrual_start:null,accrual_end:null,payment_date:'2026-10-15',coupon_rate:null,amount_per_100:'100',amount_formula:null},
];
it('shows both coupon and principal with explicit unknown economics and original nominal basis',()=>{
 const html=renderToStaticMarkup(<BondCashflowScheduleTable cashflows={cashflows} currency="USD"/>);
 expect(html).toContain('Principal');expect(html).toContain('Coupon');
 expect(html).toContain('SOFR + spread');expect(html).toContain('Not fixed / unknown');
 expect(html).toContain('per 100 original nominal');expect(html).toContain('USD');
 expect(html).not.toContain('CONFIRMED');expect(html).not.toContain('>null<');
});
it('principal editor does not demand an accrual period or coupon rate',()=>{
 const html=renderToStaticMarkup(<ScheduleEditor disabled={false} onSave={()=>{}} schedule={{schedule_id:'s',revision:1,source_reference:'Synthetic',currencyCode:'USD',cashflows:[cashflows[1]]}}/>);
 expect(html).toContain('Payment type');expect(html).toContain('Add cashflow');
 expect(html).not.toContain('Accrual start');expect(html).not.toContain('Coupon rate');
 expect(html).toContain('Redemption');
});
