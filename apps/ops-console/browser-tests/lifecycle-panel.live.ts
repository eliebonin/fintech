/** Real Next BFF/API/PostgreSQL acceptance; run via the isolated owner runner. */
import {readFileSync} from 'node:fs';
import path from 'node:path';
import {test,expect} from './console-check';
const state=JSON.parse(readFileSync(process.env.LIFECYCLE_E2E_STATE_FILE!,'utf8'));
const fx=state.product==='fx-forward',coupon=state.product==='bond-coupon';
test('direct closure and independently approved closure complete in the live side panel',async({page,context})=>{
 test.skip(coupon,'Coupon journey is read-only');
 async function identity(token:string){await context.addCookies([{name:'local_access_session',value:token,url:state.baseURL,httpOnly:true,sameSite:'Lax'}]);}
 let scrollBefore={window:0,content:0};
 async function open(strategy:string){
  await page.goto(`/lifecycle?strategyId=${strategy}&fromDate=2026-10-01&toDate=2026-11-30`);
  await expect(page.getByRole('button',{name:/Review closing entry for/})).toBeVisible();
  await page.getByRole('combobox',{name:'Rows per page',exact:true}).selectOption('50');
  await page.getByRole('searchbox',{name:'Search instrument',exact:true}).fill('SYNTHETIC Maturity');
  await page.getByRole('button',{name:'Apply filters',exact:true}).click();
  const trigger=page.getByRole('button',{name:/Review closing entry for/});await trigger.scrollIntoViewIfNeeded();
  scrollBefore=await page.evaluate(()=>({window:scrollY,content:document.getElementById('workspace-content')?.scrollTop??0}));
  const beforeURL=page.url();await trigger.click();
  const panel=page.getByRole('dialog',{name:'Review closing entry',exact:true});await expect(panel).toBeVisible();expect(page.url()).toBe(beforeURL);
  if(fx)await expect(panel.getByRole('link',{name:'Open full workspace'})).toHaveAttribute('href',/product=fx-forward/);
  return panel;
 }
 await identity(state.makerToken);
 let panel=await open(state.strategies.DIRECT);
 await panel.getByRole('button',{name:'Load closing inputs',exact:true}).click();
 await expect(panel.getByRole('region',{name:'Closing inputs',exact:true})).toContainText(fx?'1,000,000':'100,000');
 await expect(panel.getByRole('button',{name:'Book now',exact:true})).toBeEnabled();
 await page.screenshot({path:path.join(state.evidence,'live-direct-panel.png')});
 const bookedResponse=page.waitForResponse(response=>new URL(response.url()).pathname===(fx?'/api/lifecycle/fx-forward/closures/book':'/api/lifecycle/bond-redemptions/book')&&response.request().method()==='POST');
 await panel.getByRole('button',{name:'Book now',exact:true}).click();
 const booked=await bookedResponse;expect(booked.status(),JSON.stringify(await booked.json())).toBe(201);
 await expect(panel.getByRole('status').filter({hasText:'Recorded 1'})).toBeVisible({timeout:30000});
 await expect(panel.getByText('Booked · exposure closed',{exact:true})).toBeVisible({timeout:30000});
 await panel.getByRole('button',{name:'Close closing entry'}).click();
 await expect(panel).toHaveCount(0);await expect(page.getByRole('searchbox',{name:'Search instrument',exact:true})).toHaveValue('SYNTHETIC Maturity');
 await expect(page.getByRole('button',{name:/Review closing entry for/})).toBeFocused();
 await expect(page.getByRole('combobox',{name:'Rows per page',exact:true})).toHaveValue('50');
 await expect.poll(()=>page.evaluate(before=>{const content=document.getElementById('workspace-content');return {window:scrollY-Math.min(before.window,Math.max(0,document.documentElement.scrollHeight-innerHeight)),content:(content?.scrollTop??0)-Math.min(before.content,Math.max(0,(content?.scrollHeight??0)-(content?.clientHeight??0)))};},scrollBefore)).toEqual({window:0,content:0});
 panel=await open(state.strategies.REVIEW);
 await panel.getByRole('button',{name:'Load closing inputs',exact:true}).click();
 if(fx){await panel.getByRole('textbox',{name:'Comment (optional)',exact:true}).fill('Synthetic Ops maturity note');await panel.getByRole('button',{name:'Load closing inputs',exact:true}).click();}
 await expect(panel.getByRole('button',{name:'Prepare for approval',exact:true})).toBeEnabled();
 await panel.getByRole('button',{name:'Prepare for approval',exact:true}).click();
 await expect(panel.getByRole('status').filter({hasText:'Prepared for independent approval'})).toBeVisible();
 await expect(panel.getByRole('button',{name:'Approve and book',exact:true})).toBeDisabled();
 await panel.getByRole('button',{name:'Close closing entry'}).click();
 await identity(state.reviewerToken);
 panel=await open(state.strategies.REVIEW);
 await expect(panel.getByRole('button',{name:'Approve and book',exact:true})).toBeEnabled();
 await panel.getByRole('button',{name:'Approve and book',exact:true}).click();
 await expect(panel.getByRole('status').filter({hasText:'Recorded 1'})).toBeVisible({timeout:30000});
 await expect(panel.getByText('Booked · exposure closed',{exact:true})).toBeVisible({timeout:30000});
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:path.join(state.evidence,'live-reviewed-panel-mobile.png')});
 await panel.getByRole('button',{name:'Close closing entry'}).click();
 await expect(page.getByRole('searchbox',{name:'Search instrument',exact:true})).toHaveValue('SYNTHETIC Maturity');
});


test('coupon inspection uses real schedule and confirmation reads without financial actions',async({page,context})=>{
 test.skip(!coupon,'Coupon-only acceptance mode');
 await context.addCookies([{name:'local_access_session',value:state.makerToken,url:state.baseURL,httpOnly:true,sameSite:'Lax'}]);
 const writes:string[]=[];page.on('request',request=>{if(request.url().includes('/api/lifecycle/')&&request.method()!=='GET')writes.push(request.url());});
 for(const mode of ['DIRECT','REVIEW']){
  await page.goto(`/lifecycle?strategyId=${state.strategies[mode]}&fromDate=2026-10-01&toDate=2026-10-31&eventType=BOND_COUPON`);
  const trigger=page.getByRole('button',{name:/Inspect coupon for/});await expect(trigger).toBeVisible();await trigger.click();
  const panel=page.getByRole('dialog',{name:'Inspect coupon',exact:true});await expect(panel.getByRole('region',{name:'Coupon schedule'})).toContainText('2026-10-01');
  await expect(panel.getByRole('region',{name:'Coupon position context'})).toContainText('100,000');await expect(panel.locator('form')).toHaveCount(0);
  await expect(panel.getByRole('button',{name:/Book|Prepare|Approve|Record payment/})).toHaveCount(0);
  if(mode==='REVIEW')await expect(panel.getByRole('region',{name:'Recorded coupon confirmations'})).toContainText('1,000');
  await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:path.join(state.evidence,`coupon-${mode.toLowerCase()}.png`)});
  await panel.getByRole('button',{name:'Close coupon inspection'}).click();await expect(trigger).toBeFocused();
  await page.setViewportSize({width:1360,height:950});
 }
 expect(writes).toEqual([]);
});
