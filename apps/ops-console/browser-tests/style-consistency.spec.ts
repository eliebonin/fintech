import {test,expect} from './console-check';

test('native controls and organisation tables share compact, readable defaults',async({page})=>{
 await page.goto('/?mode=styles');
 const action=page.getByRole('button',{name:'Unclassified action'});
 await expect(action).toHaveCSS('border-radius','8px');
 await expect(action).toHaveCSS('min-height','40px');
 expect((await action.boundingBox())!.height).toBeLessThanOrEqual(44);
 await expect(page.getByRole('button',{name:'Material action',exact:true})).toHaveCSS('min-height','40px');
 await expect(page.getByRole('button',{name:'Compact action',exact:true})).toHaveCSS('min-height','32px');
 await expect(page.getByRole('cell',{name:'Manage',exact:true})).toHaveCSS('text-align','left');
 await expect(page.getByRole('cell',{name:'Counterparty',exact:true})).toHaveCSS('padding-top','10px');
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:'test-results/workspace-style-mobile.png',fullPage:true});
});

test('skip and section links move keyboard focus to their real targets',async({page})=>{
 await page.goto('/?mode=styles');
 await page.keyboard.press('Tab');
 await expect(page.getByRole('link',{name:'Skip to page content'})).toBeFocused();
 await page.keyboard.press('Enter');
 await expect(page.locator('#workspace-content')).toBeFocused();
 await page.getByRole('link',{name:'Second section',exact:true}).click();
 await expect(page.locator('#section-two')).toBeFocused();
});

test('pricing tasks preserve unsaved fields and support keyboard navigation',async({page})=>{
 await page.route('**/api/**',route=>route.fulfill({json:{sources:[]}}));
 await page.goto('/?mode=policy');
 await page.getByLabel('Policy code',{exact:true}).fill('PRESERVED_DRAFT');
 expect((await page.getByLabel('Policy code',{exact:true}).boundingBox())!.height).toBeLessThanOrEqual(48);
 await page.screenshot({path:'test-results/pricing-configuration-desktop.png',fullPage:true});
 await page.getByRole('tab',{name:'Configuration',exact:true}).focus();
 await page.keyboard.press('ArrowRight');
 await expect(page.getByRole('tab',{name:'Preview',exact:true})).toBeFocused();
 await expect(page.getByRole('heading',{name:'Read-only preview'})).toBeVisible();
 await expect(page.getByRole('button',{name:'Preview saved version'})).toBeDisabled();
 await page.keyboard.press('End');
 await expect(page.getByRole('tab',{name:'Reference',exact:true})).toBeFocused();
 await expect(page.getByRole('heading',{name:'Help with pricing choices',exact:true})).toBeVisible();
 await page.keyboard.press('Home');
 await expect(page.getByLabel('Policy code',{exact:true})).toHaveValue('PRESERVED_DRAFT');
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:'test-results/pricing-configuration-mobile.png',fullPage:true});
 await page.goto('/?mode=policy&reader=true');
 await expect(page.getByRole('heading',{name:'Read-only configuration'})).toBeVisible();
 await expect(page.getByRole('button',{name:'Save new immutable version'})).toHaveCount(0);
});

test('preview uses the selected saved version, not the editable draft, and keeps evidence reachable',async({page})=>{
 const posts:Record<string,unknown>[]=[];
 await page.route('**/api/**',route=>{
  if(route.request().method()==='POST'){
   posts.push(route.request().postDataJSON());
   return route.fulfill({json:{status:'READY',items:[{subjectReferenceNodeId:'00000000-0000-7000-8000-000000000001',status:'SELECTED',selectedValue:'123.456',selectionReason:'Synthetic evidence',entitlementDecision:'ALLOWED',stalenessStatus:'FRESH',pricingDateRequested:'2026-10-16',pricingDateUsed:'2026-10-16'}]}});
  }
  if(route.request().url().endsWith('/saved-policy'))return route.fulfill({json:{valuationPolicyId:'saved-policy',policyCode:'SAVED',displayName:'Saved version',versionNo:3,valuationCutId:'cut',validFrom:'2000-01-01',selectionMode:'STRICT',rules:[],defaultRules:[]}});
  return route.fulfill({json:{sources:[]}});
 });
 await page.goto('/?mode=policy');
 await page.getByRole('combobox',{name:'Policy version',exact:true}).selectOption('saved-policy');
 await expect(page.getByLabel('Policy code',{exact:true})).toHaveValue('SAVED');
 await page.getByLabel('Policy code',{exact:true}).fill('UNSAVED');
 await page.getByRole('tab',{name:'Preview',exact:true}).click();
 await page.getByLabel('Listing / reference UUIDs (up to 50)').fill('00000000-0000-7000-8000-000000000001');
 await page.getByRole('button',{name:'Preview saved version'}).click();
 await expect(page.getByRole('heading',{name:'Preview: READY'})).toBeVisible();
 expect(posts).toHaveLength(1);expect(posts[0].valuationPolicyId).toBe('saved-policy');
 await page.getByText('Input and target evidence',{exact:true}).click();
 await expect(page.locator('pre').filter({hasText:'Synthetic evidence'})).toBeVisible();
 await page.getByRole('tab',{name:'Configuration',exact:true}).click();
 await expect(page.getByLabel('Policy code',{exact:true})).toHaveValue('UNSAVED');
});

test('structured-product outline focuses real headings without hiding terms or warnings',async({page})=>{
 await page.route('**/api/**',route=>route.fulfill({status:503,json:{detail:'Synthetic catalogue unavailable'}}));
 await page.goto('/?mode=structured');
 await expect(page.getByRole('heading',{level:1,name:'New structured product'})).toBeVisible();
 await page.getByRole('link',{name:'Schedule and payoff',exact:true}).click();
 await expect(page.locator('#product-terms')).toBeFocused();
 await expect(page.getByRole('link',{name:'Events and submission'})).toHaveCount(0);
 await expect(page.getByText('This screen builds a draft contractual graph.',{exact:false})).toBeVisible();
 await expect(page.locator('#product-identity')).toBeVisible();
 await page.setViewportSize({width:390,height:844});
 await page.screenshot({path:'test-results/structured-product-mobile.png',fullPage:true});
});
