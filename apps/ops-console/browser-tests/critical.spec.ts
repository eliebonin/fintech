import {test,expect} from './console-check';
const options={strategies:[{id:'strategy',label:'Synthetic strategy',canCalculate:true}],currencies:[{id:'gbp',label:'GBP'}],policies:[],accounts:[],bonds:[],permissions:{REFERENCE_APPROVE:true,LIFECYCLE_BOOK:true}};

test('paged choices retain an off-page selection and search the server beyond the first page',async({page})=>{
 await page.route('**/api/valuation/option-choices?**',r=>{
  const query=new URL(r.request().url()).searchParams,offset=Number(query.get('offset')??0);
  const selected={id:'item-500',label:'Beyond first page',canCalculate:false};
  const items=query.get('q')?[selected]:Array.from({length:25},(_,n)=>({id:`item-${offset+n}`,label:`Strategy ${offset+n}`,canCalculate:false}));
  return r.fulfill({json:{items,total:query.get('q')?1:501,limit:25,offset,selected}});
 });
 await page.goto('/?mode=choice');
 const select=page.getByRole('combobox',{name:'Strategy',exact:true});
 await expect(select).toHaveValue('item-500');await expect(select.locator('option:checked')).toHaveText('Beyond first page');
 await page.getByRole('button',{name:'Load more strategy'}).click();
 await expect(page.getByText('501 matching · 50 loaded')).toBeVisible();
 await page.getByRole('searchbox',{name:'Search strategy'}).fill('Beyond');
 await expect(page.getByText('1 matching · 1 loaded')).toBeVisible();
 await expect(select).toHaveValue('item-500');await expect(select.locator('option')).toHaveCount(2);
});
test('display currency changes reuse authorized values without another data request',async({page})=>{
 let requests=0;page.on('request',r=>{if(r.url().includes('/api/'))requests++;});
 await page.goto('/?mode=display');await page.getByRole('combobox',{name:'Display amounts'}).selectOption('strategy');
 await expect(page.getByText(/100(?:\.00)? USD/)).toHaveCount(0);await expect(page.getByText(/80(?:\.00)? GBP/)).toBeVisible();expect(requests).toBe(0);
 await page.getByRole('combobox',{name:'Display amounts'}).selectOption('local');await expect(page.getByText(/100(?:\.00)? USD/)).toBeVisible();expect(requests).toBe(0);
});
test.beforeEach(async({page})=>{await page.route('**/api/**',r=>r.fulfill({json:{items:[],total:0}}));});
test('unknown requests warn before closing and retain the retry when closure is cancelled',async({page})=>{
 await page.route('**/api/mock-booking',r=>r.fulfill({status:503,json:{}}));await page.goto('/');await page.getByLabel('Quantity').fill('10');await page.getByRole('button').click();await expect(page.getByRole('status')).toHaveText('Outcome unknown');
 const dialog=page.waitForEvent('dialog');await page.close({runBeforeUnload:true});const warning=await dialog;expect(warning.type()).toBe('beforeunload');await warning.dismiss();expect(page.isClosed()).toBe(false);
 await expect(page.getByRole('status')).toHaveText('Outcome unknown');
});
for(const strict of [false,true])test(`actual valuation ticket selects a versioned policy, stages, inspects and explicitly publishes (strict accrual ${strict})`,async({page})=>{
 const request={strategy_id:'strategy',policy_id:'policy-v3',reporting_currency_id:'gbp',opening_cutoff:'2026-10-06T00:00:00Z',closing_cutoff:'2026-10-07T00:00:00Z'};
 const batch={batch_id:'synthetic-batch',status:'STAGED',staged_by:'maker',reviews:[],summary:{scope:'MARKET_ONLY',resultFormat:'POSITION_V2',request,marketPnl:'1',openingValue:'1',closingValue:'2',executionValue:'0',reportingCurrencyId:'gbp',externalComparison:'NOT_COMPARED',limitations:[],accrualCoverage:{mode:strict?'REQUIRED':'OPTIONAL',suppliedCount:strict?1:0,missingCount:strict?0:1,missing:strict?[]:[{instrumentId:'bond',valueDate:'2026-10-07'}]}},items:[]};
 const posts:string[]=[];
 await page.route('**/api/valuation/options',r=>r.fulfill({json:{...options,policies:[{id:'policy-v3',label:'Synthetic EOD · v3',cutId:'cut'}]}}));
 await page.route('**/api/valuation/option-choices?**',r=>{
  const query=new URL(r.request().url()).searchParams;
  const items=query.get('kind')==='policies'?[{id:'policy-v3',label:'Synthetic EOD · v3',cutId:'cut'}]:query.get('kind')==='currencies'?options.currencies:options.strategies;
  return r.fulfill({json:{items,total:items.length,limit:25,offset:0,selected:items.find(item=>item.id===query.get('selected_id'))??null}});
 });
 await page.route('**/api/valuation/attempts',async r=>{posts.push('calculate');expect(r.request().postDataJSON().policyId).toBe('policy-v3');expect(r.request().postDataJSON().requireCompleteAccruals).toBe(strict?true:undefined);await r.fulfill({json:{attempt:{attempt_id:'attempt',status:'COMPLETED',started_at:'2026-10-08T12:00:00Z',correlation_id:'synthetic',request_payload:request},events:[],batch}});});
 await page.route('**/api/valuation/batches/synthetic-batch/publish',async r=>{posts.push('publish');expect(r.request().postDataJSON().comment).toBe('Synthetic independent review');await r.fulfill({json:{...batch,status:'PUBLISHED'}});});
 await page.goto('/?mode=valuation');const input=page.getByRole('tabpanel',{name:'Input form'});
 await input.getByRole('combobox',{name:'Strategy',exact:true}).selectOption('strategy');await input.getByRole('combobox',{name:'Pricing policy'}).selectOption('policy-v3');
 await input.getByRole('combobox',{name:'Reporting currency',exact:true}).selectOption('gbp');
 await input.getByLabel('Opening valuation date').fill('2026-10-06');await input.getByLabel('Closing valuation date').fill('2026-10-07');
 const coverage=input.getByRole('checkbox',{name:'Require complete daily accrual coverage'});
 await expect(coverage).not.toBeChecked();if(strict)await coverage.check();
 await expect.poll(()=>input.locator('form').first().evaluate(form=>(form as HTMLFormElement).checkValidity())).toBe(true);
 await input.getByRole('button',{name:'Calculate and stage',exact:true}).click();await expect(page.getByRole('tab',{name:'Results',exact:true})).toHaveAttribute('aria-selected','true');
 if(strict)await expect(page.getByText('Accrual not supplied—not included.',{exact:true})).toHaveCount(0);
 else {await expect(page.getByText('Inputs to review',{exact:true})).toBeVisible();await page.getByText('Inputs to review',{exact:true}).click();await expect(page.getByText('1 daily-interest / FX input not included.',{exact:true})).toBeVisible();await page.getByText('Missing dates and scopes',{exact:true}).click();await expect(page.getByRole('link',{name:'Instrument',exact:true})).toHaveAttribute('href','/instruments/bond');}
 await expect(page.getByText('Completed · Staged — not published',{exact:true})).toBeVisible();await page.getByRole('button',{name:'Publish valuation',exact:true}).click();
 await page.getByRole('button',{name:'Confirm publication',exact:true}).click();expect(posts).toEqual(['calculate']);
 await page.getByRole('textbox',{name:'Review decision'}).fill('Synthetic independent review');await page.getByRole('button',{name:'Confirm publication',exact:true}).click();
 await expect(page.getByText('Completed · Published',{exact:true})).toBeVisible();expect(posts).toEqual(['calculate','publish']);
});
test('twenty visible positions request their authorized labels in one bounded call',async({page})=>{
 const urls:string[]=[];
 await page.route('**/api/market-data/references?**',async r=>{urls.push(r.request().url());const ids=new URL(r.request().url()).searchParams.get('ids')?.split(',')??[];await r.fulfill({json:{labels:Object.fromEntries(ids.map((id,i)=>[id,`Synthetic name ${i+1}`]))}});});
 await page.goto('/?mode=labels');await expect(page.getByRole('link',{name:'Synthetic name 1',exact:true})).toBeVisible();expect(urls).toHaveLength(1);expect(new URL(urls[0]).searchParams.get('ids')?.split(',')).toHaveLength(20);
});

