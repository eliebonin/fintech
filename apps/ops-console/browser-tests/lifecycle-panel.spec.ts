import {test,expect,type Page} from './console-check';
const strategy='00000000-0000-7000-8000-000000000555',instrument='00000000-0000-7000-8000-000000000556';
async function setup(page:Page,{direct=false,uncertain=false,rejectRetry=false,historyPaging=false,correction=false}={}){
 let prepared=false,booked=false;const requests:{path:string;method:string;key?:string;body?:any;url:URL}[]=[];
 await page.route('**/api/lifecycle/**',route=>{
  const request=route.request(),url=new URL(request.url()),path=url.pathname.replace('/api/lifecycle/','');
  requests.push({path,method:request.method(),key:request.headers()['idempotency-key'],body:request.method()==='POST'?request.postDataJSON():undefined,url});
  if(path==='worklist/options')return route.fulfill({json:{items:[{strategyId:strategy,label:'GBP Income'}],total:1}});
  if(path==='worklist')return route.fulfill({json:{items:[{eventKey:'one-event',eventType:'BOND_MATURITY',instrumentType:'BOND',strategyId:strategy,strategyName:'GBP Income',instrumentId:instrument,instrumentName:'Treasury Gilt',identifier:'GB00TEST',maturityDate:'2026-11-05',status:booked?'BOOKED':prepared?'PREPARED':'OVERDUE',attention:'ACTIONABLE',quantities:booked?[]:[{currency:'GBP',unit:'NOMINAL',netQuantity:'100000',grossQuantity:'100000',entries:1}],remainingEntries:booked?0:1,selectedTier:3,maximumTier:3,processingMode:direct?'DIRECT':'REVIEW',reasons:['Current closing inputs are checked before booking.'],actionLabel:'Prepare for approval',actionHref:`/trades/lifecycle?strategyId=${strategy}&instrumentId=${instrument}`,positionAssessed:true}],total:1,offset:Number(url.searchParams.get('offset')??0),limit:25,evaluatedAt:'2026-11-10T12:00:00Z',fromDate:url.searchParams.get('fromDate'),toDate:url.searchParams.get('toDate'),statusCounts:{[booked?'BOOKED':prepared?'PREPARED':'OVERDUE']:1},instrumentDisplays:{}}});
  const inputs={valueDate:'2026-11-05',price:'100',mode:direct?'DIRECT':'REVIEW',movements:[{subjectId:instrument,quantity:'-100000',cleanAmount:'100000',annotationFields:[{definitionId:'note',label:'Desk note',valueType:'TEXT',required:false,locked:false,value:null}]}]};
  if(path==='options')return route.fulfill({json:{strategies:[{id:strategy,label:'GBP Income'}],instruments:[{id:instrument,label:'Treasury Gilt'}],policy:{mode:direct?'DIRECT':'REVIEW',revision:1},permissions:{LIFECYCLE_READ:true,LIFECYCLE_PREPARE:true,LIFECYCLE_BOOK:true,TRADE_WRITE:true,TRADE_CORRECT:correction},assistance:{selectedTier:3,maximumTier:3,processingMode:direct?'DIRECT':'REVIEW',operations:{PREVIEW:{allowed:true,reasons:[]},PREPARE:{allowed:true,reasons:[]},DIRECT:{allowed:direct,reasons:[]}}}}});
  if(path==='bond-redemptions/preview')return route.fulfill({json:{inputHash:'a'.repeat(64),inputs}});
  if(path==='bond-redemptions/prepare'){prepared=true;return route.fulfill({json:{proposal_id:'proposal'}});}
  if(path==='bond-redemptions/cancel'){if(requests.filter(r=>r.path===path).length===1)return route.fulfill({status:503,json:{detail:'Outcome unknown; retry unchanged.'}});return route.fulfill({json:{trade_ids:['mock-trade']}});}
  if(path==='bond-redemptions/book'){
   if(uncertain&&requests.filter(r=>r.path===path).length===1)return route.fulfill({status:503,json:{detail:'Outcome unknown; retry unchanged.'}});
   if(rejectRetry&&requests.filter(r=>r.path===path).length===2)return route.fulfill({status:403,json:{detail:'Current permission check rejected this retry.'}});
   booked=true;return route.fulfill({json:{trade_ids:['closing-trade']}});
  }
  if(path==='bond-redemptions')return route.fulfill({json:{items:prepared?[{proposal_id:'proposal',instrument_id:instrument,input_hash:'a'.repeat(64),prepared_by:'operator',inputs,recorded_at:'2026-11-10T12:00:00Z',status:'PREPARED'}]:[],total:prepared?1:0}});
  return route.fulfill({json:{items:correction&&path.endsWith('/postings')?[{posting_id:'mock-posting',trade_ids:['mock-trade'],tradeStates:{'mock-trade':'BOOKED'},evidence:{operation:'BOOK'},recorded_at:'2026-11-05T12:00:00Z'}]:[],total:correction&&path.endsWith('/postings')?1:historyPaging&&path.endsWith('/postings')?26:0}});
 });
 await page.goto('/?mode=lifecycle-worklist');
 await expect(page.getByRole('button',{name:/Review closing entry for/})).toBeVisible();
 await page.getByRole('combobox',{name:'Strategy',exact:true}).selectOption(strategy);
 await page.getByRole('searchbox',{name:'Search instrument',exact:true}).fill('Gilt');
 await page.getByRole('button',{name:'Apply filters',exact:true}).click();
 await page.getByRole('button',{name:/Review closing entry for/}).click();
 const panel=page.getByRole('dialog',{name:'Review closing entry',exact:true});
 await expect(panel).toBeVisible();expect(requests.filter(r=>r.method==='POST')).toHaveLength(0);
 await panel.getByRole('button',{name:'Load closing inputs',exact:true}).click();
 await expect(panel.getByRole('heading',{name:'Maturity · 2026-11-05'})).toBeVisible();
 return {panel,requests};
}
test('prepares in the drawer and refreshes the row without losing filters or focus',async({page})=>{
 const {panel,requests}=await setup(page);
 await page.screenshot({path:'test-results/lifecycle-action-panel-desktop.png'});
 await expect(panel.getByRole('link',{name:'Open full workspace'})).toHaveAttribute('href',`/trades/lifecycle?strategyId=${strategy}&instrumentId=${instrument}`);
 await panel.getByRole('button',{name:'Prepare for approval',exact:true}).click();
 await expect(panel.getByRole('status')).toContainText('Prepared for independent approval');
 await expect(page.getByRole('region',{name:'Lifecycle event report'})).toContainText('Prepared');
 await expect(panel).toBeVisible();
 expect(requests.filter(r=>r.path==='bond-redemptions').every(r=>r.url.searchParams.get('instrumentId')===instrument)).toBe(true);
 expect(requests.filter(r=>r.path==='bond-redemptions/postings').every(r=>r.url.searchParams.get('instrumentId')===instrument)).toBe(true);
 await panel.getByRole('button',{name:'Close closing entry'}).click();
 await expect(panel).toHaveCount(0);
 await expect(page.getByRole('searchbox',{name:'Search instrument',exact:true})).toHaveValue('Gilt');
 await expect(page.getByRole('combobox',{name:'Strategy',exact:true})).toHaveValue(strategy);
 await expect(page.getByRole('button',{name:/Review closing entry for/})).toBeFocused();
 expect(requests.filter(r=>r.path.endsWith('/prepare'))).toHaveLength(1);
});
test('protects edits and retains an unchanged request key after an uncertain booking',async({page})=>{
 const {panel,requests}=await setup(page,{direct:true,uncertain:true,rejectRetry:true,historyPaging:true});
 await panel.getByRole('textbox',{name:'Desk note (optional)'}).fill('Keep this draft');
 await panel.getByRole('button',{name:'Next',exact:true}).click();
 await expect(panel.getByRole('textbox',{name:'Desk note (optional)'})).toHaveValue('Keep this draft');
 await expect(panel.getByRole('combobox',{name:'Bond',exact:true})).toHaveCount(0);
 await expect(panel.getByRole('heading',{name:'Treasury Gilt',exact:true})).toBeVisible();
 await panel.getByRole('button',{name:'Close closing entry'}).click();
 await expect(panel.getByText('Discard unsaved changes?')).toBeVisible();
 await panel.getByRole('button',{name:'Keep editing'}).click();
 await expect(panel.getByRole('textbox',{name:'Desk note (optional)'})).toHaveValue('Keep this draft');
 await panel.getByRole('button',{name:'Validate allocation inputs'}).click();
 await panel.getByRole('button',{name:'Book now',exact:true}).click();
 await expect(panel.getByRole('alert').filter({hasText:'Outcome unknown'})).toBeVisible();
 await panel.getByRole('button',{name:'Close closing entry'}).click();
 await expect(panel.getByText(/Resolve the uncertain booking/)).toBeVisible();
 await panel.getByRole('button',{name:'Book now',exact:true}).click();
 await expect(panel.getByRole('alert').filter({hasText:'Current permission check'})).toBeVisible();
 await panel.getByRole('button',{name:'Close closing entry'}).click();
 await expect(panel.getByText(/Resolve the uncertain booking/)).toBeVisible();
 await panel.getByRole('button',{name:'Book now',exact:true}).click();
 await expect(panel.getByRole('status')).toContainText('Recorded 1');
 const bookings=requests.filter(r=>r.path==='bond-redemptions/book');expect(bookings).toHaveLength(3);expect(bookings[0].key).toBeTruthy();expect(bookings[0].key).toBe(bookings[1].key);expect(bookings[0].body).toEqual(bookings[1].body);expect(bookings[2].key).toBe(bookings[0].key);expect(bookings[2].body).toEqual(bookings[0].body);
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:'test-results/lifecycle-action-panel-mobile.png'});
});


