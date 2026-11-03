import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {InterestInputEditor} from './interest-input-editor';
import {InterestInputTable} from './interest-input-tables';
import type {ClosingBalanceInput,DailyInterestInput,InterestOptions} from './interest-types';
const options:InterestOptions={bonds:[{id:'bond',label:'Example Treasury',currency:'USD',currencyId:'usd'}],currencies:[{id:'usd',label:'USD'}],canWrite:true};
const context={strategyId:'strategy',strategyLabel:'Example Strategy',from:'2026-10-01',to:'2026-10-20'};
const daily:DailyInterestInput={input_id:'proof-id',instrument_id:'bond',currency_id:'usd',value_date:'2026-10-20',daily_earned_interest:'1.123456789012',revision:3,payload:{sourceReference:'proof'}};
const closing:ClosingBalanceInput={input_id:'proof-id',instrument_id:'bond',currency_id:'usd',value_date:'2026-10-20',closing_balance:'100.123456789012',status:'ACTIVE',revision:2,source_reference:'statement'};
it('uses human context, an immutable correction identity and an exact amount',()=>{
 const html=renderToStaticMarkup(<InterestInputEditor editor={{kind:'daily',row:daily}} context={context} options={options} locked={false} error={null} onSave={()=>{}} onClose={()=>{}}/>);
 expect(html).toContain('Example Strategy');expect(html).toContain('Example Treasury');expect(html).toContain('revision 3');expect(html).toContain('1.123456789012');expect(html).toContain('readOnly=""');
 expect(html).toContain('Save new revision');expect(html).not.toContain('href="/valuation"');
});
it('separates withdrawal from editing a replacement amount and locks uncertain writes',()=>{
 const html=renderToStaticMarkup(<InterestInputEditor editor={{kind:'withdraw',row:closing}} context={context} options={options} locked error={new Error('Unknown outcome')} onSave={()=>{}} onClose={()=>{}}/>);
 expect(html).toContain('Withdrawal reason');expect(html).not.toContain('name="amount"');expect(html).toContain('does not replace the amount with zero');expect(html).toContain('fieldset disabled');
});
it('paginates the complete source dataset without losing precise values or source evidence',()=>{
 const html=renderToStaticMarkup(<InterestInputTable kind="daily" rows={Array.from({length:60},(_,i)=>({...daily,input_id:String(i)}))} options={options} writable={false} locked={false} onEdit={()=>{}}/>);
 expect(html).toContain('1–25 of 60');expect(html).toContain('value="all"');expect(html.match(/<tr>/g)).toHaveLength(26);expect(html).toContain('Retained input evidence');expect(html).not.toContain('Correct</button>');
});
