import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it,vi} from 'vitest';
import {BalanceHistoryTable} from './balance-history-table';
import type {BalanceHistoryRow} from './interest-types';
const row=(id:string,name:string):BalanceHistoryRow=>({history_id:id,instrument_id:id,instrument_name:name,currency_code:'GBP',value_date:'2026-10-20',
 opening_balance:'100',daily_earned:'1',trade_movements:'0',coupon_paid:'0',closing_balance:'101',basis:'DERIVED',source_status:'CURRENT',evidence:{}});
function find(node:any,predicate:(value:any)=>boolean):any{
 if(!node||typeof node!=='object')return;if(predicate(node))return node;
 for(const child of [node.props?.children].flat(Infinity)){const found=find(child,predicate);if(found)return found;}
}
it('opens the chart for the clicked row rather than the first instrument',()=>{
 const a=row('first-bond','First bond'),b=row('second-bond','Second bond'),open=vi.fn();
 const tree=BalanceHistoryTable({rows:[a,b],onViewChart:open});
 const action=find(tree,node=>node.type==='button'&&node.props['aria-label']==='View balance chart for Second bond');
 expect(action).toBeTruthy();action.props.onClick();expect(open).toHaveBeenCalledWith(b);
 const html=renderToStaticMarkup(tree);expect(html.match(/aria-haspopup="dialog"/g)).toHaveLength(2);
});
it('omits nested chart actions in the viewer table and respects a locked workbench',()=>{
 expect(renderToStaticMarkup(<BalanceHistoryTable rows={[row('bond','Bond')]}/>)).not.toContain('View chart');
 const html=renderToStaticMarkup(<BalanceHistoryTable rows={[row('bond','Bond')]} onViewChart={()=>{}} chartDisabled/>);
 expect(html).toContain('disabled=""');
});
it('keeps the maintenance table compact while retaining the exact balance bridge in evidence',()=>{
 const html=renderToStaticMarkup(<BalanceHistoryTable rows={[row('bond','Bond')]} compact/>);
 expect(html).not.toContain('scope="col" class="pnl-amount">Daily earned');
 expect(html).toContain('<dt>Daily earned</dt><dd>1</dd>');expect(html).toContain('<dt>Coupon paid</dt><dd>0</dd>');
});
it('shows a shared snapshot date once while the chart datapoint table retains its date column',()=>{
 const snapshot=renderToStaticMarkup(<BalanceHistoryTable rows={[row('bond','Bond')]} compact snapshotDate="2026-10-20"/>);
 expect(snapshot).toContain('Balances on 2026-10-20');expect(snapshot).not.toMatch(/<th[^>]*>Date<\/th>/);
 const history=renderToStaticMarkup(<BalanceHistoryTable rows={[row('bond','Bond')]}/>);
 expect(history).toMatch(/<th[^>]*>Date<\/th>/);expect(history).toMatch(/<td[^>]*>2026-10-20<\/td>/);
});