test('latest history page wins when reads arrive out of order',async({page})=>{
 const {panel}=await setup(page,{historyPaging:true});
 let release:()=>void=()=>{};const held=new Promise<void>(resolve=>{release=resolve;});
 await page.route('**/api/lifecycle/bond-redemptions/postings?**',async route=>{
  const offset=new URL(route.request().url()).searchParams.get('offset');
  if(offset==='25')await held;
  await route.fulfill({json:{items:[{posting_id:'history-'+offset,trade_ids:[],tradeStates:{},evidence:{operation:'CANCEL'},recorded_at:offset==='25'?'Old second page':'Current first page'}],total:26}});
 });
 await panel.getByRole('button',{name:'Next',exact:true}).click();
 await panel.getByRole('button',{name:'Previous',exact:true}).click();
 await expect(panel.getByText(/Current first page/)).toBeVisible();
 const oldResponse=page.waitForResponse(response=>response.url().includes('postings?')&&new URL(response.url()).searchParams.get('offset')==='25');
 release();await oldResponse;
 await expect(panel.getByText(/Old second page/)).toHaveCount(0);
 await expect(panel.getByText(/Current first page/)).toBeVisible();
});


test('strict rendering starts only one expensive worklist read',async({page})=>{
 let reads=0;
 await page.route('**/api/lifecycle/**',route=>{
  const url=new URL(route.request().url());
  if(url.pathname.endsWith('/options'))return route.fulfill({json:{items:[],total:0}});
  reads++;
  return route.fulfill({json:{items:[],total:0,offset:0,limit:25,evaluatedAt:'2026-11-11T12:00:00Z',fromDate:'2026-10-01',toDate:'2026-12-01',statusCounts:{},unavailableReason:'Synthetic empty scope'}});
 });
 await page.goto('/?mode=lifecycle-worklist-strict');
 await expect(page.getByRole('region',{name:'Lifecycle event report'})).toContainText('Synthetic empty scope');
 expect(reads).toBe(1);
});


