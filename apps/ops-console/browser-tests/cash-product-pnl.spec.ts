import {test,expect} from './console-check';
import type {Batch} from '../src/features/valuation/types';

for(const kind of ['ETN','DIGITAL_ASSET'])test(`inspect ${kind} native units, quote FX and product boundaries`,async({page})=>{
 const crypto=kind==='DIGITAL_ASSET',quantity=crypto?'0.125':'10',openingPrice=crypto?'60000':'100',closingPrice=crypto?'62000':'110';
 const pnl=crypto?'265':'86',openingValue=crypto?'5625':'750',closingValue=crypto?'5890':'836';
 const batch:Batch={batch_id:'synthetic-cash-product',status:'STAGED',staged_by:'ops',reviews:[],
  presentation:{references:{subject:crypto?'BTC/USD · Synthetic Coinbase':'Synthetic exchange-traded note'},instrumentTypes:{subject:{code:kind,label:crypto?'Cryptoasset':'ETN'}},currencies:{usd:'USD',gbp:'GBP'},datasets:{},rules:{},users:{},context:{},totals:{interest:null,other:null},pendingAmendments:0},
  summary:{scope:'MARKET_ONLY',resultFormat:'POSITION_V2',marketPnl:pnl,openingValue,closingValue,executionValue:'0',reportingCurrencyId:'gbp',externalComparison:'NOT_COMPARED',limitations:[]},
  items:[{attribution_id:'line',trade_id:null,position_key:'position',subject_id:'subject',version:1,market_pnl:pnl,
   components:{PRICE:crypto?'187.5':'75',FX:crypto?'75':'10',PRICE_FX_CROSS:crypto?'2.5':'1'},
   evidence:{identity:{openingCutoff:'2026-10-19T23:59:59Z',closingCutoff:'2026-10-20T23:59:59Z',reportingCurrency:'gbp',openingValue,closingValue,executionValue:'0',
    bucket:{opening_quantity:quantity,closing_quantity:quantity,key:{product_basis:kind,currency_id:'usd',quantity_unit:'UNITS',unit_multiplier:'1',quote_factor:'1'}}},executionInputs:[],selections:[
      {valuation_date:'2026-10-19',pricing_date_used:'2026-10-19',selected_value:openingPrice},
      {valuation_date:'2026-10-20',pricing_date_used:'2026-10-20',selected_value:closingPrice},
      {input_role:'FX',valuation_date:'2026-10-19',valuation_source_currency_id:'usd',pricing_date_used:'2026-10-19',conversion:{rate:'0.75',sourceCurrencyId:'usd',targetCurrencyId:'gbp'}},
      {input_role:'FX',valuation_date:'2026-10-20',valuation_source_currency_id:'usd',pricing_date_used:'2026-10-20',conversion:{rate:'0.76',sourceCurrencyId:'usd',targetCurrencyId:'gbp'}}]}}]};
 await page.route('**/api/test-instrument-report',route=>route.fulfill({json:batch}));
 await page.goto('/?mode=instrument-report');
 await page.getByRole('button',{name:'Inspect position',exact:true}).click();
 const panel=page.getByRole('complementary',{name:'Position inspection'});
 await expect(panel).toContainText(crypto?'A stablecoin is not assumed equal to USD':'Underlying exposure and embedded leverage are not applied again');
 await expect(panel).toContainText('GBP per 1 USD');await expect(panel).toContainText(quantity);
 await expect(panel).toContainText('2026-10-19');await expect(panel).toContainText('2026-10-20');
 await page.screenshot({path:`test-results/cash-product-pnl-${kind}.png`,fullPage:true});
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await page.getByRole('button',{name:'Close position details',exact:true}).click();await expect(panel).toBeHidden();
});
