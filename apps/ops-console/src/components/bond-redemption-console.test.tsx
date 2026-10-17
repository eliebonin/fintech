import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {BondRedemptionConsole} from './bond-redemption-console';
it('requires scoped strategy selection and does not equate redemption with payment',()=>{
 const html=renderToStaticMarkup(<BondRedemptionConsole actorId="user"/>);
 expect(html).toContain('Choose a strategy');expect(html).toContain('Final interest, payment and cash balances are separate');
 expect(html).not.toContain('Approve and book');expect(html).not.toContain('Book now');
});
it('explains FX maturity selection without implying cash or full valuation support',()=>{
 const html=renderToStaticMarkup(<BondRedemptionConsole actorId="user" fx/>);
 expect(html).toContain('maturity-date policy-selected FX rate');
 expect(html).toContain('Discounted MTM modelling remains unsupported');
 expect(html).not.toContain('per 100 nominal');
});
