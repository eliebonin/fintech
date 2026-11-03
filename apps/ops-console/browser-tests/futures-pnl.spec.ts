import {test,expect} from './console-check';
import type {Batch} from '../src/features/valuation/types';

test('inspect futures price variation without gross-notional asset values',async({page})=>{
 const batch:Batch={batch_id:'synthetic-futures',status:'STAGED',staged_by:'ops',reviews:[],
  presentation:{references:{future:'Synthetic ES contract'},instrumentTypes:{future:{code:'FUTURE',label:'Future'}},currencies:{usd:'USD',gbp:'GBP'},datasets:{},rules:{},users:{},context:{},totals:{interest:null,other:null},pendingAmendments:0},
  summary:{scope:'MARKET_ONLY',resultFormat:'POSITION_V2',marketPnl:'375375',openingValue:'0',closingValue:'0',executionValue:'0',futuresVariationPnl:'375375',reportingCurrencyId:'gbp',externalComparison:'NOT_COMPARED',limitations:[]},
  items:[{attribution_id:'future-line',trade_id:null,position_key:'future-position',subject_id:'future',version:1,market_pnl:'375375',components:{PRICE:'375375',FX:'0',PRICE_FX_CROSS:'0'},
   evidence:{identity:{bucket:{key:{product_basis:'FUTURE',currency_id:'usd'}}},selections:[{valuation_date:'2026-10-19',pricing_date_used:'2026-10-19'},{valuation_date:'2026-10-20',pricing_date_used:'2026-10-20'},{valuation_date:'2026-10-20',pricing_date_used:'2026-10-20',input_role:'FX',valuation_source_currency_id:'usd'}],economicInputs:[{kind:'FUTURES_DAILY_VARIATION',currencyId:'usd',days:[{valueDate:'2026-10-20',openingDate:'2026-10-19',openingQuantity:'1000',closingQuantity:'1002',openingPrice:'6000',closingPrice:'6010',monetaryMultiplier:'50',quoteFactor:'1',localVariation:'500500',closingFx:'0.75',reportingVariation:'375375',executions:[{tradeId:'synthetic-buy',quantity:'2',price:'6005',effectiveAt:'2026-10-20T10:00:00Z'}]}]}]}}]};
 await page.route('**/api/test-instrument-report',route=>route.fulfill({json:batch}));
 await page.goto('/?mode=instrument-report');
 await page.getByRole('button',{name:'Inspect position',exact:true}).click();
 const inspection=page.getByRole('region',{name:'Manual futures P&L check'});
 await expect(inspection).toBeVisible();await expect(inspection).toContainText('500,500');await expect(inspection).toContainText('375,375');
 await expect(inspection).toContainText('GBP per 1 USD');await expect(inspection).toContainText('contract MTM is not assessed');
 await expect(inspection).toContainText('Actual FX date: 2026-10-20');
 await expect(inspection.getByRole('link',{name:/Buy/})).toHaveAttribute('href','/trades/synthetic-buy');
 await page.screenshot({path:'test-results/futures-pnl-inspection.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await page.getByRole('button',{name:'Close position details',exact:true}).click();
 await expect(page.getByRole('complementary',{name:'Position inspection'})).toBeHidden();
});
