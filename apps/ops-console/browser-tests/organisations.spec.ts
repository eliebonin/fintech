import {test,expect,type Page} from '@playwright/test';
const id='00000000-0000-7000-8000-000000000777';
function fixture(legacy=false){return {organisationId:id,displayName:'Synthetic bank',legalName:'Synthetic bank Ltd',
 status:'ACTIVE',leis:[],label:null,internalCode:null,notes:null,versionNo:0,
 roles:{COUNTERPARTY:!legacy,EXECUTING_BROKER:!legacy},history:[],policies:{
  COUNTERPARTY:{mode:legacy?'LEGACY':'CURATED',versionNo:legacy?0:1},
  EXECUTING_BROKER:{mode:legacy?'LEGACY':'CURATED',versionNo:legacy?0:1}}};}
async function workspace(page:Page,{unknown=false,refreshFailure=false,legacy=false}={}){
 let detail=fixture(legacy),failed=false;const posts:Array<Record<string,unknown>>=[];
 await page.route('**/api/trade-configuration/**',async route=>{
  const req=route.request(),url=new URL(req.url());
  if(req.method()==='POST'){
   const body=req.postDataJSON();posts.push(body);
   if(url.pathname.includes('organisation-roles'))return route.fulfill({json:{data:detail.policies}});
   detail={...detail,versionNo:1,label:body.label,displayName:body.label||detail.legalName,internalCode:body.internalCode,
    notes:body.notes,roles:{...detail.roles,...body.roles}};
   if(unknown&&!failed){failed=true;return route.fulfill({status:503,json:{error:{message:'Synthetic transport interruption'}}});}
   return route.fulfill({json:{data:detail}});
  }
  if(url.pathname.endsWith(id))return route.fulfill({json:{data:detail}});
  if(refreshFailure&&posts.length&&!failed){failed=true;return route.fulfill({status:503,json:{error:{message:'Synthetic refresh failure'}}});}
  return route.fulfill({json:{data:{items:[detail],total:1,offset:0,limit:25,policies:detail.policies}}});
 });
 await page.goto('/?mode=organisations');
 await expect(page.getByRole('heading',{name:'Organisations',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Manage Synthetic bank',exact:true}).click();
 return posts;
}
test('organisation editor retains exact retry and independent role selections',async({page})=>{
 const posts=await workspace(page,{unknown:true});
 await page.getByLabel('Tenant label',{exact:true}).fill('My synthetic bank');
 await page.getByLabel('Private notes',{exact:true}).fill('Tenant-private note');
 await page.getByLabel('Counterparties',{exact:true}).uncheck();
 await page.getByLabel('Reason for change',{exact:true}).fill('Disable this counterparty only');
 await page.getByRole('button',{name:'Save organisation',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Outcome not confirmed'})).toBeVisible();
 await expect(page.getByLabel('Private notes',{exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'Retry unchanged request',exact:true}).click();
 await expect(page.getByText('Saved. Changes apply to new selections; historical records are unchanged.')).toBeVisible();
 expect(posts).toHaveLength(2);expect(posts[1]).toEqual(posts[0]);
 expect(posts[0].roles).toEqual({COUNTERPARTY:false,EXECUTING_BROKER:true});
 expect(posts[0].idempotencyKey).toMatch(/^[0-9a-f-]{36}$/);
});
test('confirmed organisation save is not called failed when refresh fails',async({page})=>{
 const posts=await workspace(page,{refreshFailure:true});
 await page.getByLabel('Reason for change',{exact:true}).fill('Update private settings');
 await page.getByRole('button',{name:'Save organisation',exact:true}).click();
 await expect(page.getByText('Saved. Changes apply to new selections; historical records are unchanged.')).toBeVisible();
 await expect(page.getByRole('alert')).toContainText('Synthetic refresh failure');
 await expect(page.getByRole('button',{name:'Retry unchanged request',exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'Reload current state',exact:true}).click();
 await expect(page.getByRole('button',{name:'Save organisation',exact:true})).toBeEnabled();expect(posts).toHaveLength(1);
});
test('legacy role setup requires explicit acknowledgement and preserves selected initial identity',async({page})=>{
 const posts=await workspace(page,{legacy:true});
 await page.getByRole('button',{name:'Set up counterparties list with this organisation',exact:true}).click();
 await expect(page.getByText('Initial selection: Synthetic bank Ltd')).toBeVisible();
 await page.getByLabel('Reason for list activation').fill('Establish a curated counterparty list');
 await page.getByRole('button',{name:'Activate curated list',exact:true}).click();expect(posts).toHaveLength(0);
 await page.getByLabel('I understand this restricts future selections.').check();
 await page.getByRole('button',{name:'Activate curated list',exact:true}).click();
 await expect.poll(()=>posts.length).toBe(1);expect(posts[0].ids).toEqual([id]);
});

test('pagination uses the applied search rather than an unsubmitted draft',async({page})=>{
 const searches:string[]=[];
 await page.route('**/api/trade-configuration/organisations?**',route=>{
  const url=new URL(route.request().url()),offset=Number(url.searchParams.get('offset'));
  searches.push(url.searchParams.get('q')??'');
  const items=Array.from({length:Math.min(25,30-offset)},(_,n)=>({...fixture(),organisationId:`party-${n+offset}`,displayName:`Party ${n+offset}`}));
  return route.fulfill({json:{data:{items,total:30,limit:25,offset,policies:fixture().policies}}});
 });
 await page.goto('/?mode=organisations');await expect(page.getByText('1–25 of 30')).toBeVisible();
 await page.getByRole('searchbox',{name:'Search organisations'}).fill('Unsubmitted draft');
 await page.getByRole('button',{name:'Next',exact:true}).click();
 await expect(page.getByText('26–30 of 30')).toBeVisible();expect(searches).toEqual(['','']);
});
