import {test,expect} from './console-check';

test('review separates scope, readiness and hold; export preview includes every page',async({page})=>{
 const profile={profileId:'profile',name:'Synthetic investment firm',lei:'TEST0000000000000071',firmCategory:'MIFID_FIRM',firmScope:'IN_SCOPE',revision:1,reason:'Synthetic assessment'};
 const items=Array.from({length:28},(_,i)=>({candidateId:'candidate-'+i,tradeId:'trade-'+i,revision:1,reportability:'NEEDS_ASSESSMENT',readiness:'INCOMPLETE',disposition:'AUTO',included:false,reason:'Instrument scope needs assessment',mapping:{},missingFields:['buyerId'],facts:{instrumentName:'Instrument '+i,instrumentType:'EQUITY',quantity:'100000.123456789012',quantityUnit:'SHARES',executionPrice:'12.123456789012',priceCurrency:'GBP',priceBasis:'UNIT_PRICE',executionTime:'2026-10-28T14:31:10Z',bookingTerms:{quantityBasis:'UNITS'}}}));
 let prepared=false;let frozen=false;
 await page.route('**/api/regulatory-reporting/**',async route=>{
  const url=new URL(route.request().url());const path=url.pathname.split('/api/regulatory-reporting/')[1];
  let data:unknown={};
  if(path==='options')data={profiles:[profile],strategies:[{id:'strategy',name:'Synthetic fund'}]};
  if(path==='prepare'){prepared=true;data={created:28,changed:0,examined:28};}
  if(path==='candidates'){
   const offset=Number(url.searchParams.get('offset')??0);const rows=prepared?items:[];
   data={items:rows.slice(offset,offset+25),total:rows.length,totals:{total:rows.length,included:items.filter(x=>x.included).length,attention:rows.length-1,held:0,notReportable:0}};
  }
  if(path==='candidates/candidate-0')data={...items[0],history:[{reason:'Source import',action:'PREPARED'}]};
  if(path==='candidates/candidate-0/review'){
   const request=route.request().postDataJSON();expect(request.reason).toBe('Reviewed synthetic execution');
   Object.assign(items[0],{included:true,revision:2,reportability:'REPORTABLE',readiness:'READY',mapping:request.mapping});data=items[0];
  }
  if(path==='export-preview')data={expectedRevisions:{'candidate-0':2},totals:{total:28,included:1,attention:27,held:0,notReportable:0}};
  if(path==='exports'&&route.request().method()==='POST'){
   expect(route.request().headers()['idempotency-key']).toBeTruthy();
   expect(route.request().postDataJSON().expectedRevisions).toEqual({'candidate-0':2});
   frozen=true;data={exportId:'export',contentHash:'abc',csvContent:'quantity\n100000.123456789012\n',manifest:{validationLevel:'PREPARATION_ONLY',submissionStatus:'NOT_SUBMITTED',totals:{total:28,included:1,attention:27,held:0,notReportable:0}}};
  }
  if(path==='exports'&&route.request().method()==='GET')data={items:[],total:0};
  if(path==='exports/export')data={exportId:'export',contentHash:'abc',csvContent:'quantity\n100000.123456789012\n',manifest:{validationLevel:'PREPARATION_ONLY',submissionStatus:'NOT_SUBMITTED'}};
  await route.fulfill({json:data});
 });
 await page.goto('/?mode=reporting');
 await expect(page.getByText('How to use this page')).toBeVisible();
 await page.getByRole('combobox',{name:'Reporting entity',exact:true}).selectOption('profile');await page.getByRole('combobox',{name:'Strategy',exact:true}).selectOption('strategy');
 await page.getByLabel('From execution date').fill('2026-10-28');await page.getByLabel('To execution date').fill('2026-10-28');
 await page.getByRole('button',{name:'Prepare / refresh executions'}).click();
 await expect(page.getByText('1–25 of 28')).toBeVisible();await expect(page.getByText('100,000.123456789012 SHARES').first()).toBeVisible();
 await page.getByRole('button',{name:'Next',exact:true}).click();await expect(page.getByText('26–28 of 28')).toBeVisible();
 await page.getByRole('button',{name:'Previous',exact:true}).click();await page.getByRole('button',{name:'Inspect',exact:true}).first().click();
 const inspection=page.getByRole('region',{name:'Report inspection'});
 await inspection.getByRole('combobox',{name:'Action',exact:true}).selectOption('REPORTABLE');
 await inspection.getByLabel('Buyer reporting ID').fill('SYNTHETIC_BUYER');
 await inspection.getByLabel('Reason',{exact:true}).fill('Reviewed synthetic execution');
 await inspection.getByRole('button',{name:'Save reviewed revision'}).click();
 await page.getByRole('button',{name:'Review preparation export'}).click();
 await expect(page.getByText('All ready reports in this entity/strategy/date scope will be included, across every page.',{exact:false})).toBeVisible();
 await page.getByRole('button',{name:'Freeze preparation export (1)'}).click();
 await expect(page.getByText('Preparation only · Not submitted · Not regulator-validated')).toBeVisible();expect(frozen).toBe(true);
 const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Download preparation CSV'}).click()]);
 expect(download.suggestedFilename()).toBe('uk-mifir-preparation-export.csv');
 await page.screenshot({path:'test-results/regulatory-reporting-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await page.screenshot({path:'test-results/regulatory-reporting.png',fullPage:true});
});

test('readers have no preparation, review, entity configuration or export controls',async({page})=>{
 await page.route('**/api/regulatory-reporting/options',route=>route.fulfill({json:{profiles:[],strategies:[]}}));
 await page.goto('/?mode=reporting&reader=true');
 await expect(page.getByRole('button',{name:'Prepare / refresh executions'})).toHaveCount(0);
 await page.getByRole('tab',{name:'Reporting entities'}).click();await expect(page.getByRole('button',{name:'Add entity'})).toHaveCount(0);
 await expect(page.getByText('No reporting entities configured.')).toBeVisible();
});
