import {test,expect} from './console-check';

const coupon={cashflow_id:'coupon',cashflow_key:'Final coupon',cashflow_type:'COUPON',accrual_start:'2026-04-15',accrual_end:'2026-10-15',payment_date:'2026-10-15',coupon_rate:'0.05',amount_per_100:'2.5',amount_formula:null};
const principal={cashflow_id:'principal',cashflow_key:'Redemption',cashflow_type:'PRINCIPAL',accrual_start:null,accrual_end:null,payment_date:'2026-10-15',coupon_rate:null,amount_per_100:'100',amount_formula:null};
const schedule={schedule_id:'schedule',revision:1,source_reference:'Synthetic terms',currencyCode:'USD',cashflows:[coupon,principal]};
async function mock(page:import('@playwright/test').Page,principalOnly=false){
 await page.route('**/api/lifecycle/coupons/options*',route=>route.fulfill({json:{strategies:[{id:'strategy',label:'Synthetic strategy'}],currencies:[{id:'usd',label:'USD'}],accounts:[],bonds:[{id:'bond',label:'Synthetic bond'}],permissions:{REFERENCE_APPROVE:true,LIFECYCLE_BOOK:true}}}));
 await page.route('**/api/lifecycle/coupons/schedule?*',route=>route.fulfill({json:{schedule:{...schedule,cashflows:principalOnly?[principal]:schedule.cashflows},history:[{schedule_id:'schedule',revision:1}]}}));
 await page.route('**/api/lifecycle/coupons/payments?*',route=>route.fulfill({json:{items:[],total:0}}));
 await page.goto('/?mode=coupon');
 await page.getByRole('combobox',{name:'Strategy',exact:true}).selectOption('strategy');
 await page.getByLabel('Canonical bond').fill('bond');
 await page.getByRole('button',{name:'Load bond schedule'}).click();
 await expect(page.getByRole('table',{name:'Contractual expectations — not payment confirmations'})).toBeVisible();
}

test('same-day coupon and principal are readable; editor submits both while receipts select only coupons',async({page})=>{
 await mock(page);
 const table=page.getByRole('table',{name:'Contractual expectations — not payment confirmations'});
 await expect(table.locator('tbody tr')).toHaveCount(2);
 await expect(table).toContainText('Principal');await expect(page.getByText(/Amounts in USD, per 100 original nominal/)).toBeVisible();
 const receipt=page.getByRole('combobox',{name:'Coupon period',exact:true});
 await expect(receipt.locator('option')).toHaveCount(1);await expect(receipt.locator('option')).toHaveAttribute('value','coupon');
 await expect(receipt.locator('option')).toHaveText('Final coupon — scheduled 2026-10-15');
 await page.getByText('Maintain sourced schedule',{exact:true}).click();
 const form=page.locator('form.bond-cashflow-editor');
 await form.getByLabel('Source / document reference').fill('Updated synthetic source');await form.getByLabel('Reason',{exact:true}).fill('Verified full schedule');
 await form.getByRole('checkbox').check();
 let body:Record<string,unknown>|undefined;
 await page.route('**/api/lifecycle/coupons/schedules',async route=>{body=route.request().postDataJSON();await route.fulfill({json:schedule});});
 await form.getByRole('button',{name:'Save new schedule revision'}).click();
 await expect(page.getByRole('status').filter({hasText:'Evidence saved'})).toBeVisible();
 expect(body?.cashflows).toEqual([
  {cashflowKey:'Final coupon',cashflowType:'COUPON',accrualStart:'2026-04-15',accrualEnd:'2026-10-15',paymentDate:'2026-10-15',couponRate:'0.05',amountPer100:'2.5'},
  {cashflowKey:'Redemption',cashflowType:'PRINCIPAL',paymentDate:'2026-10-15',amountPer100:'100'},
 ]);
 await page.screenshot({path:'test-results/bond-cashflow-schedule.png',fullPage:true});
});

test('principal-only schedules offer no coupon receipt and changing row type clears coupon economics',async({page})=>{
 await mock(page,true);
 await expect(page.getByRole('button',{name:'Confirm receipt',exact:true})).toHaveCount(0);
 await page.getByText('Maintain sourced schedule',{exact:true}).click();
 const form=page.locator('form.bond-cashflow-editor');
 await expect(form.getByLabel('Accrual start')).toHaveCount(0);
 await form.getByRole('button',{name:'Add cashflow',exact:true}).click();
 const newRow=form.locator('fieldset.bond-cashflow-row').nth(1);
 await newRow.getByLabel('Coupon rate').fill('0.05');await newRow.getByLabel('Amount per 100 original nominal',{exact:true}).fill('2.5');
 await newRow.getByRole('combobox',{name:'Payment type'}).selectOption('PRINCIPAL');
 await expect(newRow.getByLabel('Accrual start')).toHaveCount(0);await expect(newRow.getByLabel('Coupon rate')).toHaveCount(0);
 await expect(newRow.getByLabel('Amount per 100 original nominal',{exact:true})).toHaveValue('');
 await page.setViewportSize({width:390,height:844});
 await expect(form.getByRole('button',{name:'Save new schedule revision'})).toBeVisible();
 expect(await form.evaluate(el=>el.scrollWidth<=el.clientWidth+1)).toBe(true);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await page.screenshot({path:'test-results/bond-cashflow-schedule-mobile.png',fullPage:true});
});
