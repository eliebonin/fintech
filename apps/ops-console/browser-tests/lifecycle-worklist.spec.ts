import {test,expect} from './console-check';
const strategy='00000000-0000-7000-8000-000000000555',instrument='00000000-0000-7000-8000-000000000556';
const subscription={tenantId:'synthetic-tenant',maximumTier:3,configuredMaximumTier:3,revision:1,source:'MANUAL',moduleActive:true,notificationDiscoveryAvailable:true,entitlementFingerprint:'e'.repeat(64)};
const rows=Array.from({length:31},(_,index)=>({eventKey:`event-${index}`,eventType:'BOND_MATURITY',instrumentType:'BOND',strategyId:strategy,strategyName:'GBP Income',instrumentId:instrument,instrumentName:`Treasury Gilt ${String(index+1).padStart(2,'0')}`,identifier:'GB00TEST',maturityDate:'2026-11-05',status:index===0?'BLOCKED':'OVERDUE',attention:'ACTIONABLE',quantities:index===0?[]:[{currency:'GBP',unit:'NOMINAL',netQuantity:'100000.000000000000',grossQuantity:'100000.000000000000',entries:1}],remainingEntries:index===0?null:1,selectedTier:3,maximumTier:3,processingMode:'DIRECT',reasons:index===0?['Position could not be assessed: original evidence is missing.']:['Current source validation occurs in the booking workspace.'],actionLabel:'Open one-click workflow',actionHref:`/trades/lifecycle?strategyId=${strategy}&instrumentId=${instrument}`,positionAssessed:index!==0}));

