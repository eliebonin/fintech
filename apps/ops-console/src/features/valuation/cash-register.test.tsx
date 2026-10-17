import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {CashRegister} from './cash-register';
it('requires a strategy and labels balances as snapshots not profit',()=>{
 const html=renderToStaticMarkup(<CashRegister canWrite={false}/>);
 expect(html).toContain('Choose a strategy');expect(html).toContain('not cash P&amp;L');
 expect(html).not.toContain('Save balance');expect(html).not.toContain('Create account');
});
