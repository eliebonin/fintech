import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {BondCouponConsole,CouponScheduleTable} from './bond-coupon-console';
it('separates contractual expectations, daily earnings and payment evidence',()=>{
 const html=renderToStaticMarkup(<BondCouponConsole/>);
 expect(html).toContain('Choose a strategy');
 expect(html).toContain('Daily interest remains in valuation');
 expect(html).toContain('No additional P&amp;L');
 expect(html).not.toContain('Confirm receipt</button>');
});
it('does not convert unknown coupon economics into zero or dates into payments',()=>{
 const html=renderToStaticMarkup(<CouponScheduleTable periods={[{period_id:'p',coupon_key:'Floating',accrual_start:'2026-01-01',accrual_end:'2026-07-01',payment_date:'2026-07-02',coupon_rate:null,amount_per_100:null,rate_formula:'SONIA + spread'}]}/>);
 expect(html).toContain('Not fixed / unknown');expect(html).toContain('SONIA + spread');
 expect(html).toContain('Scheduled payment');expect(html).not.toContain('CONFIRMED');
});
