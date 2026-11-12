import {test,expect} from './console-check';
const strategy='00000000-0000-7000-8000-000000000555',instrument='00000000-0000-7000-8000-000000000556';
test('FX event filter and side panel use native FX routes, preserving worklist context',async({page})=>{
 const calls:{path:string;method:string;url:URL}[]=[];let booked=false;
 await page.route('**/api/lifecycle/**',route=>{
  const request=route.request(),url=new URL(request.url()),path=url.pathname.replace('/api/lifecycle/','');calls.push({path,method:request.method(),url});
  if(path==='worklist/options')return route.fulfill({json:{items:[{strategyId:strategy,label:'FX strategy'}],total:1}});
  if(path==='worklist'){const shown=url.searchParams.get('eventType')!=='BOND_MATURITY';return route.fulfill({json:{items:shown?[{eventKey:'forward-event',eventType:'FX_FORWARD_MATURITY',instrumentType:'FX_FORWARD',strategyId:strategy,strategyName:'FX strategy',instrumentId:instrument,instrumentName:'GBP / USD October Forward',maturityDate:'2026-10-01',status:booked?'BOOKED':'OVERDUE',attention:'ACTIONABLE',quantities:booked?[]:[{currency:'GBP',unit:'CURRENCY_AMOUNT',netQuantity:'1000000',grossQuantity:'1000000',entries:1}],remainingEntries:booked?0:1,selectedTier:3,maximumTier:3,processingMode:'DIRECT',reasons:['Exposure closure does not move cash.'],actionHref:`/trades/lifecycle?product=fx-forward&strategyId=${strategy}&instrumentId=${instrument}`,positionAssessed:true}]:[],total:shown?1:0,limit:25,offset:0,fromDate:url.searchParams.get('fromDate'),toDate:url.searchParams.get('toDate'),evaluatedAt:'2026-11-11T10:00:00Z',statusCounts:shown?{OVERDUE:1}:{},instrumentDisplays:{}}});}
  if(path==='fx-forward/options')return route.fulfill({json:{strategies:[{id:strategy,label:'FX strategy'}],instruments:[{id:instrument,label:'GBP / USD October Forward'}],policy:{mode:'DIRECT',revision:1,pricing_policy_id:'policy'},permissions:{MARKET_DATA_READ:true,LIFECYCLE_READ:true,LIFECYCLE_PREPARE:true,LIFECYCLE_BOOK:true,TRADE_WRITE:true},assistance:{selectedTier:3,maximumTier:3,processingMode:'DIRECT',operations:{PREVIEW:{allowed:true,reasons:[]},DIRECT:{allowed:true,reasons:[]},PREPARE:{allowed:true,reasons:[]}}}}});
  if(path==='fx-forward/closures/preview')return route.fulfill({json:{inputHash:'a'.repeat(64),inputs:{valueDate:'2026-10-01',price:'1.12',suggestedPrice:'1.12',mode:'DIRECT',quoteConvention:'USD_PER_GBP',fxEvidence:{observationDate:'2026-10-01',method:'DIRECT'},movements:[{subjectId:instrument,quantity:'-1000000',cleanAmount:null,quoteAmount:'-1120000',annotationFields:[]}]}}});
  if(path==='fx-forward/closures/book'){booked=true;return route.fulfill({json:{trade_ids:['synthetic-fx-close']}});}
  return route.fulfill({json:{items:[],total:0}});
 });
 await page.goto('/?mode=lifecycle-worklist');
 await page.getByRole('combobox',{name:'Event type',exact:true}).selectOption('FX_FORWARD_MATURITY');await page.getByRole('button',{name:'Apply filters',exact:true}).click();
 await expect.poll(()=>calls.filter(c=>c.path==='worklist').at(-1)?.url.searchParams.get('eventType')).toBe('FX_FORWARD_MATURITY');
 const before=page.url();await page.getByRole('button',{name:/Review closing entry for GBP/}).click();
 const panel=page.getByRole('dialog',{name:'Review closing entry',exact:true});await expect(panel).toBeVisible();expect(page.url()).toBe(before);
 await expect(panel.getByRole('link',{name:'Open full workspace'})).toHaveAttribute('href',/product=fx-forward/);
 expect(calls.filter(c=>c.method==='POST')).toHaveLength(0);
 await panel.getByRole('button',{name:'Load closing inputs',exact:true}).click();await expect(panel).toContainText('USD_PER_GBP');await panel.getByRole('button',{name:'Book now',exact:true}).click();
 await expect(panel.getByRole('status').filter({hasText:'Recorded 1'})).toBeVisible();expect(calls.some(c=>c.path==='fx-forward/closures/book')).toBe(true);expect(calls.some(c=>c.path.startsWith('bond-redemptions'))).toBe(false);
 await panel.getByRole('button',{name:'Close closing entry'}).click();await expect(page.getByRole('combobox',{name:'Event type',exact:true})).toHaveValue('FX_FORWARD_MATURITY');
});
