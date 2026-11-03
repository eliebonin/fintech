import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {ResultWorkspace as ReportWorkspace} from './result-workspace';
import type {Batch} from './types';

const ResultWorkspace=(props:Omit<React.ComponentProps<typeof ReportWorkspace>,'activeTab'|'onNavigate'>)=><ReportWorkspace {...props} activeTab="positions" onNavigate={()=>{}}/>;

const batch:Batch={batch_id:'mixed',status:'STAGED',staged_by:'maker',reviews:[],
 summary:{scope:'ECONOMIC_WITH_CASH_FX',marketPnl:'100',netPnl:'1100',openingValue:'1000',closingValue:'1100',executionValue:'0',
  reportingCurrencyId:'gbp',externalComparison:'NOT_COMPARED',limitations:[],request:{strategy_id:'strategy',policy_id:'policy',reporting_currency_id:'gbp'},
  cashFxPnl:'1000',cashCoverage:{status:'INCLUDED',knownScopeCount:1,suppliedCount:1,missingCount:0,missing:[],scopes:[{accountId:'cash-account',currencyId:'usd'}]}},
 presentation:{references:{equity:'Example equity'},currencies:{usd:'USD',gbp:'GBP'},cashAccounts:{'cash-account':'Northern Trust · Custody'},
  datasets:{},rules:{},users:{},context:{},totals:{interest:null,other:'1000'},pendingAmendments:0},
 items:[{attribution_id:'position',version:1,trade_id:null,subject_id:'equity',market_pnl:'100',net_pnl:'100',components:{PRICE:'100'},evidence:{}},
  {attribution_id:'cash-line',version:1,trade_id:null,subject_id:null,cash_account_id:'cash-account',cash_currency_id:'usd',
   market_pnl:'0',net_pnl:'1000',components:{CASH_FX:'1000'},evidence:{resultFormat:'CASH_FX_V1',cashFx:{
    convention:'OPENING_BALANCE_EOD_MOVEMENTS',account_id:'cash-account',currency_id:'usd',reporting_currency_id:'gbp',days:[{
     value_date:'2026-10-20',opening:{cash_balance_id:'opening-snapshot',balance_as_of_date:'2026-10-19',amount:'100000',revision:1,note:'Custodian statement'},
     closing:{cash_balance_id:'closing-snapshot',balance_as_of_date:'2026-10-20',amount:'120000',revision:1},
     opening_fx:'0.75',closing_fx:'0.76',amount:'1000',fx_mode:'POLICY_FX'}],missing:[]},selections:[]}}]};

it('shows account-owned cash separately from investment positions without fake instrument names',()=>{
 const html=renderToStaticMarkup(<ResultWorkspace batch={batch} currency="GBP"/>);
 expect(html).toContain('Cash FX attribution');
 expect(html).toContain('Northern Trust · Custody');expect(html).toContain('USD');
 expect(html).toContain('1 positions');
 expect(html).not.toContain('Instrument name unavailable');
 expect(html).not.toContain('/instruments/cash-account');
 expect(html).not.toContain('Not implemented');
 expect(html).toContain('100000');expect(html).toContain('120000');
 expect(html).toContain('0.75');expect(html).toContain('0.76');
 expect(html).toContain('opening-snapshot');expect(html).toContain('Custodian statement');
});

it('makes missing cash coverage explicit rather than implying a confirmed zero',()=>{
 const partial={...batch,summary:{...batch.summary,cashCoverage:{...batch.summary.cashCoverage!,status:'PARTIAL' as const,
  missingCount:1,missing:[{accountId:'cash-account',currencyId:'usd',valueDate:'2026-10-20',missingOpening:true,missingClosing:false}]}}};
 const html=renderToStaticMarkup(<ResultWorkspace batch={partial} currency="GBP"/>);
 expect(html).toContain('Inputs to review');
 expect(html).toContain('Cash coverage · 1 missing daily scope inputs');
 expect(html).toContain('Missing is not zero');
 expect(html).toContain('2026-10-20');
 expect(html).not.toContain('accounts without a known uploaded currency scope');
 expect(html).not.toContain('unassessed accounts');
});

it('does not expose cash accounts, balances or attribution when current DISPLAY is denied',()=>{
 const html=renderToStaticMarkup(<ResultWorkspace batch={{...batch,summary:{...batch.summary,evidenceAccess:'DENIED'}}} currency="GBP"/>);
 expect(html).not.toContain('Cash FX attribution');expect(html).not.toContain('Northern Trust');
 expect(html).not.toContain('100000');expect(html).not.toContain('opening-snapshot');
});
