import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {CoverageReview,isPartialResult} from './coverage-review';
import {ReviewSummary} from './review-summary';
import {positionAttention,selectPositionRows} from './ops-review-model';
import type {Batch,Item} from './types';

const base:Batch={batch_id:'batch',status:'STAGED',staged_by:'ops',reviews:[],items:[],summary:{scope:'MARKET_ONLY',marketPnl:'1',netPnl:'1',openingValue:'1',closingValue:'2',executionValue:'0',reportingCurrencyId:'gbp',externalComparison:'NOT_COMPARED',limitations:[]}};

it('keeps cash-only gaps visible in one collapsed, nonblocking summary',()=>{
 const batch:Batch={...base,summary:{...base.summary,cashCoverage:{status:'PARTIAL',missingCount:1,suppliedCount:1,knownScopeCount:1,scopes:[],missing:[{accountId:'account',currencyId:'usd',valueDate:'2026-10-20',missingOpening:true,missingClosing:false}]}}};
 const html=renderToStaticMarkup(<CoverageReview batch={batch} onInspect={()=>{}}/>);
 expect(isPartialResult(batch)).toBe(true);expect(html).toContain('Inputs to review');expect(html).toContain('1 cash');
 expect(html).toContain('2026-10-20');expect(html).toContain('Publication remains available');
 expect(html).not.toContain('role="alert"');expect(html).not.toMatch(/<details[^>]*\sopen/);
 expect(html).not.toContain('role="dialog"');
 expect(renderToStaticMarkup(<ReviewSummary batch={batch} currency="GBP"/>)).toContain('Total included P&amp;L · partial');
});
it('does not invent warnings for disappeared scopes or certify complete economics',()=>{
 const batch={...base,summary:{...base.summary,cashCoverage:{status:'NOT_ASSESSED' as const,missingCount:0,suppliedCount:0,knownScopeCount:0,scopes:[],missing:[]}}};
 expect(isPartialResult(batch)).toBe(false);
 expect(renderToStaticMarkup(<CoverageReview batch={batch}/>)).toBe('');
});
it('routes missing optional FX, stocks and anchor differences through Attention before pagination',()=>{
 const item:Item={attribution_id:'last',trade_id:null,subject_id:'bond',version:1,market_pnl:'1',components:{PRICE:'1'},evidence:{economicInputs:[
  {kind:'MISSING_DAILY_ACCRUAL_FX'}, {kind:'ACCRUED_BALANCE_FX',days:[{reason:'ACCRUED_BALANCE_FX_UNAVAILABLE',balance:{warnings:['CLOSING_ANCHOR_DIFFERS_FROM_REPLAY']}}]}]}};
 expect(positionAttention(item)).toEqual(['Interest FX unavailable','Accrued FX unavailable','Accrued balance mismatch']);
 const items:Item[]=Array.from({length:26},(_,i)=>({...item,attribution_id:String(i),evidence:{}}));items.push(item);
 expect(selectPositionRows(items,undefined,{query:'',attentionOnly:true,sort:'name'}).map(row=>row.attribution_id)).toEqual(['last']);
 const html=renderToStaticMarkup(<CoverageReview batch={{...base,items:[item]}} onInspect={()=>{}}/>);
 expect(html).toContain('1 position');expect(html).toContain('Show affected positions');
});
