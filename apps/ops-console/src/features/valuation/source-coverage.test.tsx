import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {PnlSourceCoverage} from './source-coverage';
import type {Batch,SourceCoverageRow} from './types';

function fixture(row:SourceCoverageRow):Batch{
 return {batch_id:'retained',status:'STAGED',staged_by:'maker',reviews:[],items:[],
  summary:{scope:'SUPPORTED_ECONOMIC_ALPHA',marketPnl:'0',netPnl:'0',openingValue:'0',closingValue:'0',
   executionValue:'0',reportingCurrencyId:'gbp',externalComparison:'NOT_COMPARED',limitations:[]},
  presentation:{references:{},currencies:{gbp:'GBP'},datasets:{},rules:{},users:{},context:{},
   totals:{interest:null,other:null},pendingAmendments:0,sourceCoverage:{
    basis:'STORED_REPORTING_CURRENCY_COMPONENTS',rows:[row],includedTotal:row.amount,recordedNet:null,reconciliation:'NOT_ASSESSED'}}};
}
const unknown:SourceCoverageRow={code:'PRICE',label:'Price movements',componentCodes:['PRICE'],
 description:'Historical component breakdown unavailable.',amount:null,status:'NOT_ASSESSED',positionCount:0,missingCount:0};

it.each([
 ['12.50','pnl-positive'],['-12.50','pnl-negative'],
 ['0.0000000000000000000000001','pnl-positive'],['-0.0000000000000000000000001','pnl-negative'],
 ['0',null],['-0.000',null],[null,null],['unavailable',null],
])('colours source amounts and the included total by exact sign for %s',(amount,tone)=>{
 const html=renderToStaticMarkup(<PnlSourceCoverage batch={fixture({...unknown,amount})} currency="GBP" onInspect={()=>{}}/>);
 const table=html.match(/<table[\s\S]*?<\/table>/)![0];
 if(tone){
  expect(table.match(new RegExp(`class="pnl-amount ${tone}"`,'g'))).toHaveLength(2);
  expect(table).not.toContain(tone==='pnl-positive'?'pnl-negative':'pnl-positive');
 }else{
  expect(table).not.toContain('pnl-positive');
  expect(table).not.toContain('pnl-negative');
 }
});

it('never claims an absence of contributions when historical coverage is not assessed',()=>{
 const html=renderToStaticMarkup(<PnlSourceCoverage batch={fixture(unknown)} currency="GBP" onInspect={()=>{}}/>);
 expect(html).toContain('Not assessed');
 expect(html).not.toContain('No contributions');
 expect(html).not.toContain('No recorded contributions');
 expect(html).not.toContain('No recorded entries');
 expect(html).not.toContain('0.00');
});

it('preserves exact tiny amounts while displaying a signed nonzero marker',()=>{
 const row={...unknown,status:'INCLUDED' as const,amount:'-0.000001',positionCount:1};
 const html=renderToStaticMarkup(<PnlSourceCoverage batch={fixture(row)} currency="GBP" onInspect={()=>{}}/>);
 expect(html).toContain('−&lt;0.01');
 expect(html).toContain('title="-0.000001"');
 expect(html).toContain('<dd>-0.000001</dd>');
 expect(html).toContain('Inspect positions: Price movements');
 expect(html).not.toContain('>0.00<');
});

it('distinguishes assessed absence from historical unknown and recorded zero',()=>{
 const absent={...unknown,status:'NOT_RECORDED' as const};
 const html=renderToStaticMarkup(<PnlSourceCoverage batch={fixture(absent)} currency="GBP" onInspect={()=>{}}/>);
 expect(html).toContain('No recorded entries');
 const zero={...unknown,status:'INCLUDED' as const,amount:'0',positionCount:1};
 const recorded=renderToStaticMarkup(<PnlSourceCoverage batch={fixture(zero)} currency="GBP" onInspect={()=>{}}/>);
 expect(recorded).toContain('>0.00<');
 expect(recorded).toContain('Inspect positions: Price movements');
 expect(recorded).toContain('<span class="pnl-amount" title="0">0.00</span>');
});

it('does not show a cash warning banner when cash is included',()=>{
 const batch=fixture({...unknown,code:'CASH_BALANCE_FX',label:'Cash-balance FX P&L',componentCodes:['CASH_FX'],
  status:'INCLUDED',amount:'14.65',cashAccountCount:5});
 batch.summary.cashCoverage={status:'INCLUDED',knownScopeCount:5,suppliedCount:5,missingCount:0,missing:[],scopes:[]};
 const html=renderToStaticMarkup(<PnlSourceCoverage batch={batch} currency="GBP" onInspect={()=>{}}/>);
 expect(html).not.toContain('pnl-cash-gap');
 expect(html).not.toContain('Cash FX included · opening-balance convention.');
 expect(html).toContain('Cash-balance FX P&amp;L');
 expect(html).toContain('14.65');
 expect(html).toContain('Included · recorded');
});

it('keeps actual missing cash inputs visible',()=>{
 const batch=fixture({...unknown,code:'CASH_BALANCE_FX',label:'Cash-balance FX P&L',componentCodes:['CASH_FX'],
  status:'MISSING_INPUTS',missingCount:1});
 batch.summary.cashCoverage={status:'MISSING_INPUTS',knownScopeCount:1,suppliedCount:0,missingCount:1,
  missing:[{accountId:'account',currencyId:'usd',valueDate:'2026-10-20',missingOpening:true,missingClosing:false}],scopes:[]};
 const html=renderToStaticMarkup(<PnlSourceCoverage batch={batch} currency="GBP" onInspect={()=>{}}/>);
 expect(html).not.toContain('pnl-cash-gap');
 expect(html).toContain('1 missing cash scope/date');
 expect(html).toContain('Not supplied · Not included');
});
