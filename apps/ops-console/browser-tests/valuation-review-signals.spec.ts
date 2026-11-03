import {test,expect} from './console-check';
import type {Batch,Item} from '../src/features/valuation/types';

test('compact input review finds later positions and shows frozen dual-currency stocks',async({page})=>{
 const ordinary:Item[]=Array.from({length:29},(_,i)=>({attribution_id:String(i),subject_id:`equity${i}`,trade_id:null,version:1,market_pnl:'1',net_pnl:'1',components:{PRICE:'1'},evidence:{},display:{interest:null,other:null,attention:[]}}));
 const missing:Item={...ordinary[0],attribution_id:'missing-fx',subject_id:'missing',display:{interest:null,other:null,attention:['Interest FX unavailable']},evidence:{economicInputs:[{kind:'MISSING_DAILY_ACCRUAL_FX',valueDate:'2026-10-20'}]}};
 const bond:Item={...ordinary[0],attribution_id:'bond',subject_id:'bond',market_pnl:'0',net_pnl:'25.20',components:{PRICE:'0',ACCRUAL:'15.20',CARRY:'10'},
  display:{interest:'15.20',other:'10',attention:['Accrued balance mismatch'],accruedBalanceStocks:[{valueDate:'2026-10-20',currencyId:'usd',reportingCurrencyId:'gbp',openingReporting:'750.00',closingReporting:'19.00',openingBasis:'FROZEN_FX',closingBasis:'FROZEN_FX'}]},
  evidence:{economicInputs:[{kind:'ACCRUED_BALANCE_FX',currencyId:'usd',days:[{balance:{value_date:'2026-10-20',opening:'1000',daily_earned:'20',trade_movements:'0',coupon_paid:'1000',closing:'25',basis:'SUPPLIED_CLOSING_ANCHOR',warnings:['CLOSING_ANCHOR_DIFFERS_FROM_REPLAY']},opening_fx:'0.75',closing_fx:'0.76',amount:'10',reason:null}]}]}};
 const batch:Batch={batch_id:'synthetic-review',status:'STAGED',staged_by:'ops',reviews:[],items:[...ordinary,missing,bond],
  summary:{scope:'ECONOMIC_RECORDED_INPUTS',resultFormat:'POSITION_V2',marketPnl:'30',netPnl:'55.20',grossPnl:'55.20',openingValue:'0',closingValue:'30',executionValue:'0',reportingCurrencyId:'gbp',externalComparison:'NOT_COMPARED',limitations:[],accrualCoverage:{mode:'OPTIONAL',suppliedCount:1,missingCount:1,missing:[{instrumentId:'missing',valueDate:'2026-10-20'}]}},
  presentation:{references:{...Object.fromEntries(ordinary.map((row,i)=>[row.subject_id!,`Equity ${i}`])),missing:'Position missing interest FX',bond:'Bond to review'},currencies:{usd:'USD',gbp:'GBP'},datasets:{},rules:{},users:{},context:{},totals:{interest:'15.20',other:'10'},pendingAmendments:1}};
 await page.route('**/api/test-instrument-report',route=>route.fulfill({json:batch}));
 await page.goto('/?mode=instrument-report&reportView=breakdown');
 const review=page.locator('details.pnl-coverage-review');
 await expect(review).not.toHaveAttribute('open','');
 await expect(page.getByText('Publication blockers',{exact:true})).toBeVisible();
 const summary=review.locator(':scope > summary');await summary.focus();await summary.press('Enter');
 await expect(summary).toBeFocused();await expect(review).toContainText('Publication remains available');
 await review.getByRole('button',{name:'Show affected positions'}).click();
 await expect(review).not.toHaveAttribute('open','');
 const positions=page.getByRole('region',{name:'Position attribution'});
 await expect(page.getByRole('tab',{name:'Positions & cash'})).toHaveAttribute('aria-selected','true');
 await expect(positions).toContainText('2 matching of 31');await expect(positions.getByRole('row')).toHaveCount(3);
 await expect(page.getByRole('complementary',{name:'Position inspection'})).toBeHidden();
 await positions.getByRole('row').filter({hasText:'Bond to review'}).getByRole('button',{name:'Review notes: Accrued balance mismatch'}).click();
 const inspection=page.getByRole('complementary',{name:'Position inspection'});
 await expect(inspection).toBeVisible();await expect(inspection.getByText('750.00 GBP',{exact:true})).toBeVisible();
 await expect(inspection.getByText('19.00 GBP',{exact:true})).toBeVisible();
 await expect(inspection.getByRole('region',{name:'Position review notes'})).toContainText('Accrued balance mismatch');
 await page.screenshot({path:'test-results/valuation-review-signals.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await page.getByRole('button',{name:'Close position details',exact:true}).click();
 await expect(inspection).toBeHidden();
});
