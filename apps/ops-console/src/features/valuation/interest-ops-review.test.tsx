import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {InterestOpsReview} from './interest-ops-review';
it('uses one strategy and one date, with no historical range in the maintenance workflow',()=>{
 const html=renderToStaticMarkup(<InterestOpsReview stage="DAILY" initialStrategy="" initialDate="2026-10-20"/>);
 expect(html).toContain('Value date');expect(html).not.toContain('From date');expect(html).not.toContain('To date');
 expect(html).toContain('Daily accrual review');expect(html).toContain('Balance review');
 expect(html).not.toContain('Validate all</button>');
});
it('distinguishes balance review from P&L publication',()=>{
 const html=renderToStaticMarkup(<InterestOpsReview stage="BALANCE" initialStrategy="" initialDate="2026-10-20"/>);
 expect(html).toContain('Balance review');expect(html).toContain('does not publish');expect(html).not.toContain('href="/valuation"');
});
it('offers independent balance exploration without requiring daily validation',()=>{
 const html=renderToStaticMarkup(<InterestOpsReview stage="DAILY" initialStrategy="strategy" initialDate="2026-10-20"/>);
 expect(html).toContain('Explore balances');
 expect(html).toContain('/valuation/interest/explorer?strategyId=strategy&amp;toDate=2026-10-20');
});