test('uncertain cancellation preserves its reason and original request identity',async({page})=>{
 const {panel,requests}=await setup(page,{correction:true});
 await panel.getByRole('button',{name:'Cancel erroneous redemption',exact:true}).click();
 const reason=panel.getByRole('textbox',{name:'Correction reason',exact:true});
 await reason.fill('Synthetic erroneous entry');
 await panel.getByRole('checkbox',{name:/Cancel this erroneous record/}).check();
 await panel.getByRole('button',{name:'Record cancellation',exact:true}).click();
 await expect(panel.getByRole('alert').filter({hasText:'Outcome unknown'})).toBeVisible();
 await expect(reason).toHaveJSProperty('readOnly',true);
 await expect(panel.getByRole('button',{name:'Keep entry',exact:true})).toBeDisabled();
 await panel.getByRole('button',{name:'Record cancellation',exact:true}).click();
 await expect(panel.getByRole('status').filter({hasText:'Recorded 1'})).toBeVisible();
 const writes=requests.filter(r=>r.path==='bond-redemptions/cancel');expect(writes).toHaveLength(2);expect(writes[0].body.reason).toBe('Synthetic erroneous entry');expect(writes[1].body).toEqual(writes[0].body);expect(writes[1].key).toBe(writes[0].key);
});
