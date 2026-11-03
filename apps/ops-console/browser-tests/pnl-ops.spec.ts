import {test,expect,type Page} from './console-check';
import type {Batch} from '../src/features/valuation/types';

const request={strategy_id:'strategy',policy_id:'policy',reporting_currency_id:'gbp',opening_cutoff:'2026-10-19T23:59:59Z',closing_cutoff:'2026-10-20T23:59:59Z'};

test('busy submission is explicit and manual retry preserves the request key and inputs',async({page})=>{
 const posts:Array<{key:string|undefined;body:unknown}>=[];
 const options={strategies:[{id:'strategy',label:'Example strategy',currencyId:'gbp',canCalculate:true}],
  policies:[{id:'policy',label:'Daily EOD',cutId:'cut'}],currencies:[{id:'gbp',label:'GBP'}]};
 await page.route('**/api/**',route=>route.fulfill({json:{items:[],total:0}}));
 await page.route('**/api/valuation/options',route=>route.fulfill({json:options}));
 await page.route('**/api/valuation/option-choices?**',route=>{const kind=new URL(route.request().url()).searchParams.get('kind') as keyof typeof options;return route.fulfill({json:{items:options[kind]??[],selected:null,total:options[kind]?.length??0,limit:25,offset:0}});});
 await page.route('**/api/valuation/attempts',route=>{
  if(route.request().method()!=='POST')return route.fulfill({json:{items:[],total:0}});
  posts.push({key:route.request().headers()['idempotency-key'],body:route.request().postDataJSON()});
  return route.fulfill({status:429,headers:{'Retry-After':'5'},json:{code:'workload.busy',detail:'This submission was not started. Retry unchanged after 5 seconds.',notStarted:true,retryable:true,retryAfterSeconds:5}});
 });
 await page.goto('/?mode=valuation');
 const panel=page.getByRole('tabpanel',{name:'Input form',exact:true});
 await panel.getByRole('combobox',{name:'Strategy',exact:true}).selectOption('strategy');
 await panel.getByRole('combobox',{name:'Pricing policy',exact:true}).selectOption('policy');
 await panel.getByRole('combobox',{name:'Reporting currency',exact:true}).selectOption('gbp');
 await panel.getByLabel('Opening valuation date').fill('2026-10-19');
 await panel.getByLabel('Closing valuation date').fill('2026-10-20');
 await expect.poll(()=>panel.locator('form').first().evaluate(form=>Array.from(form.querySelectorAll<HTMLInputElement|HTMLSelectElement>('input,select')).filter(input=>!input.checkValidity()).map(input=>({name:input.name,message:input.validationMessage})))).toEqual([]);
 await panel.getByRole('button',{name:'Calculate and stage',exact:true}).click();
 await expect(panel.getByText('This submission was not started. Check History for any earlier submission before retrying unchanged or changing the request.',{exact:true})).toBeVisible();
 expect(posts).toHaveLength(1);
 await panel.getByRole('button',{name:'Retry unchanged',exact:true}).click();
 await expect.poll(()=>posts.length).toBe(2);
 expect(posts[1]).toEqual(posts[0]);expect(posts[0].key).toBeTruthy();
});
function fixture():Batch{
 const items=Array.from({length:27},(_,i)=>({attribution_id:`a${i}`,trade_id:null,position_key:`p${i}`,subject_id:`s${i}`,version:1,market_pnl:'10',net_pnl:'11.25',
  display:{interest:'1.25',other:null,attention:i===26?['Interest not supplied']:[]},components:{PRICE:'8',FX:'1',PRICE_FX_CROSS:'1',ACCRUAL:'1.25'},
  evidence:{identity:{openingCutoff:request.opening_cutoff,closingCutoff:request.closing_cutoff,bucket:{opening_quantity:'100',closing_quantity:'125',key:{currency_id:'gbp',quantity_unit:'SHARES',unit_multiplier:'1',quote_factor:'1'}}},
   selections:[{valuation_date:'2026-10-20',selected_value:'105.123456789012',pricing_date_requested:'2026-10-20',pricing_date_used:'2026-10-20',dataset_id:'dataset',policy_rule_id:'rule',staleness_status:'FRESH',staleness_business_days:0,pricing_evidence:{}}]},lineage:[{trade_id:'original-trade',event_id:`event${i}`,role:'OPENING_EVIDENCE'}]}));
 return {batch_id:'batch',status:'STAGED',staged_by:'maker',sourceHealth:{status:'CURRENT',changes:[]},reviews:[],items,
  presentation:{references:Object.fromEntries(items.map((item,i)=>[item.subject_id,`Example instrument ${i} · CODE${i} · GBP`])),currencies:{gbp:'GBP'},datasets:{dataset:'Example provider · Daily closes'},rules:{rule:'EOD · v3 · Closing price'},users:{maker:'Ops maker'},context:{strategy:'Example strategy · OPS',policy:'Daily EOD · EOD · v3',currency:'GBP'},totals:{interest:'33.75',other:null},pendingAmendments:0,
   sourceCoverage:{basis:'STORED_REPORTING_CURRENCY_COMPONENTS',includedTotal:'303.75',recordedNet:'303.75',reconciliation:'MATCH',rows:[
    {code:'PRICE',label:'Price movements',description:'Investment price movement.',componentCodes:['PRICE'],amount:'216',status:'INCLUDED',positionCount:27,missingCount:0},
    {code:'FX',label:'Position FX movements',description:'Investment FX, not cash.',componentCodes:['FX'],amount:'27',status:'INCLUDED',positionCount:27,missingCount:0},
    {code:'PRICE_FX_CROSS',label:'Price × FX interaction',description:'Counted once.',componentCodes:['PRICE_FX_CROSS'],amount:'27',status:'INCLUDED',positionCount:27,missingCount:0},
    {code:'ACCRUAL',label:'Daily interest earned',description:'Daily added interest only.',componentCodes:['ACCRUAL'],amount:'33.75',status:'PARTIAL',positionCount:27,missingCount:1},
    {code:'RESET',label:'Resets',description:'Income-classified reset flows.',componentCodes:['RESET'],amount:null,status:'NOT_RECORDED',positionCount:0,missingCount:0},
    {code:'CASH_BALANCE_FX',label:'Cash-balance FX P&L',description:'Daily snapshot inputs not supplied.',componentCodes:['CASH_FX'],amount:null,status:'MISSING_INPUTS',positionCount:0,missingCount:1}
   ]}},
  summary:{scope:'SUPPORTED_ECONOMIC_ALPHA',resultFormat:'POSITION_V2',request,marketPnl:'270',grossPnl:'303.75',netPnl:'303.75',openingValue:'1000',closingValue:'1270',executionValue:'0',reportingCurrencyId:'gbp',externalComparison:'NOT_COMPARED',limitations:[],cashCoverage:{status:'MISSING_INPUTS',knownScopeCount:1,suppliedCount:0,missingCount:1,missing:[],scopes:[]},accrualCoverage:{mode:'OPTIONAL',missingCount:1,suppliedCount:27,missing:[{instrumentId:'s26',valueDate:'2026-10-20'}]}}};
}

