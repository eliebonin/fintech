import {test,expect,type Page} from './console-check';

async function setup(page:Page,{invalid=false,uncertain=false}={}){
 const posts:{path:string;body:unknown;key:string|undefined}[]=[];let failed=false;
 const received={jobId:'11111111-1111-4111-8111-111111111111',strategyId:'s',source:'mock-source',filename:'mock.csv',createdAt:'2026-10-19T10:00:00Z',
  status:'RECEIVED',total:0,valid:0,invalid:0,applied:0,replayed:0,rows:[],receipt:[],offset:0,limit:50};
 let job:Record<string,unknown>={...received};
 await page.route('**/api/trade-imports/**',async route=>{
  const req=route.request();const path=new URL(req.url()).pathname;
  if(path.endsWith('/options'))return route.fulfill({json:{strategies:[{id:'s',label:'Synthetic strategy'}],maxRows:500,maxBytes:524288,products:['EQUITY']}});
  if(path.endsWith('/history'))return route.fulfill({json:{items:posts.length?[job]:[],total:posts.length?1:0}});
  if(req.method()==='POST'){
   posts.push({path,body:req.postDataJSON(),key:req.headers()['idempotency-key']});
   if(path.endsWith('/validate'))job={...received,status:invalid?'NEEDS_CORRECTION':'READY',total:2,valid:invalid?1:2,invalid:invalid?1:0,reviewHash:'a'.repeat(64),
    rows:[{row:2,sourceTradeId:'trade-1',status:'VALID',values:{side:'BUY',quantity:'10',executionPrice:'100',listingId:'listing-1',tradeDatetime:'2026-10-01T14:30:00Z',settlementDate:'2026-10-05'},evidence:{instrumentId:'instrument-1',listingId:'listing-1',currency:'GBP',instrumentType:'EQUITY'},errors:[]},
     {row:3,sourceTradeId:'trade-2',status:invalid?'INVALID':'VALID',values:{side:'SELL',quantity:'5',executionPrice:'101',listingId:'listing-1',tradeDatetime:'2026-10-01T15:30:00Z',settlementDate:'2026-10-05'},errors:invalid?[{field:'counterparty',code:'unavailable',message:'Choose an eligible counterparty.'}]:[]}]};
   if(path.endsWith('/confirm')){
    job={...job,status:'APPLIED',applied:2,receipt:[{row:2,sourceTradeId:'trade-1',tradeId:'booked-1',outcome:'BOOKED'}]};
    if(uncertain&&!failed){failed=true;return route.fulfill({status:503,json:{error:{message:'Synthetic lost response'}}});}
   }
   return route.fulfill({json:job});
  }
  return route.fulfill({json:job});
 });
 await page.goto('/?mode=imports');
 await page.getByRole('combobox',{name:'Strategy',exact:true}).selectOption('s');
 await expect(page.getByRole('link',{name:'Download tenant-specific Excel template'})).toHaveAttribute('href',/strategyId=s/);
 await page.getByRole('textbox',{name:'File source',exact:true}).fill('mock-source');
 await page.getByLabel('Trade file (.xlsx or UTF-8 CSV)').setInputFiles({name:'mock.csv',mimeType:'text/csv',buffer:Buffer.from('sourceTradeId\ntrade-1')});
 await page.getByRole('button',{name:'Upload for review — no booking'}).click();
 await expect(page.getByRole('heading',{name:'Review mock.csv'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Prepare your template'})).not.toBeVisible();
 await page.getByRole('button',{name:'Validate all rows',exact:true}).click();
 return posts;
}

test('an invalid row blocks booking and gives actionable feedback',async({page})=>{
 const posts=await setup(page,{invalid:true});
 await expect(page.getByRole('button',{name:'Book 2 trades',exact:true})).toBeDisabled();
 await expect(page.getByText('Choose an eligible counterparty.')).toBeVisible();
 await expect(page.getByText(/Correct the listed errors in your file and submit a revised upload/)).toBeVisible();
 await expect(page.locator('tbody tr').first()).toContainText('trade-2');
 await expect(page.getByRole('heading',{name:'Review mock.csv'})).toBeFocused();
 await page.screenshot({path:'test-results/trade-import-review-desktop.png',fullPage:true});
 expect(posts.map(p=>p.path.split('/').at(-1))).toEqual(['create','validate']);
});

test('uncertain booking retains exact request and does not offer fresh upload',async({page})=>{
 const posts=await setup(page,{uncertain:true});
 await page.getByRole('button',{name:'Book 2 trades',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Outcome not yet confirmed'})).toBeVisible();
 await expect(page.getByRole('button',{name:'New import',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'Retry unchanged request',exact:true}).click();
 await expect(page.getByRole('link',{name:'Open booked trade'})).toBeVisible();
 expect(posts[3]).toEqual(posts[2]);
 await page.getByRole('button',{name:'Import history',exact:true}).click();
 await expect(page.getByRole('cell',{name:'Booking completed'})).toBeVisible();
});

test('guided setup is compact and usable on a narrow screen',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.route('**/api/trade-imports/options',r=>r.fulfill({json:{strategies:[{id:'s',label:'Synthetic strategy'}]}}));
 await page.route('**/api/trade-imports/history?*',r=>r.fulfill({json:{items:[],total:0}}));
 await page.goto('/?mode=imports');
 await expect(page.getByRole('list',{name:'Import progress'})).toBeVisible();
 const help=page.locator('details').filter({has:page.locator('summary',{hasText:'How to use this page'})});
 await expect(help).not.toHaveAttribute('open','');
 expect(await help.evaluate(el=>Boolean(el.compareDocumentPosition(document.querySelector('nav[aria-label="Import views"]')!)&Node.DOCUMENT_POSITION_FOLLOWING))).toBe(true);
 await help.locator('summary').click();
 await expect(help.getByText('Download the template for your permitted strategy and fill in its trade table.')).toBeVisible();
 await help.locator('summary').click();
 await expect(page.getByRole('heading',{name:'Prepare your template'})).toBeVisible();
 await page.getByRole('combobox',{name:'Strategy',exact:true}).selectOption('s');
 await expect(page.getByRole('textbox',{name:'File source',exact:true})).toBeEnabled();
 await expect(page.getByRole('button',{name:'Upload for review — no booking'})).toBeDisabled();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:'test-results/trade-import-setup-mobile.png',fullPage:true});
});

test('read-only users can inspect history without booking affordances',async({page})=>{
 await page.route('**/api/trade-imports/history?*',route=>route.fulfill({json:{items:[{jobId:'readonly-job',filename:'existing.csv',source:'custodian',createdAt:'2026-10-19T10:00:00Z',status:'APPLIED',total:2,valid:2,invalid:0,applied:2,replayed:0}],total:1}}));
 await page.goto('/?mode=imports&reader=true');
 await expect(page.getByRole('button',{name:'Upload for review — no booking'})).toHaveCount(0);
 await page.getByRole('button',{name:'Import history',exact:true}).click();
 await expect(page.getByRole('cell',{name:'Booking completed'})).toBeVisible();
 await expect(page.getByRole('cell',{name:'19 Oct 2026, 10:00 UTC'})).toBeVisible();
});
