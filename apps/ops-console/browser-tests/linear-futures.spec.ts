import {test,expect} from './console-check';
import type {Batch} from '../src/features/valuation/types';

for(const settlement of ['CASH','PHYSICAL'] as const){
 const cv={kind:'FUTURE',quantityUnit:'CONTRACTS',effectiveFrom:'2026-09-01',priceCurrencyId:'usd',sourceReference:'Synthetic exchange rules',
  priceBasis:'UNDERLYING_UNIT',settlementMethod:settlement,contractSize:'5',contractSizeCurrencyId:'btc',monetaryMultiplier:'5',quoteFactor:'1',tickSize:'5',allowNegativePrice:false,
  lastTradingAtUtc:'2027-03-17T16:00:00Z',finalSettlementDate:'2027-03-19',deliveryStartDate:settlement==='PHYSICAL'?'2027-03-19':null,deliveryEndDate:settlement==='PHYSICAL'?'2027-03-19':null};
 test(`${settlement} crypto convention preserves approved economics and submission context`,async({page})=>{
  await page.route('**/api/test-future-convention',route=>route.fulfill({json:{kind:'FUTURE',tenantId:'synthetic-tenant',instrumentId:'synthetic-future',currencyCode:'USD',current:cv,
   currencies:[{groupCode:'REGULAR',label:'Fiat',items:[{currencyId:'usd',currencyCode:'USD',displayName:'US dollar'}]}]}}));
  const sent:Record<string,unknown>[]=[];
  await page.route('**/api/instruments/booking-conventions',route=>{
   expect(route.request().headers()['x-expected-tenant-id']).toBe('synthetic-tenant');
   const body=route.request().postDataJSON();sent.push(body);return route.fulfill({json:{data:{proposalId:'synthetic-convention-proposal'}}});
  });
  await page.goto('/?mode=future-convention');
  await expect(page.getByText('Price basis:',{exact:false})).toContainText('Underlying-unit quote');
  await expect(page.getByRole('textbox',{name:'Underlying units per contract',exact:true})).toHaveValue('5');
  await expect(page.getByRole('textbox',{name:'Underlying units per contract',exact:true})).toHaveAttribute('readonly','');
  await page.getByLabel('Effective from',{exact:true}).fill('2026-10-02');
  await page.getByRole('textbox',{name:'Source evidence / term-sheet or exchange-specification reference'}).fill('Reviewed synthetic source');
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  await page.getByRole('button',{name:'Submit for approval',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Submitted for approval'})).toBeVisible();
  expect(sent).toHaveLength(1);expect(sent[0].convention).toEqual({...cv,effectiveFrom:'2026-10-02',sourceReference:'Reviewed synthetic source'});
 });

 test(`${settlement} crypto daily P&L shows exact inputs and delivery boundary`,async({page})=>{
  const batch:Batch={batch_id:'synthetic-linear-future',status:'STAGED',staged_by:'ops',reviews:[],
   presentation:{references:{future:'Synthetic BTC March future'},instrumentTypes:{future:{code:'FUTURE',label:'Future'}},currencies:{usd:'USD',gbp:'GBP'},datasets:{},rules:{},users:{},context:{},totals:{interest:null,other:null},pendingAmendments:0},
   summary:{scope:'MARKET_ONLY',resultFormat:'POSITION_V2',marketPnl:'8000',openingValue:'0',closingValue:'0',executionValue:'0',futuresVariationPnl:'8000',reportingCurrencyId:'gbp',externalComparison:'NOT_COMPARED',limitations:[]},
   items:[{attribution_id:'future-line',trade_id:null,position_key:'future-position',subject_id:'future',version:1,market_pnl:'8000',components:{PRICE:'8000',FX:'0',PRICE_FX_CROSS:'0'},
    evidence:{identity:{bucket:{key:{product_basis:'FUTURE',currency_id:'usd'}}},economicInputs:[{kind:'FUTURES_DAILY_VARIATION',currencyId:'usd',contractConvention:cv,
     days:[{valueDate:'2026-10-20',openingDate:'2026-10-19',openingQuantity:'2',closingQuantity:'2',openingPrice:'100000',closingPrice:'101000',monetaryMultiplier:'5',quoteFactor:'1',localVariation:'10000',closingFx:'0.8',reportingVariation:'8000',executions:[]}]}]}}]};
  await page.route('**/api/test-instrument-report',route=>route.fulfill({json:batch}));await page.goto('/?mode=instrument-report');
  await page.getByRole('button',{name:'Inspect position',exact:true}).click();
  const report=page.getByRole('region',{name:'Manual futures P&L check'});
  for(const text of ['100,000','101,000','10,000','8,000','Underlying-unit quote','2027-03-19','No cash or underlying delivery is posted'])await expect(report).toContainText(text);
  await expect(report).toContainText(settlement==='PHYSICAL'?'Physical delivery':'Cash settlement');
  await page.screenshot({path:`test-results/linear-futures-${settlement}.png`,fullPage:true});
  await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  await page.getByRole('button',{name:'Close position details',exact:true}).click();await expect(page.getByRole('complementary',{name:'Position inspection'})).toBeHidden();
 });
}