test('Ops finds an off-page warning, inspects business labels and explicitly publishes a reviewed result',async({page})=>{
 const batch=fixture();const posts:string[]=[];const labelRequests:string[]=[];
 await page.route('**/api/**',r=>r.fulfill({json:{items:[],total:0}}));
 const options={strategies:[{id:'strategy',label:'Example strategy · OPS',canCalculate:true}],policies:[{id:'policy',label:'Daily EOD · EOD · v3',cutId:'cut'}],currencies:[{id:'gbp',label:'GBP'}]};
 await page.route('**/api/valuation/options',r=>r.fulfill({json:options}));
 await page.route('**/api/valuation/option-choices?**',r=>{const q=new URL(r.request().url()).searchParams;const items=q.get('kind')==='strategies'?options.strategies:q.get('kind')==='policies'?options.policies:options.currencies;return r.fulfill({json:{items,total:items.length,limit:25,offset:0,selected:items.find(item=>item.id===q.get('selected_id'))??null}});});
 await page.route('**/api/valuation/attempts?**',r=>r.fulfill({json:{items:[{attempt_id:'attempt',status:'COMPLETED',batch_status:'STAGED',request_payload:request,strategy_id:'strategy',started_at:'2026-10-21T08:00:00Z',valuation_date:'2026-10-20',financial_summary:{netPnl:'303.75',reportingCurrencyId:'gbp'}}],total:1}}));
 await page.route('**/api/valuation/attempts/attempt',r=>r.fulfill({json:{attempt:{attempt_id:'attempt',status:'COMPLETED',started_at:'2026-10-21T08:00:00Z',correlation_id:'correlation',request_payload:request},events:[],batch}}));
 await page.route('**/api/market-data/references?**',r=>{labelRequests.push(r.request().url());return r.fulfill({json:{labels:{}}});});
 await page.route('**/api/valuation/batches/batch/publish',r=>{posts.push('publish');expect(r.request().postDataJSON()).toEqual({comment:'Daily result and warnings reviewed'});return r.fulfill({json:{...batch,status:'PUBLISHED'}});});
 await page.goto('/?mode=valuation');await page.getByRole('tab',{name:'Results',exact:true}).click();
 const results=page.getByRole('tabpanel',{name:'Results',exact:true});
 await results.getByRole('combobox',{name:'Strategy',exact:true}).selectOption('strategy');
 await expect.poll(()=>results.locator('form').first().evaluate(form=>(form as HTMLFormElement).checkValidity())).toBe(true);
 await results.getByRole('button',{name:'Find results',exact:true}).click();await results.getByRole('button',{name:'Open result',exact:true}).click();
 await expect(results.getByRole('heading',{name:'Example strategy · OPS'})).toBeVisible();
 const coverage=results.getByRole('region',{name:'P&L sources and coverage'});
 await expect(coverage.getByText('Reconciles to recorded total',{exact:true})).toBeVisible();
 await expect(coverage.getByRole('table').getByText('Not supplied · Not included',{exact:true})).toBeVisible();
 await expect(coverage.getByText(/Missing snapshots are not zero and do not by themselves block publication/)).toBeVisible();
 await expect(coverage.getByRole('table').getByText('No recorded entries',{exact:true})).toBeVisible();
 await coverage.getByRole('button',{name:'Inspect positions: Daily interest earned',exact:true}).click();
 await expect(results.getByRole('heading',{name:'Position attribution',exact:true})).toBeFocused();
 await expect(results.getByText('Contributing source:',{exact:false})).toBeVisible();
 await results.getByRole('button',{name:'Show all sources',exact:true}).click();
 await results.getByRole('searchbox',{name:'Search positions'}).fill('CODE26');await results.getByRole('checkbox',{name:'Attention only'}).check();
 await expect(results.getByText('1 matching of 27.',{exact:false})).toBeVisible();
 await results.getByRole('button',{name:'Inspect position',exact:true}).click();
 await results.getByText('Sources, applied rules and technical proof',{exact:true}).click();
 await expect(results.getByText('Example provider · Daily closes',{exact:true})).toBeVisible();
 await expect(results.getByText('EOD · v3 · Closing price',{exact:true})).toBeVisible();
 await expect(results.getByRole('table',{name:'Frozen prices and FX · exact values'}).locator('td > strong',{hasText:'105.123456789012'})).toBeVisible();
 await results.getByText('Instrument ID',{exact:true}).click();
 await expect(results.getByRole('complementary',{name:'Position inspection'}).getByText('s26',{exact:true})).toBeVisible();
 const positions=results.getByRole('region',{name:'Position attribution',exact:true});
 const inspector=results.getByRole('complementary',{name:'Position inspection'});
 const inspect=positions.getByRole('button',{name:'Inspect position',exact:true});
 for(const width of [1800,1280,760]){
  await page.setViewportSize({width,height:1000});
  await inspect.click();
  await expect(inspect).toHaveAttribute('aria-expanded','true');
  await inspector.getByRole('button',{name:'Close position details',exact:true}).click();
  await expect(inspector).toBeHidden();
  await expect(inspect).toBeFocused();
  await expect(inspect).toHaveAttribute('aria-expanded','false');
  const tableBox=await positions.boundingBox();const gridBox=await results.locator('.pnl-result-grid').boundingBox();
  expect(tableBox).not.toBeNull();expect(gridBox).not.toBeNull();
  expect(Math.abs(tableBox!.width-gridBox!.width)).toBeLessThan(2);
  await expect(results.getByRole('searchbox',{name:'Search positions'})).toHaveValue('CODE26');
  await expect(results.getByRole('checkbox',{name:'Attention only'})).toBeChecked();
  await inspect.press('Enter');
  await expect(inspector).toBeVisible();
  await expect(inspector.getByRole('heading',{name:'Example instrument 26 · CODE26 · GBP',exact:true})).toBeVisible();
 }
 expect(labelRequests).toEqual([]);expect(posts).toEqual([]);
 await results.getByRole('button',{name:'Publish valuation',exact:true}).click();
 const confirmation=results.getByRole('form',{name:'Confirm valuation publication'});
 await expect(confirmation.getByText('303.75 GBP',{exact:true})).toBeVisible();
 await expect(confirmation.getByText(/Accrual not supplied/)).toBeVisible();
 await confirmation.getByRole('button',{name:'Confirm publication',exact:true}).click();expect(posts).toEqual([]);
 await confirmation.getByRole('textbox',{name:'Review decision'}).fill('Daily result and warnings reviewed');
 await confirmation.getByRole('button',{name:'Confirm publication',exact:true}).click();
 await expect(results.getByText('Completed · Published',{exact:true})).toBeVisible();expect(posts).toEqual(['publish']);
 await page.setViewportSize({width:760,height:1000});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:'test-results/pnl-ops-review.png',fullPage:true});
});

