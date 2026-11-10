import {test,expect,type Page} from './console-check';

// These journeys replace the retired tenant-global allocation editor checks.
// Exercise the real profile editor; only its HTTP boundary is synthetic.
const profileId='00000000-0000-7000-8000-000000000771';
const versionId='00000000-0000-7000-8000-000000000772';
const nextVersionId='00000000-0000-7000-8000-000000000773';
const fieldLabel='Investment mandate with a deliberately long descriptive label';
const fields=[
 ...['COUNTERPARTY','EXECUTING_BROKER','TRADER','COMMENT'].map(standardFieldKey=>({standardFieldKey,propertyCode:null,propertyVersion:null,requirement:'OPTIONAL',lifecycleBehavior:'INPUT'})),
 {standardFieldKey:null,propertyCode:'MANDATE',propertyVersion:1,requirement:'OPTIONAL',lifecycleBehavior:'INPUT'},
];
const version={profileStatus:'ACTIVE',versionId,profileId,versionNo:1,label:'Maturity classification',description:'Governed closing-entry classifications',reason:'Initial setup',contentHash:'a'.repeat(64),fields,fieldLabels:{'CUSTOM:MANDATE':fieldLabel},publishedAt:'2026-11-04T10:00:00Z'};
const defaults={profileVersionId:versionId,profileId,revision:1,label:version.label,versionNo:1};
const pageOf=(items:unknown[])=>({items,total:items.length,offset:0,limit:25});

type Write={path:string;body:any};
async function openEditor(page:Page){
 const writes:Write[]=[];
 let current=version;
 await page.route('**/api/trade-profiles/**',route=>{
  const request=route.request(),path=new URL(request.url()).pathname.replace('/api/trade-profiles/','');
  if(request.method()==='POST'){
   const body=request.postDataJSON();writes.push({path,body});
   if(path!==`${profileId}/versions`)return route.fulfill({status:400,json:{detail:'Unexpected mutation in profile-publication journey'}});
   current={...version,...body,versionId:nextVersionId,versionNo:2};
   return route.fulfill({status:201,json:current});
  }
  if(path==='register')return route.fulfill({json:pageOf([{profileId,code:'MATURITY',status:'ACTIVE',versionId:current.versionId,versionNo:current.versionNo,label:current.label}])});
  if(path==='default')return route.fulfill({json:defaults});
  if(path===`versions/${versionId}`)return route.fulfill({json:version});
  if(path===`${profileId}/versions`)return route.fulfill({json:pageOf([current])});
  return route.fulfill({status:404,json:{detail:'Unexpected profile read'}});
 });
 await page.goto('/?mode=trade-configuration');
 await page.getByRole('button',{name:'View profile Maturity classification',exact:true}).click();
 await expect(page.getByText('Published version · read-only.',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Create next version',exact:true}).click();
 await page.getByRole('tab',{name:'Lifecycle rules',exact:true}).click();
 await page.getByRole('button',{name:`Edit ${fieldLabel}`,exact:true}).click();
 return {writes,editor:page.getByRole('group',{name:`Edit ${fieldLabel}`,exact:true})};
}

test('profile lifecycle editor keeps long labels and controls readable on desktop and mobile',async({page})=>{
 const {editor,writes}=await openEditor(page);
 await expect(editor.getByRole('combobox',{name:'Lifecycle treatment',exact:true})).toBeFocused();
 for(const width of [1280,390]){
  await page.setViewportSize({width,height:950});
  const layout=await editor.evaluate(panel=>{
   const bounds=panel.getBoundingClientRect();
   const control=panel.querySelector('select')!.getBoundingClientRect();
   return {contained:[...panel.querySelectorAll('select,button')].every(input=>{const r=input.getBoundingClientRect();return r.left>=bounds.left-1&&r.right<=bounds.right+1;}),controlWidth:control.width,controlHeight:control.height,pageFits:document.documentElement.scrollWidth<=innerWidth};
  });
  await expect(editor).toContainText('Ops supplies a value when required');
  expect(layout.contained).toBe(true);expect(layout.controlWidth).toBeGreaterThan(100);expect(layout.controlHeight).toBeGreaterThanOrEqual(36);expect(layout.pageFits).toBe(true);
  await page.screenshot({path:`test-results/lifecycle-profile-rules-${width}.png`,fullPage:true});
 }
 await page.getByRole('button',{name:'Done editing field',exact:true}).click();
 await expect(page.getByRole('button',{name:`Edit ${fieldLabel}`,exact:true})).toBeFocused();
 expect(writes).toHaveLength(0);
});

test('lifecycle rule publication requires a reason and review, publishing a new version without reassignment',async({page})=>{
 const {editor,writes}=await openEditor(page);
 await editor.getByRole('combobox',{name:'Lifecycle treatment',exact:true}).selectOption('ALLOCATION');
 await page.getByRole('button',{name:'Done editing field',exact:true}).click();
 await page.getByRole('button',{name:'Review publication',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Review profile publication',exact:true})).toHaveCount(0);
 expect(writes).toHaveLength(0);
 await page.getByLabel('Reason for this version',{exact:true}).fill('Preserve mandate allocations through maturity');
 await page.getByRole('button',{name:'Review publication',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Review profile publication',exact:true})).toBeFocused();
 await expect(page.getByRole('table',{name:'Proposed field rules'})).toContainText('Keep exposure separate by this field');
 expect(writes).toHaveLength(0);
 await page.getByRole('button',{name:'Publish version',exact:true}).click();
 await expect(page.getByRole('status').filter({hasText:'v2 published'})).toBeVisible();
 expect(writes).toHaveLength(1);
 expect(writes[0]?.path).toBe(`${profileId}/versions`);
 expect(writes[0]?.body).toMatchObject({expectedVersion:1,reason:'Preserve mandate allocations through maturity',fields:expect.arrayContaining([{standardFieldKey:null,propertyCode:'MANDATE',propertyVersion:1,requirement:'OPTIONAL',lifecycleBehavior:'ALLOCATION'}])});
 await expect(page.getByText('Published version · read-only.',{exact:true})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Default for new strategies',exact:true}).locator('..')).toContainText('Maturity classification · v1');
 await page.getByRole('tab',{name:'Lifecycle rules',exact:true}).click();
 await expect(page.getByRole('table',{name:'Lifecycle field handling'})).toContainText('Keep exposure separate by this field');
 await expect(page.getByRole('combobox',{name:'Lifecycle treatment',exact:true})).toHaveCount(0);
});
