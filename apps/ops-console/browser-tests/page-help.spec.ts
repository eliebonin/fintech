import {test,expect} from './console-check';

test('page guidance opens with the keyboard and leaves policy drafts and requests untouched',async({page})=>{
 const writes:string[]=[];
 await page.route('**/api/**',route=>{if(route.request().method()!=='GET')writes.push(route.request().method());return route.fulfill({json:{sources:[]}});});
 await page.goto('/?mode=policy');
 await page.getByLabel('Policy code',{exact:true}).fill('KEEP_THIS_DRAFT');
 const toggle=page.locator('summary').filter({hasText:'How to use this page'});
 await toggle.focus();
 await page.keyboard.press('Enter');
 await expect(page.getByRole('heading',{name:'Workflow impact',exact:true})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Key terms',exact:true})).toBeVisible();
 await expect(page.getByLabel('Policy code',{exact:true})).toHaveValue('KEEP_THIS_DRAFT');
 expect(writes).toEqual([]);
 await toggle.focus();await page.keyboard.press('Space');
 await expect(page.getByRole('heading',{name:'Workflow impact',exact:true})).toBeHidden();
 await expect(page.getByLabel('Policy code',{exact:true})).toHaveValue('KEEP_THIS_DRAFT');
 await toggle.click();await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:'test-results/page-help-mobile.png',fullPage:true});
});