test('Ops automatically includes cash FX, inspects a separate account report and publishes with review',async({page})=>{
 const batch:Batch=fixture();
 batch.summary={...batch.summary,scope:'ECONOMIC_WITH_CASH_FX',netPnl:'1303.75',grossPnl:'1303.75',cashFxPnl:'1000',
  request,cashCoverage:{status:'INCLUDED',knownScopeCount:1,suppliedCount:1,missingCount:0,missing:[],scopes:[{accountId:'cash-account',currencyId:'usd'}]}};
 batch.items.push({attribution_id:'cash-line',trade_id:null,cash_account_id:'cash-account',cash_currency_id:'usd',version:1,
  market_pnl:'0',net_pnl:'1000',components:{CASH_FX:'1000'},evidence:{resultFormat:'CASH_FX_V1',cashFx:{days:[{
   value_date:'2026-10-20',opening:{cash_balance_id:'open-snapshot',balance_as_of_date:'2026-10-19',amount:'100000',revision:1,note:'Reviewed custody statement'},
   closing:{cash_balance_id:'close-snapshot',balance_as_of_date:'2026-10-20',amount:'120000',revision:1},opening_fx:'0.75',closing_fx:'0.76',amount:'1000',fx_mode:'POLICY_FX'}]},selections:[]}});
 const metadata=batch.presentation!;metadata.cashAccounts={'cash-account':'Northern Trust · Custody'};metadata.currencies.usd='USD';metadata.totals.other='1000';
 const coverage=metadata.sourceCoverage!;coverage.includedTotal=coverage.recordedNet='1303.75';
 coverage.rows=coverage.rows.filter(row=>row.code!=='CASH_BALANCE_FX').concat({code:'CASH_BALANCE_FX',label:'Cash-balance FX P&L',description:'Opening cash × daily FX change.',componentCodes:['CASH_FX'],amount:'1000',status:'INCLUDED',positionCount:0,cashAccountCount:1,missingCount:0});
 const options={strategies:[{id:'strategy',label:'Example strategy · OPS',canCalculate:true}],policies:[{id:'policy',label:'Daily EOD · EOD · v3',cutId:'cut'}],currencies:[{id:'gbp',label:'GBP'}]};
 await page.route('**/api/**',r=>r.fulfill({json:{items:[],total:0}}));
 await page.route('**/api/valuation/options',r=>r.fulfill({json:options}));
 await page.route('**/api/valuation/option-choices?**',r=>{const q=new URL(r.request().url()).searchParams;const items=q.get('kind')==='strategies'?options.strategies:q.get('kind')==='policies'?options.policies:options.currencies;return r.fulfill({json:{items,total:items.length,limit:25,offset:0,selected:items.find(item=>item.id===q.get('selected_id'))??null}});});
 const writes:string[]=[];
 await page.route('**/api/valuation/attempts',r=>{expect(r.request().postDataJSON()).not.toHaveProperty('includeCashBalances');writes.push('calculate');return r.fulfill({json:{attempt:{attempt_id:'attempt',status:'COMPLETED',started_at:'2026-10-21T08:00:00Z',correlation_id:'cash-synthetic',request_payload:batch.summary.request},events:[],batch}});});
 await page.route('**/api/valuation/batches/batch/publish',r=>{expect(r.request().postDataJSON()).toEqual({comment:'Cash inputs and opening convention reviewed'});writes.push('publish');return r.fulfill({json:{...batch,status:'PUBLISHED'}});});
 await page.goto('/?mode=valuation');const input=page.getByRole('tabpanel',{name:'Input form'});
 await input.getByRole('combobox',{name:'Strategy',exact:true}).selectOption('strategy');await input.getByRole('combobox',{name:'Pricing policy'}).selectOption('policy');await input.getByRole('combobox',{name:'Reporting currency',exact:true}).selectOption('gbp');
 await input.getByLabel('Opening valuation date').fill('2026-10-19');await input.getByLabel('Closing valuation date').fill('2026-10-20');
 await expect(input.getByRole('checkbox',{name:'Include cash-balance FX P&L'})).toHaveCount(0);
 await expect(input.getByText('Cash-balance FX P&L is always assessed.',{exact:true})).toBeVisible();
 await expect.poll(()=>input.locator('form').first().evaluate(form=>(form as HTMLFormElement).checkValidity())).toBe(true);
 await input.getByRole('button',{name:'Calculate and stage',exact:true}).click();
 const results=page.getByRole('tabpanel',{name:'Results',exact:true});
 await expect(results.locator('.pnl-cash-gap')).toHaveCount(0);
 await results.getByRole('button',{name:'Inspect cash accounts: Cash-balance FX P&L',exact:true}).click();
 await expect(results.getByRole('heading',{name:'Cash FX attribution',exact:true})).toBeFocused();
 const cash=results.getByRole('region',{name:'Cash FX attribution'});
 await cash.getByRole('button',{name:'Inspect cash inputs',exact:true}).click();
 await expect(cash.getByRole('heading',{name:'Northern Trust · Custody · USD',exact:true})).toBeFocused();
 await expect(cash.getByRole('table',{name:'Daily cash FX contributions · GBP'})).toContainText('100000');
 await expect(cash.getByRole('table',{name:'Daily cash FX contributions · GBP'})).toContainText('0.75 / 0.76');
 await expect(cash.getByText('Reviewed custody statement',{exact:true})).toBeVisible();
 await expect(results.getByRole('link',{name:'Instrument name unavailable',exact:true})).toHaveCount(0);
 await page.setViewportSize({width:760,height:1000});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:'test-results/cash-fx-review.png',fullPage:true});
 await results.getByRole('button',{name:'Publish valuation',exact:true}).click();
 await results.getByRole('textbox',{name:'Review decision'}).fill('Cash inputs and opening convention reviewed');await results.getByRole('button',{name:'Confirm publication',exact:true}).click();
 await expect(results.getByText('Completed · Published',{exact:true})).toBeVisible();expect(writes).toEqual(['calculate','publish']);
});

