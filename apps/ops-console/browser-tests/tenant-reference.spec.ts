import {test,expect} from './console-check';
const source={sourceKey:'catalogue:00000000-0000-7000-8000-000000000777',catalogueId:'00000000-0000-7000-8000-000000000777',kind:'CUSTOM',code:'MANDATES',label:'Investment mandates',status:'ACTIVE',activeEntryCount:1,fieldCount:1};
const record={recordVersionId:'version',recordId:'stable',code:'CORE',label:'Core mandate',versionNo:1,status:'ACTIVE'};

test('reference register searches the server and pages beyond the initial population',async({page})=>{
 const requests:string[]=[];
 await page.route('**/api/tenant-reference/sources?**',route=>{const url=new URL(route.request().url());requests.push(url.search);return route.fulfill({json:{items:[source],total:url.searchParams.get('q')?1:55,offset:Number(url.searchParams.get('offset')??0),limit:25}});});
 await page.goto('/?mode=reference-data');await expect(page.getByRole('link',{name:'Open catalogue',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Next',exact:true}).click();await expect(page.getByText('26–50 of 55')).toBeVisible();
 await page.getByLabel('Find a source').fill('mandates');await page.getByRole('button',{name:'Search sources'}).click();await expect(page.getByText('1–1 of 1')).toBeVisible();
 expect(requests.some(url=>url.includes('offset=25'))).toBe(true);expect(requests.at(-1)).toContain('q=mandates');
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test('catalogue correction preserves native audit validation and its confirmed write after failed refresh',async({page})=>{
 let written=false;const writes:unknown[]=[];
 await page.route('**/api/tenant-reference/**',route=>{
  if(written)return route.fulfill({status:503,json:{detail:'Synthetic read failure'}});
  return route.fulfill({json:route.request().url().includes('/entries?')?{items:[record],total:1,offset:0,limit:25}:source});
 });
 await page.route('**/api/trade-configuration/**',route=>{writes.push(route.request().postDataJSON());written=true;return route.fulfill({json:{data:record}});});
 await page.goto('/?mode=reference-catalogue');await page.getByRole('button',{name:'Correct Core mandate'}).click();
 await page.getByLabel('Display label').fill('Core allocation');await page.getByRole('button',{name:'Save corrected version'}).click();expect(writes).toHaveLength(0);
 await page.getByLabel('Change reason',{exact:true}).fill('Clarify name');await page.getByRole('button',{name:'Save corrected version'}).click();
 await expect(page.getByRole('status').filter({hasText:'Entry corrected'})).toContainText('Entry corrected');await expect(page.getByRole('alert')).toContainText('Synthetic read failure');
 expect(writes).toEqual([{label:'Core allocation',description:'',reason:'Clarify name'}]);await expect(page.getByRole('button',{name:'Add entry',exact:true})).toBeDisabled();
});

test('catalogue sections support manual keyboard activation without losing context',async({page})=>{
 await page.route('**/api/tenant-reference/**',route=>route.fulfill({json:route.request().url().includes('/entries?')?{items:[],total:0,offset:0,limit:25}:route.request().url().includes('/usage?')?{items:[{definitionId:'field',label:'Mandate',code:'MANDATE',versionNo:1,status:'ACTIVE'}],total:1,offset:0,limit:25}:source}));
 await page.goto('/?mode=reference-catalogue');await expect(page.getByText('No entries recorded.',{exact:true})).toBeVisible();
 await page.getByRole('tab',{name:'Entries',exact:true}).focus();await page.keyboard.press('ArrowRight');await expect(page.getByRole('tab',{name:'Used by',exact:true})).toBeFocused();await expect(page.getByRole('tab',{name:'Entries',exact:true})).toHaveAttribute('aria-selected','true');
 await page.keyboard.press('Enter');await expect(page.getByRole('link',{name:'Mandate',exact:true})).toBeVisible();
});


test('catalogue history waits for its own rows instead of interpreting loaded entries as audit events',async({page})=>{
 let releaseHistory!:()=>void;
 const historyGate=new Promise<void>(resolve=>{releaseHistory=resolve;});
 await page.route('**/api/tenant-reference/**',async route=>{
  const url=new URL(route.request().url());
  if(url.pathname.endsWith('/entries'))return route.fulfill({json:{items:[record],total:1,offset:0,limit:25}});
  if(url.pathname.endsWith('/usage'))return route.fulfill({json:{items:[{definitionId:'field',label:'Mandate',code:'MANDATE',versionNo:1,status:'ACTIVE'}],total:1,offset:0,limit:25}});
  if(url.pathname.endsWith('/history')){
   await historyGate;
   return route.fulfill({json:{items:[{eventId:'event',action:'RECORD_CREATED',subjectId:'stable',reason:'Initial mandate creation',recordedAtUtc:'2026-11-04T12:00:00Z'}],total:1,offset:0,limit:25}});
  }
  return route.fulfill({json:source});
 });
 await page.goto('/?mode=reference-catalogue');
 await expect(page.getByRole('button',{name:'Correct Core mandate',exact:true})).toBeVisible();
 try{
  await page.getByRole('tab',{name:'History',exact:true}).click();
  await expect(page.getByRole('status')).toHaveText('Loading history…',{timeout:3000});
  await expect(page.getByRole('table')).toHaveCount(0);
 }finally{releaseHistory();}
 await expect(page.getByRole('table',{name:'Catalogue history',exact:true})).toContainText('record created');
 await expect(page.getByText('Initial mandate creation',{exact:true})).toBeVisible();
 await page.getByRole('tab',{name:'Used by',exact:true}).click();
 await expect(page.getByRole('link',{name:'Mandate',exact:true})).toBeVisible();
 await page.getByRole('tab',{name:'History',exact:true}).click();
 await expect(page.getByRole('table',{name:'Catalogue history',exact:true})).toContainText('Initial mandate creation');
 await page.getByRole('tab',{name:'Entries',exact:true}).click();
 await expect(page.getByRole('button',{name:'Correct Core mandate',exact:true})).toBeVisible();
});
