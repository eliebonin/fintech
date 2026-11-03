import {test,expect} from './console-check';
import type {Batch} from '../src/features/valuation/types';

function report(missing=false):Batch{
 const day={balance:{value_date:'2026-10-01',opening:missing?null:'1000',daily_earned:'20',trade_movements:'0',coupon_paid:'1000',closing:missing?null:'20',basis:'DERIVED',warnings:[]},opening_fx:missing?null:'0.75',closing_fx:missing?null:'0.76',amount:missing?null:'10',reason:missing?'OPENING_ACCRUED_BALANCE_UNAVAILABLE':null};
 return {batch_id:'synthetic-interest',status:'STAGED',staged_by:'ops',reviews:[],
  presentation:{references:{bond:'Example USD bond'},instrumentTypes:{bond:{code:'BOND',label:'Bond'}},currencies:{usd:'USD',gbp:'GBP'},datasets:{},rules:{},users:{},context:{},totals:{interest:'15.2',other:missing?null:'10'},pendingAmendments:0},
  summary:{scope:'ECONOMIC_RECORDED_INPUTS',resultFormat:'POSITION_V2',marketPnl:'100',openingValue:'1000',closingValue:'1100',executionValue:'0',netPnl:missing?'115.2':'125.2',reportingCurrencyId:'gbp',externalComparison:'NOT_COMPARED',limitations:[],pnlCompleteness:missing?'PARTIAL':'RECORDED_COMPONENTS',accruedBalanceCoverage:{status:missing?'MISSING_INPUTS':'INCLUDED',suppliedCount:missing?0:1,missingCount:missing?1:0,missing:missing?[{instrumentId:'bond',valueDate:'2026-10-01',reason:'OPENING_ACCRUED_BALANCE_UNAVAILABLE'}]:[],warnings:[]}},
  items:[{attribution_id:'interest-line',trade_id:null,position_key:'position',subject_id:'bond',version:1,market_pnl:'100',net_pnl:missing?'115.2':'125.2',components:{PRICE:'100',ACCRUAL:'15.2',...(missing?{}:{CARRY:'10'})},evidence:{economicInputs:[{kind:'ACCRUED_BALANCE_FX',currencyId:'usd',days:[day]}]}}]};
}

for(const missing of [false,true])test(`inspect frozen accrued stock and FX, missing data ${missing}`,async({page})=>{
 await page.route('**/api/test-instrument-report',route=>route.fulfill({json:report(missing)}));
 await page.goto('/?mode=instrument-report');
 await page.getByRole('button',{name:'Inspect position',exact:true}).click();
 const inspector=page.getByRole('region',{name:'Accrued-interest balance and FX'});
 await expect(inspector).toBeVisible();
 const table=inspector.getByRole('table',{name:'Daily accrued-interest balance · USD'});
 await expect(table).toContainText('20');
 if(missing){await expect(table).toContainText('Not calculated');await expect(page.getByText('Accrued-interest FX partially assessed.')).toBeVisible();}
 else{await expect(table).toContainText('1,000');await expect(table).toContainText('0.75');await expect(table).toContainText('0.76');}
 await page.screenshot({path:`test-results/accrued-balance-${missing?'missing':'complete'}.png`,fullPage:true});
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await page.getByRole('button',{name:'Close position details',exact:true}).click();
 await expect(page.getByRole('complementary',{name:'Position inspection'})).toBeHidden();
});