test('valuation options keep compact checkboxes beside readable labels and help on new and corrected tickets',async({page})=>{
 const batch=fixture();
 const options={strategies:[{id:'strategy',label:'Example strategy · OPS',canCalculate:true}],policies:[{id:'policy',label:'Daily EOD · EOD · v3',cutId:'cut'}],currencies:[{id:'gbp',label:'GBP'}]};
 await page.route('**/api/**',r=>r.fulfill({json:{items:[],total:0}}));
 await page.route('**/api/valuation/options',r=>r.fulfill({json:options}));
 await page.route('**/api/valuation/option-choices?**',r=>{const q=new URL(r.request().url()).searchParams;const items=q.get('kind')==='strategies'?options.strategies:q.get('kind')==='policies'?options.policies:options.currencies;return r.fulfill({json:{items,total:items.length,limit:25,offset:0,selected:items.find(item=>item.id===q.get('selected_id'))??null}});});
 await page.route('**/api/valuation/attempts?**',r=>r.fulfill({json:{items:[{attempt_id:'attempt',status:'COMPLETED',batch_status:'STAGED',request_payload:request,strategy_id:'strategy',started_at:'2026-10-21T08:00:00Z',valuation_date:'2026-10-20',financial_summary:{netPnl:'303.75',reportingCurrencyId:'gbp'}}],total:1}}));
 await page.route('**/api/valuation/attempts/attempt',r=>r.fulfill({json:{attempt:{attempt_id:'attempt',status:'COMPLETED',started_at:'2026-10-21T08:00:00Z',correlation_id:'synthetic',request_payload:request},events:[],batch}}));
 await page.goto('/?mode=valuation');
 const input=page.getByRole('tabpanel',{name:'Input form',exact:true});
 for(const corrected of [false,true]){
  if(corrected){
   await page.getByRole('tab',{name:'Results',exact:true}).click();const results=page.getByRole('tabpanel',{name:'Results',exact:true});
   await results.getByRole('combobox',{name:'Strategy',exact:true}).selectOption('strategy');
   await expect.poll(()=>results.locator('form').first().evaluate(form=>(form as HTMLFormElement).checkValidity())).toBe(true);
   await results.getByRole('button',{name:'Find results',exact:true}).click();await results.getByRole('button',{name:'Open result',exact:true}).click();
   await results.getByRole('tab',{name:'Review',exact:true}).click();
   await results.getByRole('button',{name:'Prepare corrected-input recalculation',exact:true}).click();
   await expect(input.getByRole('textbox',{name:'Recalculation reason',exact:true})).toBeVisible();
  }
  for(const width of [1400,900,480]){
   await page.setViewportSize({width,height:1000});
   await expect(input.getByRole('checkbox',{name:'Include cash-balance FX P&L'})).toHaveCount(0);
   for(const name of ['Require complete daily accrual coverage']){
    const checkbox=input.getByRole('checkbox',{name,exact:true});await expect(checkbox).toBeVisible();
    const layout=await checkbox.evaluate(element=>{
     const box=element as HTMLInputElement,label=box.labels![0],copy=label.querySelector('span')??label;
     const help=document.getElementById(box.getAttribute('aria-describedby')??'');
     const shape=(node:Element)=>{const r=node.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width};};
     return {box:shape(box),copy:shape(copy),help:help?shape(help):null,bounds:shape(box.closest('fieldset')!)};
    });
    expect(layout.box.width).toBeLessThanOrEqual(24);
    expect(layout.copy.x).toBeGreaterThanOrEqual(layout.box.right+4);
    expect(layout.copy.right).toBeLessThanOrEqual(layout.bounds.right+1);
    expect(layout.help).not.toBeNull();
    expect(layout.help!.y).toBeGreaterThanOrEqual(layout.copy.bottom);
    expect(layout.help!.right).toBeLessThanOrEqual(layout.bounds.right+1);
    const wasChecked=await checkbox.isChecked();await checkbox.click();await expect(checkbox).toBeChecked({checked:!wasChecked});
   }
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  }
  await page.setViewportSize({width:1400,height:1000});
  await input.screenshot({path:`test-results/valuation-options-${corrected?'correction':'new'}.png`});
 }
});

