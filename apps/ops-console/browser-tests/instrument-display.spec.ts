import {test,expect} from './console-check';
import type {Batch,Presentation} from '../src/features/valuation/types';
import type {InstrumentDisplays} from '../src/lib/instrument-display';

function report():Batch{
 const examples=[
  ['Air Liquide','TICKER','AI','EQUITY','Equity','Euronext Paris','EUR quote','air-parent'],
  ['Air Liquide','TICKER','AIL','EQUITY','Equity','Tradegate','EUR quote','air-parent'],
  ['UK Treasury Bill','ISIN','GB00BSGRV302','BOND','Bond','','GBP denomination','bond'],
  ['S&P 500 future','CONTRACT_SYMBOL','ESZ6','FUTURE','Future','CME','USD quote','future'],
  ['SPX December put','CONTRACT_SYMBOL','SPX.202612.P.05800000','OPTION','Option','Cboe','USD quote','option'],
  ['SPX total return swap','TENANT_REFERENCE','SPX_SWAP_CLIENT_7','SWAP','Swap','','USD denomination','swap'],
  ['Example fund share class','ISIN','IE00EXAMPLE01','FUND','Fund','','EUR denomination','fund'],
  ['Example AMC','ISIN','DE000EXAMPLE1','ACTIVELY_MANAGED_CERTIFICATE','AMC','','USD denomination','amc'],
  ['Missing identifier bond','','','BOND','Bond','','GBP denomination','missing'],
 ];
 const instrumentDisplays:InstrumentDisplays=Object.fromEntries(examples.map(([name,scheme,value,type,typeLabel,venue,currency,parent],index)=>[`s${index}`,{
  primaryName:name,identifier:scheme?{scheme,value}:null,instrumentId:parent,context:[venue,currency].filter(Boolean),
  instrumentType:type,instrumentTypeLabel:typeLabel,searchText:`${name} ${value} INTERNAL_IMPORT_${index}`,basis:'CURRENT_ACCESSIBLE_METADATA' as const}]));
 const presentation:Presentation={references:{},instrumentDisplays,instrumentTypes:Object.fromEntries(Object.entries(instrumentDisplays).map(([id,d])=>[id,{code:d.instrumentType!,label:d.instrumentTypeLabel!}])),currencies:{},datasets:{},rules:{},users:{},context:{},totals:{interest:null,other:null},pendingAmendments:0};
 return {batch_id:'display-fixture',status:'STAGED',staged_by:'ops',reviews:[],presentation,
  summary:{scope:'SUPPORTED_ECONOMIC_ALPHA',resultFormat:'POSITION_V2',marketPnl:'9',openingValue:'100',closingValue:'109',executionValue:'0',reportingCurrencyId:'gbp',externalComparison:'NOT_COMPARED',limitations:[]},
  items:examples.map((_,index)=>({attribution_id:`a${index}`,trade_id:null,subject_id:`s${index}`,version:1,market_pnl:'1',components:{PRICE:'1'},evidence:{}}))};
}

test('readable product identities retain listing links, alias search and keyboard inspection',async({page})=>{
 await page.route('**/api/test-instrument-report',r=>r.fulfill({json:report()}));
 await page.goto('/?mode=instrument-report');
 const table=page.getByRole('table',{name:'Position attribution'});
 await expect(table).toBeVisible();
 const typeHeading=table.getByRole('columnheader',{name:'Instrument type',exact:true});
 await expect(typeHeading).toHaveCSS('text-align','center');
 await expect(table.locator('tbody tr').first().locator('.pnl-instrument-type')).toHaveCSS('text-align','center');
 await expect(table.getByRole('link',{name:'Air Liquide'})).toHaveCount(2);
 await expect(table.getByRole('link',{name:'Air Liquide'}).nth(0)).toHaveAttribute('href','/instruments/air-parent#listing-s0');
 await expect(table.getByRole('link',{name:'Air Liquide'}).nth(1)).toHaveAttribute('href','/instruments/air-parent#listing-s1');
 await expect(table.getByText('ISIN GB00BSGRV302 · GBP denomination',{exact:true})).toBeVisible();
 await expect(table.getByText('Identifier not supplied · GBP denomination',{exact:true})).toBeVisible();
 await expect(table).not.toContainText('INTERNAL_IMPORT');
 await page.getByRole('searchbox',{name:'Search positions'}).fill('INTERNAL_IMPORT_5');
 await expect(table.locator('tbody tr')).toHaveCount(1);
 await expect(table.getByRole('link',{name:'SPX total return swap'})).toBeVisible();
 const inspect=table.getByRole('button',{name:'Inspect position'});await inspect.focus();await page.keyboard.press('Enter');
 await expect(page.getByRole('complementary',{name:'Position inspection'})).toBeVisible();
 await page.getByRole('button',{name:'Close position details'}).click();await expect(inspect).toBeFocused();
 await page.getByRole('searchbox',{name:'Search positions'}).fill('');
 await page.screenshot({path:'test-results/shared-instrument-display.png',fullPage:true});
});

test('identifiers wrap on narrow screens without widening the page',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.route('**/api/test-instrument-report',r=>r.fulfill({json:report()}));
 await page.goto('/?mode=instrument-report');
 await expect(page.getByRole('link',{name:'SPX December put'})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});
