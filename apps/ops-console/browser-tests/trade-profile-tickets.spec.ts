import {test,expect} from './console-check';
const strategy='00000000-0000-7000-8000-000000000555',field='00000000-0000-7000-8000-000000000558',bank='00000000-0000-7000-8000-000000000559';
function context(revision=1,custom=true){return {data:{tenantId:'synthetic-tenant',bookedByUserAccountId:'synthetic-actor',tags:[],properties:custom?[{definitionId:field,code:'MANDATE',label:'Mandate',valueType:'TEXT',required:true,choices:[],description:'Classify this execution',catalogueId:null}]:[],tradeProfile:{tenantId:'synthetic-tenant',strategyId:strategy,profileVersionId:'00000000-0000-7000-8000-000000000778',profileId:'00000000-0000-7000-8000-000000000777',profileLabel:'Fund dealing',versionNo:revision,assignmentRevision:revision,configurationHash:'a'.repeat(64),fields:['COUNTERPARTY','EXECUTING_BROKER','TRADER','COMMENT'].map(standardFieldKey=>({standardFieldKey,requirement:standardFieldKey==='COUNTERPARTY'&&!custom?'NOT_USED':'OPTIONAL',lifecycleBehavior:'INPUT',label:standardFieldKey,sourceKey:null,definitionId:null,fieldKey:'STANDARD:'+standardFieldKey}))}}};}
test('cash ticket reloads a changed profile without losing its execution or property draft',async({page})=>{
 let revision=1;const posted:any[]=[];
 await page.route('**/api/trades/booking-context?**',route=>route.fulfill({json:context(revision)}));
 await page.route('**/api/trades',route=>{posted.push(route.request().postDataJSON());if(posted.length===1){revision=2;return route.fulfill({status:409,json:{error:{code:'configuration.changed',message:'Strategy trade configuration changed. Reload and review.'}}});}return route.fulfill({status:201,json:{data:{trade:{tradeId:'synthetic-trade'}}}});});
 await page.goto('/?mode=profile-cash-ticket');await page.getByRole('combobox',{name:'Strategy',exact:true}).selectOption(strategy);
 await expect(page.getByText('Fund dealing · v1')).toBeVisible();
 await page.getByRole('textbox',{name:'Quantity',exact:true}).fill('10');await page.getByRole('textbox',{name:'Execution price',exact:true}).fill('1.25');await page.getByRole('textbox',{name:'Trade time',exact:true}).fill('2026-10-01T10:00:00Z');await page.getByLabel('Settlement date',{exact:true}).fill('2026-10-05');
 await page.getByRole('textbox',{name:'Mandate (required)',exact:true}).fill('Income');
 await page.getByRole('button',{name:'Review booking',exact:true}).click();await page.getByRole('button',{name:'Confirm booking',exact:true}).click();
 await expect(page.getByText('Strategy trade configuration changed. Reload and review.')).toBeVisible();
 await page.getByRole('button',{name:'Reload trade configuration',exact:true}).click();await expect(page.getByText('Fund dealing · v2')).toBeVisible();
 await expect(page.getByRole('textbox',{name:'Quantity',exact:true})).toHaveValue('10');await expect(page.getByRole('textbox',{name:'Execution price',exact:true})).toHaveValue('1.25');await expect(page.getByRole('textbox',{name:'Mandate (required)',exact:true})).toHaveValue('Income');
 await page.getByRole('button',{name:'Review booking',exact:true}).click();await page.getByRole('button',{name:'Confirm booking',exact:true}).click();
 await expect.poll(()=>posted.length).toBe(2);expect(posted[0].profileAssignmentRevision).toBe(1);expect(posted[1]).toMatchObject({profileAssignmentRevision:2,quantity:'10',executionPrice:'1.25'});
});
test('forward retains native counterparty requirement even when profile marks it not used',async({page})=>{
 let scope='';await page.route('**/api/trades/booking-context?**',route=>route.fulfill({json:context(1,false)}));
 await page.route('**/api/tenant-reference/options?**',route=>{scope=route.request().url();return route.fulfill({json:{items:[{id:bank,label:'Example bank'}],selected:[],total:1,offset:0,limit:26}});});
 await page.goto('/?mode=profile-forward-ticket');await page.getByRole('combobox',{name:'Strategy',exact:true}).selectOption(strategy);await expect(page.getByText('Fund dealing · v1')).toBeVisible();
 await page.getByLabel('Base-currency amount',{exact:false}).fill('1000');
 await page.getByRole('group',{name:'Counterparty (required)',exact:true}).getByRole('button',{name:'Search values',exact:true}).click();await page.getByRole('button',{name:'Example bank',exact:true}).click();
 expect(scope).toContain('consumer=booking');expect(scope).toContain(`strategyId=${strategy}`);await expect(page.getByText('Example bank',{exact:true})).toBeVisible();
});