async function mockReport(page:Page,{failed=false,denied=false,batch=fixture()}={}){
 if(denied)batch.summary.evidenceAccess='DENIED';
 const attempt={attempt_id:'attempt',status:failed?'FAILED':'COMPLETED',batch_status:failed?null:'STAGED',started_at:'2026-10-21T08:00:00Z',correlation_id:'synthetic-report-correlation',request_payload:request,strategy_id:'strategy',valuation_date:'2026-10-20'};
 const detail={attempt,batch:failed?null:batch,events:[{event_id:'event',stage:'CALCULATION',event_code:failed?'FAILED':'COMPLETED',recorded_at:'2026-10-21T08:00:01Z',details:failed?{reason:'Input selection blocked: NO_ELIGIBLE_OBSERVATION',errorCode:'VALUATION_BLOCKED'}:{note:'Synthetic retained event'}}]};
 const options={strategies:[{id:'strategy',label:'Example strategy · OPS',canCalculate:true}],policies:[{id:'policy',label:'Daily EOD · EOD · v3',cutId:'cut'}],currencies:[{id:'gbp',label:'GBP'}]};
 const writes:string[]=[];let reads=0;
 await page.route('**/api/**',route=>{if(route.request().method()!=='GET')writes.push(route.request().url());return route.fulfill({json:{items:[],total:0}});});
 await page.route('**/api/valuation/options',route=>route.fulfill({json:options}));
 await page.route('**/api/valuation/option-choices?**',route=>{const query=new URL(route.request().url()).searchParams;const items=query.get('kind')==='strategies'?options.strategies:query.get('kind')==='policies'?options.policies:options.currencies;return route.fulfill({json:{items,total:items.length,limit:25,offset:0,selected:items.find(item=>item.id===query.get('selected_id'))??null}});});
 await page.route('**/api/valuation/attempts?**',route=>route.fulfill({json:{items:[attempt],total:1}}));
 await page.route('**/api/valuation/attempts/attempt',route=>{reads++;return route.fulfill({json:detail});});
 return {writes,reads:()=>reads};
}

test('source coverage expands every row and its total without internal vertical scrolling',async({page})=>{
 const batch=fixture();
 for(const row of batch.presentation!.sourceCoverage!.rows)row.description+=' Stored result components retain exact amounts, source evidence and coverage exceptions for operational review.'.repeat(3);
 const mock=await mockReport(page,{batch});
 await page.goto('/?mode=valuation#valuationRun=attempt&report=breakdown');
 const coverage=page.getByRole('region',{name:'P&L sources and coverage'});
 const table=coverage.getByRole('table',{name:'P&L sources · GBP',exact:true});
 await expect(table.locator('tbody tr')).toHaveCount(6);
 for(const width of [1280,760,480]){
  await page.setViewportSize({width,height:900});
  const layout=await table.evaluate(element=>{
   const wrapper=element.parentElement!,bounds=wrapper.getBoundingClientRect();
   return {tableHeight:element.getBoundingClientRect().height,hiddenHeight:wrapper.scrollHeight-wrapper.clientHeight,
    totalBottom:element.querySelector('tfoot')!.getBoundingClientRect().bottom,wrapperBottom:bounds.bottom};
  });
  expect(layout.tableHeight).toBeGreaterThan(560);
  expect(layout.hiddenHeight).toBeLessThanOrEqual(1);
  expect(layout.totalBottom).toBeLessThanOrEqual(layout.wrapperBottom+1);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 }
 expect(mock.writes).toEqual([]);
});

test('source coverage displays gains green, losses red and zero or missing amounts neutral',async({page})=>{
 const batch=fixture(),coverage=batch.presentation!.sourceCoverage!;
 ['12.50','-12.50','0',null,'-0.000001','0.000001'].forEach((amount,index)=>coverage.rows[index].amount=amount);
 coverage.includedTotal='-0.000001';
 const mock=await mockReport(page,{batch});
 await page.goto('/?mode=valuation#valuationRun=attempt&report=breakdown');
 const table=page.getByRole('table',{name:'P&L sources · GBP',exact:true});
 const amounts=table.locator('tbody .pnl-amount');
 for(const index of [0,5])await expect(amounts.nth(index)).toHaveCSS('color','rgb(22, 101, 52)');
 for(const index of [1,4])await expect(amounts.nth(index)).toHaveCSS('color','rgb(180, 35, 24)');
 for(const index of [2,3]){
  await expect(amounts.nth(index)).not.toHaveCSS('color','rgb(22, 101, 52)');
  await expect(amounts.nth(index)).not.toHaveCSS('color','rgb(180, 35, 24)');
 }
 await expect(table.locator('tfoot .pnl-amount')).toHaveCSS('color','rgb(180, 35, 24)');
 expect(mock.writes).toEqual([]);
});