test('worklist applies server filters, paginates full counts and preserves contextual inspection',async({page})=>{
 const reads:URL[]=[];const writes:string[]=[];
 await page.route('**/api/lifecycle/**',route=>{
  const request=route.request(),url=new URL(request.url());
  if(request.method()!=='GET'){writes.push(request.url());return route.fulfill({status:400,json:{detail:'Read-only journey'}});}
  if(url.pathname.endsWith('/worklist/options'))return route.fulfill({json:{items:[{strategyId:strategy,label:'GBP Income'}],total:1,offset:0,limit:25}});
  if(url.pathname.endsWith('/options'))return route.fulfill({json:{strategies:[{id:strategy,label:'GBP Income'}],instruments:[{id:instrument,label:'Treasury Gilt'}],policy:{mode:'DIRECT',revision:1},permissions:{LIFECYCLE_READ:true},assistance:{selectedTier:3,maximumTier:3,processingMode:'DIRECT',operations:{PREVIEW:{allowed:true,reasons:[]}}}}});
  if(!url.pathname.includes('/worklist'))return route.fulfill({json:{items:[],total:0}});
  reads.push(url);const offset=Number(url.searchParams.get('offset')??0),limit=Number(url.searchParams.get('limit')??25);const matches=url.searchParams.get('q')?rows.filter(row=>row.instrumentName.includes(url.searchParams.get('q')!)):rows;
  return route.fulfill({json:{items:matches.slice(offset,offset+limit),total:matches.length,offset,limit,evaluatedAt:'2026-11-05T10:00:00Z',fromDate:url.searchParams.get('fromDate'),toDate:url.searchParams.get('toDate'),statusCounts:{BLOCKED:1,OVERDUE:30},subscription,discoveryEventTypes:['BOND_MATURITY'],instrumentDisplays:{},unavailableReason:null}});
 });
 await page.goto('/?mode=lifecycle-worklist');
 await expect(page.getByRole('table',{name:'Lifecycle events · 31 matching'})).toBeVisible();
 await expect(page.getByRole('row')).toHaveCount(26);
 await expect(page.getByRole('dialog',{name:'Review closing entry',exact:true})).toHaveCount(0);
 await expect(page.getByRole('region',{name:'Lifecycle event report'}).getByText('Not assessed',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Review closing entry for Treasury Gilt 01 in GBP Income',exact:true}).click();
 const panel=page.getByRole('dialog',{name:'Review closing entry',exact:true});
 await expect(panel.getByRole('heading',{name:'Review closing entry',exact:true})).toBeFocused();
 await panel.getByText('Event context and evidence',{exact:true}).click();
 await expect(panel).toContainText('original evidence is missing');
 await expect(panel.getByRole('link',{name:'Open full workspace'})).toHaveAttribute('href',`/trades/lifecycle?strategyId=${strategy}&instrumentId=${instrument}`);
 await page.getByRole('button',{name:'Close closing entry'}).click();
 await expect(page.getByRole('button',{name:'Review closing entry for Treasury Gilt 01 in GBP Income',exact:true})).toBeFocused();
 await page.getByRole('combobox',{name:'Strategy',exact:true}).selectOption(strategy);
 await page.getByRole('combobox',{name:'Event relevance',exact:true}).selectOption('ACTIONABLE');
 await page.getByLabel('From date',{exact:true}).fill('2026-11-01');
 await expect(page.getByRole('region',{name:'Lifecycle event report'})).toContainText('2026-10-01 to 2026-12-01');
 await page.getByRole('button',{name:'Apply filters',exact:true}).click();
 await expect(page.getByRole('region',{name:'Lifecycle event report'})).toContainText('GBP Income · 2026-11-01 to 2026-12-01');
 expect(reads.at(-1)?.searchParams.get('strategyId')).toBe(strategy);expect(reads.at(-1)?.searchParams.get('attention')).toBe('ACTIONABLE');
 await page.getByRole('button',{name:'Next',exact:true}).click();await expect(page.getByText('26–31 of 31',{exact:true})).toBeVisible();expect(reads.at(-1)?.searchParams.get('offset')).toBe('25');
 await page.getByRole('combobox',{name:'Rows per page',exact:true}).selectOption('50');await expect(page.getByText('1–31 of 31',{exact:true})).toBeVisible();expect(reads.at(-1)?.searchParams.get('limit')).toBe('50');
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.getByRole('searchbox',{name:/Search instrument/}).fill('Gilt 31');
 await page.getByRole('button',{name:'Apply filters',exact:true}).click();
 await expect(page.getByRole('table',{name:'Lifecycle events · 1 matching'})).toContainText('Treasury Gilt 31');
 expect(reads.at(-1)?.searchParams.get('q')).toBe('Gilt 31');expect(reads.at(-1)?.searchParams.get('offset')).toBe('0');
 expect(writes).toEqual([]);
});

test('maturity handoff preselects authorised context without preparing or booking on load',async({page})=>{
 const writes:unknown[]=[];
 await page.route('**/api/lifecycle/**',route=>{
  const request=route.request(),url=new URL(request.url());
  if(request.method()!=='GET'){writes.push(request.postDataJSON());return route.fulfill({json:{inputHash:'a'.repeat(64),inputs:{valueDate:'2026-11-05',price:'100',mode:'DIRECT',movements:[{subjectId:instrument,quantity:'-100000.000000000000',cleanAmount:'100000',annotationFields:[]}]}}});}
  if(url.pathname.endsWith('/options'))return route.fulfill({json:{strategies:[{id:strategy,label:'GBP Income'}],instruments:[{id:instrument,label:'Treasury Gilt'}],policy:{mode:'DIRECT',revision:1},permissions:{LIFECYCLE_READ:true,LIFECYCLE_BOOK:true,TRADE_WRITE:true},assistance:{selectedTier:3,maximumTier:3,processingMode:'DIRECT',operations:{PREVIEW:{allowed:true,reasons:[]},PREPARE:{allowed:false,reasons:[]},DIRECT:{allowed:true,reasons:[]}}}}});
  return route.fulfill({json:{items:url.pathname.endsWith('/postings')?[{posting_id:'mock-posting',trade_ids:['mock-trade'],tradeStates:{'mock-trade':'BOOKED'},evidence:{operation:'BOOK'},recorded_at:'2026-11-01T12:00:00Z'}]:[],total:url.pathname.endsWith('/postings')?1:0}});
 });
 await page.goto('/?mode=lifecycle-context');
 await expect(page.getByRole('combobox',{name:'Strategy',exact:true})).toHaveValue(strategy);
 await expect(page.getByRole('combobox',{name:'Bond',exact:true})).toHaveValue(instrument);
 await expect(page.getByRole('button',{name:'Load closing inputs',exact:true})).toBeEnabled();
 expect(writes).toEqual([]);
 await page.getByRole('button',{name:'Load closing inputs',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Maturity · 2026-11-05'})).toBeVisible();
 expect(writes).toEqual([{strategyId:strategy,instrumentId:instrument}]);
 await expect(page.getByRole('region',{name:'Closing inputs',exact:true})).toContainText('100,000');
 await expect(page.getByRole('link',{name:'Open closing trade 1'})).toHaveAttribute('href','/trades/mock-trade');
 await expect(page.getByRole('button',{name:'Book now',exact:true})).toBeEnabled();
 for(const width of [1280,390]){
  await page.setViewportSize({width,height:950});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:`test-results/maturity-workspace-${width}.png`,fullPage:true});
 }
 expect(writes).toHaveLength(1);
});


test('changing processing mode refreshes assistance before exposing booking actions',async({page})=>{
 let mode='REVIEW';let policyWrites=0;let financialWrites=0;
 await page.route('**/api/lifecycle/**',route=>{
  const request=route.request(),url=new URL(request.url());
  if(url.pathname.endsWith('/policy')){policyWrites++;mode=request.postDataJSON().mode;return route.fulfill({json:{mode,revision:1}});}
  if(url.pathname.endsWith('/preview'))return route.fulfill({json:{inputHash:'a'.repeat(64),inputs:{valueDate:'2026-11-05',price:'100',mode,movements:[]}}});
  if(request.method()!=='GET'){financialWrites++;return route.fulfill({status:400,json:{detail:'No financial effect in this test'}});}
  if(url.pathname.endsWith('/options'))return route.fulfill({json:{strategies:[{id:strategy,label:'GBP Income'}],instruments:[{id:instrument,label:'Treasury Gilt'}],policy:{mode,revision:0},permissions:{LIFECYCLE_READ:true,LIFECYCLE_CONFIGURE:true,LIFECYCLE_BOOK:true,LIFECYCLE_PREPARE:true,TRADE_WRITE:true},assistance:{selectedTier:3,maximumTier:3,processingMode:mode,operations:{PREVIEW:{allowed:true,reasons:[]},PREPARE:{allowed:true,reasons:[]},DIRECT:{allowed:mode==='DIRECT',reasons:[]}}}}});
  return route.fulfill({json:{items:[],total:0}});
 });
 await page.goto('/?mode=lifecycle-context');
 await expect(page.getByRole('button',{name:'Load closing inputs'})).toBeEnabled();
 await page.getByText('Configure processing mode',{exact:true}).click();
 await page.getByRole('combobox',{name:'Mode',exact:true}).selectOption('DIRECT');
 await page.getByLabel('Change reason',{exact:true}).fill('Synthetic direct-control review');
 await page.getByRole('checkbox',{name:'Confirm this strategy’s processing control change'}).check();
 await page.getByRole('button',{name:'Save mode',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('Processing mode updated');
 await page.getByRole('button',{name:'Load closing inputs'}).click();
 await expect(page.getByRole('button',{name:'Book now',exact:true})).toBeVisible();
 expect(policyWrites).toBe(1);expect(financialWrites).toBe(0);
});
