import {test,expect} from './console-check';
const profileId='00000000-0000-7000-8000-000000000777',v1='00000000-0000-7000-8000-000000000778',v2='00000000-0000-7000-8000-000000000779';
const strategyId='00000000-0000-7000-8000-000000000555';
const fields=['COUNTERPARTY','EXECUTING_BROKER','TRADER','COMMENT'].map(standardFieldKey=>({standardFieldKey,propertyCode:null,propertyVersion:null,requirement:'OPTIONAL',lifecycleBehavior:'INPUT'}));
const version={profileStatus:'ACTIVE',versionId:v1,profileId,versionNo:1,label:'Fund dealing',description:'Fund execution metadata',reason:'Initial setup',contentHash:'a'.repeat(64),fields,fieldLabels:{},publishedAt:'2026-11-04T10:00:00Z'};
const row={profileId,code:'FUND',status:'ACTIVE',versionId:v1,versionNo:1,label:'Fund dealing'};
const defaults={profileVersionId:v1,profileId,revision:1,label:'Fund dealing',versionNo:1};
const pageOf=(items:unknown[],total=items.length,offset=0)=>({items,total,offset,limit:25});

test('publish reviewed rules without changing strategy assignments or the tenant default',async({page})=>{
 const mutations:Array<{path:string;body:any}>=[];let current=version;
 await page.route('**/api/trade-profiles/**',route=>{
  const request=route.request(),url=new URL(request.url()),path=url.pathname.replace('/api/trade-profiles/','');
  if(request.method()==='POST'){
   const body=request.postDataJSON();mutations.push({path,body});current={...version,...body,versionId:v2,versionNo:2};return route.fulfill({status:201,json:current});
  }
  if(path==='register')return route.fulfill({json:pageOf([{...row,versionId:current.versionId,versionNo:current.versionNo}])});
  if(path==='default')return route.fulfill({json:defaults});
  if(path.startsWith('versions/'))return route.fulfill({json:version});
  if(path.endsWith('/versions'))return route.fulfill({json:pageOf([current])});
  return route.fulfill({json:pageOf([])});
 });
 await page.goto('/?mode=trade-configuration');await page.getByRole('button',{name:'View profile Fund dealing'}).click();
 await expect(page.getByText('Published version · read-only.',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Create next version'}).click();
 await page.getByRole('button',{name:'Edit Counterparty',exact:true}).click();
 await page.getByRole('combobox',{name:'Booking requirement',exact:true}).selectOption('REQUIRED');await page.getByRole('button',{name:'Done editing field'}).click();
 await page.getByRole('tab',{name:'Lifecycle rules',exact:true}).click();await page.getByRole('button',{name:'Edit Counterparty',exact:true}).click();
 await expect(page.getByRole('region',{name:'Lifecycle treatment guide'})).toContainText('Protection and Income are closed separately');
 await page.getByRole('combobox',{name:'Lifecycle treatment',exact:true}).selectOption('ALLOCATION');await page.getByRole('button',{name:'Done editing field'}).click();
 await page.getByRole('button',{name:'Edit Comment',exact:true}).click();
 await expect(page.getByRole('combobox',{name:'Lifecycle treatment',exact:true}).locator('option')).toHaveCount(2);
 await expect(page.getByText('Comment is descriptive metadata.',{exact:false})).toBeVisible();
 await page.getByRole('button',{name:'Done editing field'}).click();
 await page.getByLabel('Reason for this version').fill('Preserve counterparty exposure at maturity');
 await page.getByRole('button',{name:'Review publication'}).click();await expect(page.getByRole('heading',{name:'Review profile publication'})).toBeFocused();
 await expect(page.getByText('Changed from optional')).toBeVisible();expect(mutations).toHaveLength(0);
 await page.getByRole('button',{name:'Publish version',exact:true}).click();await expect(page.getByRole('status').filter({hasText:'v2 published'})).toBeVisible();
 expect(mutations).toHaveLength(1);expect(mutations[0]?.path).toBe(`${profileId}/versions`);expect(mutations[0]?.body.fields[0]).toMatchObject({standardFieldKey:'COUNTERPARTY',requirement:'REQUIRED',lifecycleBehavior:'ALLOCATION'});
 await expect(page.getByRole('heading',{name:'Default for new strategies'}).locator('..')).toContainText('Fund dealing · v1');
 await page.getByRole('tab',{name:'Fields',exact:true}).focus();await page.keyboard.press('ArrowRight');await expect(page.getByRole('tab',{name:'Lifecycle rules',exact:true})).toBeFocused();await expect(page.getByRole('tab',{name:'Fields',exact:true})).toHaveAttribute('aria-selected','true');await page.keyboard.press('Enter');
 await page.setViewportSize({width:390,height:844});const dimensions=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,wide:[...document.querySelectorAll<HTMLElement>('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1&&e.getBoundingClientRect().width>0).slice(0,12).map(e=>({tag:e.tagName,css:e.className,right:e.getBoundingClientRect().right,width:e.getBoundingClientRect().width}))}));expect(dimensions.scroll,JSON.stringify(dimensions)).toBeLessThanOrEqual(dimensions.width);
});

test('strategy readers see the pinned version and no assignment controls',async({page})=>{
 await page.route('**/api/trade-profiles/**',route=>route.fulfill({json:{tenantId:'synthetic-tenant',strategyId,profileVersionId:v1,profileId,profileLabel:'Fund dealing',versionNo:1,assignmentRevision:3,configurationHash:'a'.repeat(64),fields:[],canAssign:false}}));
 await page.goto('/?mode=strategy-profile');await expect(page.getByText('Fund dealing · v1',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Change assigned profile'})).toHaveCount(0);
});

test('assignment conflict keeps the selected version and operator reason',async({page})=>{
 await page.route('**/api/trade-profiles/**',route=>{
  const request=route.request(),path=new URL(request.url()).pathname.replace('/api/trade-profiles/','');
  if(path.endsWith('/preview'))return route.fulfill({json:{strategyId,allowed:true,issues:[],affectedTradeCount:12,inputHash:'b'.repeat(64),assignmentRevision:3}});
  if(request.method()==='POST')return route.fulfill({status:409,json:{detail:'Source bookings changed. Review again.'}});
  if(path==='register')return route.fulfill({json:pageOf([row])});
  if(path.endsWith('/versions'))return route.fulfill({json:pageOf([version])});
  return route.fulfill({json:{tenantId:'synthetic-tenant',strategyId,profileVersionId:v1,profileId,profileLabel:'Fund dealing',versionNo:1,assignmentRevision:3,configurationHash:'a'.repeat(64),fields:[],canAssign:true}});
 });
 await page.goto('/?mode=strategy-profile');await page.getByRole('button',{name:'Change assigned profile'}).click();
 await page.getByRole('combobox',{name:'Profile',exact:true}).selectOption(profileId);await page.getByRole('combobox',{name:'Version',exact:true}).selectOption(v1);await page.getByRole('button',{name:'Review assignment impact'}).click();
 await page.getByLabel('Reason for assignment').fill('Use the reviewed dealing profile');await page.getByRole('button',{name:'Confirm strategy assignment'}).click();
 await expect(page.getByRole('alert')).toContainText('Review again');await expect(page.getByLabel('Reason for assignment')).toHaveValue('Use the reviewed dealing profile');await expect(page.getByRole('combobox',{name:'Version',exact:true})).toHaveValue(v1);
});