test('position inspection leads with manually reproducible inputs and keeps technical proof collapsed and reachable',async({page})=>{
 const batch=fixture();batch.items=batch.items.slice(0,1);
 batch.items[0]={...batch.items[0],market_pnl:'422',net_pnl:'434.5',gross_pnl:'434.5',components:{PRICE:'337.5',FX:'80',PRICE_FX_CROSS:'4.5',ACCRUAL:'12.5'},display:{interest:'12.5',other:null,attention:[]},evidence:{
  identity:{openingCutoff:request.opening_cutoff,closingCutoff:request.closing_cutoff,reportingCurrency:'gbp',openingValue:'6000',closingValue:'7980',executionValue:'1558',
   bucket:{opening_quantity:'100000',closing_quantity:'125000',key:{subject_id:'s0',currency_id:'usd',quantity_unit:'SHARES',product_basis:'EQUITY',unit_multiplier:'1',quote_factor:'1'}}},
  selections:[{valuation_date:'2026-10-19',selected_value:'0.08',pricing_date_used:'2026-10-19'},
   {valuation_date:'2026-10-20',selected_value:'0.084',pricing_date_used:'2026-10-20',dataset_id:'dataset',policy_rule_id:'rule'},
   {input_role:'FX',valuation_date:'2026-10-19',valuation_source_currency_id:'usd',selected_value:'1.333333333333',pricing_date_used:'2026-10-19',conversion:{rate:'0.75',method:'RECIPROCAL',targetCurrencyId:'gbp'}},
   {input_role:'FX',valuation_date:'2026-10-20',valuation_source_currency_id:'usd',selected_value:'0.76',pricing_date_used:'2026-10-20',conversion:{rate:'0.76',method:'DIRECT',targetCurrencyId:'gbp'}}],
  executionInputs:[{event_id:'buy',effective_at:'2026-10-20T12:00:00Z',booking:{trade_id:'buy',quantity:'25000',price:'0.082',unit_multiplier:'1',quote_factor:'1'}}]}};
 batch.presentation!.currencies.usd='USD';batch.presentation!.totals.interest='12.5';
 batch.summary={...batch.summary,marketPnl:'422',grossPnl:'434.5',netPnl:'434.5',openingValue:'6000',closingValue:'7980',executionValue:'1558',accrualCoverage:{mode:'OPTIONAL',suppliedCount:1,missingCount:0,missing:[]}};
 const source=batch.presentation!.sourceCoverage!;source.includedTotal=source.recordedNet='434.5';
 for(const row of source.rows){if(row.code in batch.items[0].components){row.amount=batch.items[0].components[row.code];row.positionCount=1;row.missingCount=0;row.status='INCLUDED';}}
 const mock=await mockReport(page,{batch});
 await page.goto('/?mode=valuation#valuationRun=attempt&report=positions');await page.getByRole('button',{name:'Inspect position',exact:true}).click();
 const inspector=page.getByRole('complementary',{name:'Position inspection'}),manual=inspector.getByRole('region',{name:'Manual P&L check',exact:true});
 const proof=inspector.locator('details.pnl-inspector-proof');
 await expect(manual.getByRole('heading',{name:'Reproduce this P&L',exact:true})).toBeVisible();
 await expect(proof).not.toHaveAttribute('open','');
 const boundaries=manual.getByRole('table',{name:'Boundary prices and quantities',exact:true});
 await expect(boundaries.getByRole('row',{name:'Signed quantity 100,000 125,000',exact:true})).toBeVisible();
 for(const value of ['100,000','125,000'])await expect(boundaries.getByRole('row',{name:'Signed quantity 100,000 125,000',exact:true}).getByRole('cell',{name:value,exact:true})).toHaveCSS('text-align','right');
 await expect(boundaries.getByRole('row',{name:'FX · GBP per 1 USD 0.75 0.76',exact:true})).toBeVisible();
 await expect(manual.getByText('1,558',{exact:true})).toBeVisible();await expect(manual.getByText('422',{exact:true})).toBeVisible();
 const trades=manual.getByRole('table',{name:'Trades during the period · exact inputs',exact:true});
 await expect(trades.getByText('0.082',{exact:true})).toBeVisible();await expect(trades.getByText('25,000',{exact:true})).toBeVisible();
 const close=inspector.getByRole('button',{name:'Close position details',exact:true});
 await expect(close).toHaveText('×');await expect(close).toHaveCSS('background-color','rgb(255, 241, 242)');
 const businessTop=await manual.evaluate(element=>element.getBoundingClientRect().top),proofTop=await proof.evaluate(element=>element.getBoundingClientRect().top);expect(businessTop).toBeLessThan(proofTop);
 for(const width of [1280,760,480]){await page.setViewportSize({width,height:900});await expect(manual).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);}
 await page.setViewportSize({width:1280,height:1000});await inspector.screenshot({path:'test-results/position-manual-check.png'});
 await proof.locator('summary').first().focus();await page.keyboard.press('Enter');
 await expect(proof).toHaveAttribute('open','');await expect(proof.getByText('Example provider · Daily closes',{exact:true})).toBeVisible();
 await close.focus();await page.keyboard.press('Enter');await expect(inspector).toBeHidden();
 await expect(page.getByRole('button',{name:'Inspect position',exact:true})).toBeFocused();
 expect(mock.writes).toEqual([]);
});

test('position instrument types filter the full report before pagination and retain existing review controls',async({page})=>{
 const batch=fixture();
 batch.presentation!.instrumentTypes=Object.fromEntries(batch.items.slice(0,26).map((item,index)=>[item.subject_id!,
  index===25?{code:'BOND',label:'Bond'}:{code:'EQUITY',label:'Equity'}]));
 const mock=await mockReport(page,{batch});
 await page.goto('/?mode=valuation#valuationRun=attempt&report=positions');
 const positions=page.getByRole('region',{name:'Position attribution',exact:true});
 const table=positions.getByRole('table',{name:'Position attribution',exact:true}),rows=table.locator('tbody tr');
 const filter=positions.getByRole('combobox',{name:'Instrument type',exact:true});
 await expect(table.getByRole('columnheader',{name:'Instrument type',exact:true})).toBeVisible();
 await expect(rows).toHaveCount(25);await expect(rows.first().getByRole('cell',{name:'Equity',exact:true})).toBeVisible();
 await positions.getByRole('button',{name:'Next positions',exact:true}).click();
 await filter.selectOption('BOND');
 await expect(rows).toHaveCount(1);await expect(rows.first()).toContainText('CODE25');
 await expect(rows.first().getByRole('cell',{name:'Bond',exact:true})).toBeVisible();
 await expect(positions.getByText('1–1 of 1 positions · Page 1 of 1',{exact:true})).toBeVisible();
 await positions.getByRole('searchbox',{name:'Search positions'}).fill('CODE26');
 await expect(rows).toHaveCount(0);await expect(positions.getByText('No positions match these filters. No zero P&L is inferred.')).toBeVisible();
 await filter.selectOption('UNKNOWN');await expect(rows).toHaveCount(1);
 await positions.getByRole('checkbox',{name:'Attention only'}).check();await expect(rows).toHaveCount(1);
 await page.getByRole('tab',{name:'Breakdown',exact:true}).click();
 await page.getByRole('button',{name:'Inspect positions: Price movements',exact:true}).click();
 await expect(filter).toHaveValue('');await expect(rows).toHaveCount(25);
 await filter.selectOption('BOND');
 await page.getByRole('tab',{name:'Logs',exact:true}).click();await page.getByRole('tab',{name:'Positions & cash',exact:true}).click();
 await expect(filter).toHaveValue('BOND');await expect(rows).toHaveCount(1);
 for(const width of [1280,480]){await page.setViewportSize({width,height:900});await expect(filter).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);}
 expect(mock.writes).toEqual([]);
});

