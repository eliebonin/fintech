import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {ReviewWorkspace} from './review-workspace';
const batch={batch_id:'batch',status:'STAGED',staged_by:'maker',summary:{marketPnl:'100',grossPnl:'110',netPnl:'90',scope:'ECONOMIC_RECORDED_INPUTS'},
 items:[{attribution_id:'a',version:1,subject_id:'bond',market_pnl:'100',gross_pnl:'110',net_pnl:'90',components:{PRICE:'100',ACCRUAL:'10',OTHER_COST:'-20'},evidence:{economicInputs:[{kind:'DAILY_ACCRUAL',valueDate:'2026-10-01',payload:{currencyId:'EUR',reportingCurrencyId:'GBP',amounts:{dailyLocal:'10',dailyBase:'8.6',balanceLocal:'990',balanceBase:'851.4',receivableFx:'9.9'}}}]}}]};
it('shows server totals and separates earned interest from accumulated balance',()=>{
 const html=renderToStaticMarkup(<ReviewWorkspace batch={batch} actorId="maker" canRequest canReview onApproved={()=>{}}/>);
 expect(html).toContain('Gross P&amp;L');expect(html).toContain('Net P&amp;L');
 expect(html).toContain('Daily earned');expect(html).toContain('Accumulated balance');expect(html).toContain('851.4');
 expect(html).toContain('Request component change');expect(html).toContain('Correct source inputs');
});
it('published and read-only results expose no mutation forms',()=>{
 for(const props of [{batch:{...batch,status:'PUBLISHED'},canRequest:true,canReview:true},{batch,canRequest:false,canReview:false}]){
  const html=renderToStaticMarkup(<ReviewWorkspace {...props} actorId="reviewer" onApproved={()=>{}}/>);
  expect(html).not.toContain('Request component change');expect(html).toContain('Market P&amp;L');
 }
});
