import {test,expect} from './console-check';
import type {Batch} from '../src/features/valuation/types';

test('inspect whole-note prices, quote basis and reporting FX before technical proof',async({page})=>{
 const batch:Batch={batch_id:'synthetic-note',status:'STAGED',staged_by:'ops',reviews:[],
  presentation:{references:{note:'Synthetic funded note'},instrumentTypes:{note:{code:'STRUCTURED_PRODUCT',label:'Structured note'}},currencies:{usd:'USD',gbp:'GBP'},datasets:{},rules:{},users:{},context:{},totals:{interest:null,other:null},pendingAmendments:0},
  summary:{scope:'MARKET_ONLY',resultFormat:'POSITION_V2',marketPnl:'1740',openingValue:'73500',closingValue:'75240',executionValue:'0',reportingCurrencyId:'gbp',externalComparison:'NOT_COMPARED',limitations:[]},
  items:[{attribution_id:'note-line',trade_id:null,position_key:'note-position',subject_id:'note',version:1,market_pnl:'1740',components:{PRICE:'750',FX:'980',PRICE_FX_CROSS:'10'},
   evidence:{identity:{openingCutoff:'2026-10-19T23:59:59Z',closingCutoff:'2026-10-20T23:59:59Z',reportingCurrency:'gbp',openingValue:'73500',closingValue:'75240',executionValue:'0',
    bucket:{opening_quantity:'100000',closing_quantity:'100000',key:{product_basis:'STRUCTURED_PRODUCT',currency_id:'usd',quantity_unit:'NOMINAL',unit_multiplier:'1',quote_factor:'100'}},
    facts:[{booking:{product_evidence:{notePriceType:'DIRTY'}}}]},executionInputs:[],selections:[
      {valuation_date:'2026-10-19',pricing_date_used:'2026-10-19',selected_value:'98'},
      {valuation_date:'2026-10-20',pricing_date_used:'2026-10-20',selected_value:'99'},
      {input_role:'FX',valuation_date:'2026-10-19',valuation_source_currency_id:'usd',conversion:{rate:'0.75',sourceCurrencyId:'usd',targetCurrencyId:'gbp'}},
      {input_role:'FX',valuation_date:'2026-10-20',valuation_source_currency_id:'usd',conversion:{rate:'0.76',sourceCurrencyId:'usd',targetCurrencyId:'gbp'}}]}}]};
 await page.route('**/api/test-instrument-report',route=>route.fulfill({json:batch}));
 await page.goto('/?mode=instrument-report');
 await page.getByRole('button',{name:'Inspect position',exact:true}).click();
 const panel=page.getByRole('complementary',{name:'Position inspection'});
 await expect(panel).toContainText('Note quotation: DIRTY');await expect(panel).toContainText('100,000');
 await expect(panel).toContainText('GBP per 1 USD');await expect(panel).toContainText('98');await expect(panel).toContainText('99');
 await expect(panel).toContainText('later payment confirmation');
 await page.screenshot({path:'test-results/structured-note-pnl-inspection.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await page.getByRole('button',{name:'Close position details',exact:true}).click();
 await expect(panel).toBeHidden();
});