test('position pagination offers 25, 50, 100 and all with full-result filtering and retained inspection',async({page})=>{
 const batch=fixture(),template=batch.items[0];
 batch.items=Array.from({length:127},(_,index)=>({...template,attribution_id:`a${index}`,subject_id:`s${index}`,
  display:{interest:'1.25',other:null,attention:index===126?['Interest not supplied']:[]}}));
 batch.presentation!.references=Object.fromEntries(batch.items.map((item,index)=>[item.subject_id!,`Example instrument ${String(index).padStart(3,'0')}`]));
 const mock=await mockReport(page,{batch});
 await page.goto('/?mode=valuation#valuationRun=attempt&report=positions');
 const positions=page.getByRole('region',{name:'Position attribution',exact:true});
 const rows=positions.getByRole('table',{name:'Position attribution',exact:true}).locator('tbody tr');
 const inspector=page.getByRole('complementary',{name:'Position inspection'});
 await expect(inspector).toBeHidden();
 const initialWidth=await positions.boundingBox(),gridWidth=await page.locator('.pnl-result-grid').boundingBox();
 expect(Math.abs(initialWidth!.width-gridWidth!.width)).toBeLessThan(2);
 const size=positions.getByRole('navigation',{name:'Position pagination',exact:true}).getByRole('combobox',{name:'Positions per page',exact:true});
 await expect(size).toHaveValue('25');await expect(rows).toHaveCount(25);
 await expect(positions.getByRole('button',{name:'Previous positions',exact:true})).toBeDisabled();
 await positions.getByRole('button',{name:'Next positions',exact:true}).click();
 await expect(rows).toHaveCount(25);await expect(rows.first()).toContainText('Example instrument 025');
 await expect(positions.getByText('26–50 of 127 positions · Page 2 of 6',{exact:true})).toBeVisible();
 for(const count of [50,100]){
  await size.selectOption(String(count));await expect(rows).toHaveCount(count);
  await expect(rows.first()).toContainText('Example instrument 000');
 }
 await size.selectOption('all');await expect(rows).toHaveCount(127);
 await expect(positions.getByRole('button',{name:'Next positions',exact:true})).toBeDisabled();
 await rows.last().getByRole('button',{name:'Inspect position',exact:true}).click();
 await expect(inspector.getByRole('heading',{name:'Example instrument 126',exact:true})).toBeFocused();
 await inspector.getByRole('button',{name:'Close position details',exact:true}).click();
 await page.getByRole('tab',{name:'Breakdown',exact:true}).click();
 await page.getByRole('tab',{name:'Positions & cash',exact:true}).click();
 await expect(size).toHaveValue('all');await expect(inspector).toBeHidden();
 await size.selectOption('25');
 for(let index=0;index<5;index++)await positions.getByRole('button',{name:'Next positions',exact:true}).click();
 await expect(rows).toHaveCount(2);await expect(rows.last()).toContainText('Example instrument 126');
 await expect(positions.getByRole('button',{name:'Next positions',exact:true})).toBeDisabled();
 await positions.getByRole('searchbox',{name:'Search positions',exact:true}).fill('Example instrument 12');
 await expect(rows).toHaveCount(7);await expect(rows.first()).toContainText('Example instrument 120');
 await expect(positions.getByText('1–7 of 7 positions · Page 1 of 1',{exact:true})).toBeVisible();
 await positions.getByRole('checkbox',{name:'Attention only',exact:true}).check();
 await expect(rows).toHaveCount(1);await expect(rows.first()).toContainText('Example instrument 126');
 await positions.getByRole('searchbox',{name:'Search positions',exact:true}).fill('no matching name');
 await expect(rows).toHaveCount(0);
 await expect(positions.getByText('0 of 0 positions · Page 1 of 1',{exact:true})).toBeVisible();
 expect(mock.reads()).toBe(1);expect(mock.writes).toEqual([]);
});

test('supplied daily interest exposes currency evidence without invalid HTML nesting',async({page})=>{
 const batch=fixture();batch.items=batch.items.slice(0,1);
 batch.items[0].evidence={...batch.items[0].evidence as object,economicInputs:[{kind:'DAILY_ACCRUAL',inputId:'interest-proof',valueDate:'2026-10-20',
  payload:{currencyId:'usd',reportingCurrencyId:'gbp',sourceReference:'Reviewed daily interest',amounts:{dailyLocal:'10.125',dailyBase:'7.75',balanceLocal:'100',balanceBase:'77.5'}}}]};
 batch.presentation!.currencies.usd='USD';
 const mock=await mockReport(page,{batch});
 await page.goto('/?mode=valuation#valuationRun=attempt&report=positions');
 await page.getByRole('button',{name:'Inspect position',exact:true}).click();
 const evidence=page.getByRole('complementary',{name:'Position inspection'}).locator('article').filter({hasText:'Reviewed daily interest'});
 await expect(evidence.getByRole('heading',{name:'Daily accrued interest · 2026-10-20',exact:true})).toBeVisible();
 await expect(evidence.getByText('10.125 / 7.75',{exact:true})).toBeVisible();
 const ids=evidence.getByText('Technical ID',{exact:true});await expect(ids).toHaveCount(2);
 await ids.first().click();await expect(evidence.locator('code',{hasText:'usd'})).toBeVisible();
 await ids.last().click();await expect(evidence.locator('code',{hasText:'gbp'})).toBeVisible();
 expect(mock.writes).toEqual([]);
});