test('all position rows retain authorized labels through batches of at most twenty IDs',async({page})=>{
 const requests:string[][]=[];
 await page.route('**/api/market-data/references?**',async route=>{
  const ids=new URL(route.request().url()).searchParams.get('ids')?.split(',')??[];requests.push(ids);
  if(ids.length>20)return route.fulfill({status:400,json:{error:{code:'INVALID_REFERENCE_IDS'}}});
  return route.fulfill({json:{labels:Object.fromEntries(ids.map(id=>[id,`Synthetic ${id.slice(-12)}`]))}});
 });
 await page.goto('/?mode=labels&many=true');
 await page.getByRole('combobox',{name:'Positions per page',exact:true}).selectOption('all');
 await expect(page.getByRole('table',{name:'Position attribution',exact:true}).locator('tbody tr')).toHaveCount(127);
 await expect(page.getByRole('link',{name:/^Synthetic /})).toHaveCount(127);
 expect(requests.every(ids=>ids.length>0&&ids.length<=20)).toBe(true);
 expect(new Set(requests.flat()).size).toBe(127);
});
test('cash loading and failures never claim an empty register',async({page})=>{
 await page.route('**/api/valuation/options',r=>r.fulfill({json:options}));
 await page.route('**/api/valuation/cash-options',r=>r.fulfill({json:{companies:[]}}));
 let release!:()=>void;const gate=new Promise<void>(resolve=>release=resolve);
 await page.route('**/api/valuation/cash-balances?**',async r=>{await gate;await r.fulfill({status:503,json:{error:{message:'Synthetic unavailable'}}});});
 await page.route('**/api/valuation/cash-accounts?**',r=>r.fulfill({json:{items:[]}}));
 await page.goto('/?mode=cash');await page.getByRole('combobox',{name:'Strategy',exact:true}).selectOption('strategy');
 await expect(page.getByText('Loading balance register…')).toBeVisible();await expect(page.getByText(/No balances uploaded/)).toHaveCount(0);
 release();await expect(page.getByText(/Balance register unavailable/)).toBeVisible();await expect(page.getByRole('button',{name:'Save balance',exact:true})).toHaveCount(0);
});
test('coupon reads show pending rather than zero confirmations, then loaded empty',async({page})=>{
 await page.route('**/api/lifecycle/coupons/options*',r=>r.fulfill({json:options}));
 let release!:()=>void;const gate=new Promise<void>(resolve=>release=resolve);
 await page.route('**/api/lifecycle/coupons/payments?**',async r=>{await gate;await r.fulfill({json:{items:[],total:0}});});
 await page.goto('/?mode=coupon');await page.getByRole('combobox',{name:'Strategy',exact:true}).selectOption('strategy');
 await expect(page.getByText('Loading payment confirmations…')).toBeVisible();await expect(page.getByText(/0 latest payment/)).toHaveCount(0);
 release();await expect(page.getByText(/0 latest payment/)).toBeVisible();
});
test('a saved command with failed refresh locks further writes and recovers by GET',async({page})=>{
 let writes=0,reads=0;
 await page.route('**/api/access/users',async r=>{writes++;await r.fulfill({json:{ok:true}});});
 await page.route('**/api/access',async r=>{reads++;await r.fulfill(reads===1?{status:503,json:{error:{message:'Offline'}}}:{json:{name:'Refreshed'}});});
 await page.goto('/?mode=access');await page.getByRole('button',{name:'Save user'}).click();
 await expect(page.getByRole('alert')).toContainText('Change saved');await expect(page.getByRole('button',{name:'Save user'})).toBeDisabled();
 await page.getByRole('button',{name:'Refresh current state'}).click();await expect(page.getByRole('heading')).toHaveText('Refreshed');expect(writes).toBe(1);expect(reads).toBe(2);
});
test('native validation and uncertain retry retain one intent and send the page stamp',async({page})=>{
 const calls:{key:string|null;body:string|null;context:string|null}[]=[];
 await page.route('**/api/mock-booking',async r=>{calls.push({key:r.request().headers()['idempotency-key'],body:r.request().postData(),context:r.request().headers()['x-page-context']});await r.fulfill(calls.length===1?{status:503,json:{}}:{json:{ok:true}});});
 await page.goto('/');await page.getByRole('button').click();expect(calls).toHaveLength(0);
 await page.getByLabel('Quantity').fill('0.00000001');await page.getByRole('button').click();await expect(page.getByRole('status')).toHaveText('Outcome unknown');
 await page.getByLabel('Quantity').fill('10');await page.getByRole('button').click();await expect(page.getByRole('status')).toContainText('Retry the unchanged request');expect(calls).toHaveLength(1);
 await page.getByLabel('Quantity').fill('0.00000001');await page.getByRole('button').click();await expect(page.getByRole('status')).toHaveText('Booked');expect(calls[1]).toEqual(calls[0]);expect(calls[0].context).toBe('synthetic-old-context');
});
test('correction navigation reveals its hidden disclosure and focuses the destination on mobile',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/?mode=navigation');await page.getByRole('button').focus();await page.keyboard.press('Enter');
 await expect(page.locator('#valuation-input-register')).toBeVisible();await expect(page.locator('#valuation-input-register')).toBeFocused();
});
