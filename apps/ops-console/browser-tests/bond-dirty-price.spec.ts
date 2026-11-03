import {test,expect} from './console-check';
import type {Batch} from '../src/features/valuation/types';

test('inspect original DIRTY and derived CLEAN separately from daily interest',async({page})=>{
 const selections=[['2026-09-30','101','1'],['2026-10-01','101.02','1.02']].map(([day,dirty,accrued])=>({
  valuation_date:day,pricing_date_used:day,selected_value:dirty,valuation_value:'100',pricing_evidence:{bondPriceNormalization:{
   method:'DIRTY_MINUS_QUOTED_ACCRUAL_PER_100',marketDate:day,quoteSettlementDate:'2026-10-05',dirtyPrice:dirty,accruedPer100:accrued,cleanPrice:'100'}}}));
 const batch:Batch={batch_id:'synthetic-dirty-bond',status:'STAGED',staged_by:'ops',reviews:[],
  presentation:{references:{bond:'Synthetic plain bond'},instrumentTypes:{bond:{code:'BOND',label:'Bond'}},currencies:{gbp:'GBP'},datasets:{},rules:{},users:{},context:{},totals:{interest:'20',other:null},pendingAmendments:0},
  summary:{scope:'MARKET_ONLY',resultFormat:'POSITION_V2',marketPnl:'0',grossPnl:'20',netPnl:'20',openingValue:'100000',closingValue:'100000',executionValue:'0',reportingCurrencyId:'gbp',externalComparison:'NOT_COMPARED',limitations:[]},
  items:[{attribution_id:'bond-line',trade_id:null,position_key:'bond-position',subject_id:'bond',version:1,market_pnl:'0',gross_pnl:'20',net_pnl:'20',display:{interest:'20',other:null,attention:[]},components:{PRICE:'0',FX:'0',PRICE_FX_CROSS:'0',ACCRUAL:'20'},
   evidence:{identity:{bucket:{key:{product_basis:'BOND',currency_id:'gbp',quantity_unit:'NOMINAL',unit_multiplier:'1',quote_factor:'100'},opening_quantity:'100000',closing_quantity:'100000'},
    openingCutoff:'2026-09-30T16:00:00Z',closingCutoff:'2026-10-01T16:00:00Z',reportingCurrency:'gbp',openingValue:'100000',closingValue:'100000',executionValue:'0'},
    selections,executionInputs:[],economicInputs:[{kind:'DAILY_ACCRUAL',valueDate:'2026-10-01',payload:{currencyId:'gbp',reportingCurrencyId:'gbp',sourceReference:'Synthetic independent daily earnings',amounts:{dailyLocal:'20',dailyBase:'20',balanceLocal:'1250',balanceBase:'1250',receivableFx:'0'}}}]}}]};
 await page.route('**/api/test-instrument-report',route=>route.fulfill({json:batch}));
 await page.goto('/?mode=instrument-report');
 await page.getByRole('button',{name:'Inspect position',exact:true}).click();
 const quote=page.getByRole('region',{name:'Bond quote normalization'});
 await expect(quote).toBeVisible();await expect(quote).toContainText('101.02');await expect(quote).toContainText('1.02');
 await expect(quote).toContainText('2026-10-05');await expect(quote).toContainText('Daily interest');
 const closing=quote.getByRole('row').filter({has:page.getByRole('rowheader',{name:'2026-10-01',exact:true})});
 await expect(closing.getByRole('cell').last()).toHaveText('100');
 await page.screenshot({path:'test-results/bond-dirty-inspection.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await expect(quote).toBeVisible();
 await page.getByRole('button',{name:'Close position details',exact:true}).click();
 await expect(page.getByRole('complementary',{name:'Position inspection'})).toBeHidden();
});