test('report tabs retain filters and review drafts, support keyboard and URL navigation, and keep publication visible',async({page})=>{
 const errors:string[]=[];page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});page.on('pageerror',error=>errors.push(error.message));
 const mock=await mockReport(page);
 await page.goto('/?mode=valuation#valuationRun=attempt&report=breakdown');
 const results=page.getByRole('tabpanel',{name:'Results',exact:true});
 const tab=(name:string)=>results.getByRole('tab',{name,exact:true});
 await expect(tab('Breakdown')).toHaveAttribute('aria-selected','true');
 await expect(results.getByRole('region',{name:'Daily review summary'})).toBeVisible();
 await expect(results.getByRole('region',{name:'Position attribution',exact:true})).toBeHidden();
 await tab('Breakdown').focus();await page.keyboard.press('ArrowRight');
 await expect(tab('Positions & cash')).toBeFocused();
 await expect(results.getByRole('region',{name:'Position attribution',exact:true})).toBeVisible();
 await results.getByRole('searchbox',{name:'Search positions'}).fill('CODE26');
 await results.getByRole('button',{name:'Inspect position',exact:true}).click();
 await results.getByRole('button',{name:'Close position details',exact:true}).click();
 await tab('Review').click();
 await results.getByText('Request component change',{exact:true}).click();
 await results.getByRole('textbox',{name:'Reason',exact:true}).fill('Draft explanation must survive tab changes');
 await tab('Logs').click();
 await expect(results.getByRole('heading',{name:'Operational log',exact:true})).toBeVisible();
 await expect(results.getByRole('button',{name:'Publish valuation',exact:true})).toBeVisible();
 await expect(results.getByRole('region',{name:'Daily review summary'})).toBeVisible();
 await page.goBack();await expect(tab('Review')).toHaveAttribute('aria-selected','true');
 await expect(results.getByRole('textbox',{name:'Reason',exact:true})).toHaveValue('Draft explanation must survive tab changes');
 await page.goForward();await expect(tab('Logs')).toHaveAttribute('aria-selected','true');
 await tab('Positions & cash').click();
 await expect(results.getByRole('searchbox',{name:'Search positions'})).toHaveValue('CODE26');
 await expect(results.getByRole('complementary',{name:'Position inspection'})).toBeHidden();
 expect(mock.reads()).toBe(1);expect(mock.writes).toEqual([]);
 await page.setViewportSize({width:480,height:900});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:'test-results/valuation-report-positions-mobile.png',fullPage:true});
 await tab('Logs').click();await page.reload();
 await expect(page.getByRole('tab',{name:'Logs',exact:true})).toHaveAttribute('aria-selected','true');
 await expect(page.getByRole('heading',{name:'Operational log',exact:true})).toBeVisible();
 expect(mock.reads()).toBe(2);expect(mock.writes).toEqual([]);expect(errors).toEqual([]);
});

test('failed attempts open Logs from History without financial results',async({page})=>{
 const mock=await mockReport(page,{failed:true});
 await page.goto('/?mode=valuation');await page.getByRole('tab',{name:'History',exact:true}).click();
 const history=page.getByRole('tabpanel',{name:'History',exact:true});
 await history.getByRole('button',{name:'View logs',exact:true}).click();
 const results=page.getByRole('tabpanel',{name:'Results',exact:true});
 await expect(results.getByRole('tab',{name:'Logs',exact:true})).toHaveAttribute('aria-selected','true');
 await expect(results.getByRole('heading',{name:'Operational log',exact:true})).toBeVisible();
 await expect(results.getByRole('heading',{name:'No price meets the policy requirements',exact:true})).toBeVisible();
 await results.getByRole('tab',{name:'Breakdown',exact:true}).click();
 await expect(results.getByRole('tabpanel',{name:'Breakdown',exact:true})).toContainText('No staged financial result exists');
 await expect(results.getByRole('region',{name:'Daily review summary'})).toHaveCount(0);
 await expect(results.getByRole('button',{name:'Publish valuation',exact:true})).toHaveCount(0);
 expect(mock.writes).toEqual([]);
});

for(const denied of [false,true])test(`read-only report tabs preserve DISPLAY boundaries (denied ${denied})`,async({page})=>{
 const mock=await mockReport(page,{denied});
 await page.goto('/?mode=valuation&reader=true#valuationRun=attempt&report=positions');
 const results=page.getByRole('tabpanel',{name:'Results',exact:true});
 await expect(results.getByRole('tab',{name:'Positions & cash',exact:true})).toHaveAttribute('aria-selected','true');
 if(denied){
  await expect(results.getByRole('tabpanel',{name:'Positions & cash',exact:true})).toContainText('Current dataset DISPLAY rights are required');
  await expect(results.getByRole('table',{name:'Position attribution',exact:true})).toHaveCount(0);
  await expect(results.getByRole('region',{name:'Daily review summary'})).toHaveCount(0);
 }else await expect(results.getByRole('table',{name:'Position attribution',exact:true})).toBeVisible();
 await results.getByRole('tab',{name:'Review',exact:true}).click();
 await expect(results.getByRole('button',{name:'Submit change request',exact:true})).toHaveCount(0);
 await expect(results.getByRole('button',{name:'Publish valuation',exact:true})).toHaveCount(0);
 await results.getByRole('tab',{name:'Logs',exact:true}).click();
 await expect(results.getByRole('heading',{name:'Operational log',exact:true})).toBeVisible();
 expect(mock.writes).toEqual([]);
});
