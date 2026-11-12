import {test,expect} from './console-check';
const strategy='00000000-0000-7000-8000-000000000555';
const subscription={tenantId:'synthetic-tenant',maximumTier:3,configuredMaximumTier:3,revision:1,source:'MANUAL',moduleActive:true,notificationDiscoveryAvailable:false,entitlementFingerprint:'e'.repeat(64)};
const event={tenantId:'synthetic-tenant',strategyId:strategy,eventType:'BOND_MATURITY',maximumTier:3,selectedTier:2,subscriptionRevision:1,assistanceRevision:1,processingPolicyRevision:1,processingMode:'REVIEW',availableTiers:[0,1,2,3],status:'AVAILABLE',canConfigure:true,handlerSupported:true,notificationDiscoveryAvailable:false,operations:{}};

test('platform downgrade requires preview and blocked-workflow acknowledgement, preserving confirmed save on read failure',async({page})=>{
 let saved=false;const writes:unknown[]=[];
 await page.route('**/api/platform/**',route=>{
  if(route.request().method()==='PUT'){writes.push(route.request().postDataJSON());saved=true;return route.fulfill({json:{...subscription,maximumTier:1,configuredMaximumTier:1,revision:2}});}
  if(route.request().method()==='POST')return route.fulfill({json:{current:subscription,proposedMaximumTier:1,affectedEventCount:2,pendingPreparationCount:4,inputHash:'a'.repeat(64)}});
  return route.fulfill(saved?{status:503,json:{detail:'Synthetic read failure'}}:{json:subscription});
 });
 await page.goto('/?mode=lifecycle-subscription');await expect(page.getByText('Available:',{exact:false})).toBeVisible();
 const radioLayout=await page.getByRole('radio',{name:/Tier 1 — Notifications/}).evaluate(input=>{const rect=input.getBoundingClientRect();return {width:rect.width,height:rect.height,direction:getComputedStyle(input.parentElement!).flexDirection};});
 expect(radioLayout.width).toBeLessThanOrEqual(22);expect(radioLayout.height).toBeLessThanOrEqual(22);expect(radioLayout.direction).toBe('row');
 await page.getByRole('radio',{name:/Tier 1 — Notifications/}).check();await page.getByRole('button',{name:'Review subscription change',exact:true}).click();
 await expect(page.getByText('2 configured event(s)',{exact:false})).toBeVisible();
 await page.getByLabel('Subscription change reason').fill('Requested commercial downgrade');
 await page.getByRole('button',{name:'Confirm subscription change'}).click();expect(writes).toHaveLength(0);
 await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Confirm subscription change'}).click();
 await expect(page.getByRole('status')).toContainText('subscription saved');await expect(page.getByRole('alert')).toContainText('was saved, but refresh failed');
 expect(writes).toHaveLength(1);await expect(page.getByRole('button',{name:'Confirm subscription change'})).toHaveCount(0);
});

test('strategy changes require review and preserve intent on a configuration conflict',async({page})=>{
 const writes:unknown[]=[];
 await page.route('**/api/lifecycle/assistance**',route=>{
  if(route.request().method()==='POST'){writes.push(route.request().postDataJSON());return route.fulfill({status:409,json:{detail:'Configuration changed; reload and review again.'}});}
  const type=new URL(route.request().url()).searchParams.get('eventType');return route.fulfill({json:{...event,eventType:type}});
 });
 await page.goto('/?mode=lifecycle-strategy');await page.getByRole('button',{name:'Configure Bond maturity',exact:true}).click();
 await page.getByRole('radio',{name:/Tier 1 — Notifications/}).check();await page.getByLabel('Reason for assistance change').fill('Keep notifications only');await page.getByRole('button',{name:'Review assistance change',exact:true}).click();
 expect(writes).toHaveLength(0);await page.getByRole('button',{name:'Save assistance setting',exact:true}).click();
 await expect(page.getByRole('alert')).toContainText('Configuration changed');await expect(page.getByLabel('Reason for assistance change')).toHaveValue('Keep notifications only');
 expect(writes[0]).toMatchObject({selectedTier:1,expectedSubscriptionRevision:1,expectedRevision:1});
});

test('downgrade review keeps valid choices and requires explicit all-to-zero confirmation',async({page})=>{
 const requests:any[]=[];const saves:any[]=[];
 const rows=[3,2,1,0].map((tier,index)=>({strategyId:strategy.replace(/555$/,String(555+index)),strategyLabel:`Strategy ${index+1}`,eventType:'BOND_MATURITY',beforeTier:tier,afterTier:tier,revision:1,changed:false}));
 await page.route('**/api/lifecycle/assistance/**',route=>{
  const request=route.request();
  if(request.method()==='GET')return route.fulfill({json:{items:[{strategyId:strategy,label:'Strategy 1',code:'S1',canConfigure:true,configuredEvents:{BOND_MATURITY:3}}],total:1,offset:0,limit:25,subscription,canConfigureAll:true}});
  const body=request.postDataJSON();
  if(request.url().endsWith('/apply')){saves.push(body);return route.fulfill({json:{updatedCount:3,unchangedCount:1,commercialSubscriptionChanged:false,message:'Strategy settings saved. The platform subscription is unchanged.'}});}
  requests.push(body);const items=rows.map(row=>{const afterTier=body.replacement==='KEEP'?row.beforeTier:body.scope==='ALL_CONFIGURED'?body.targetTier:row.beforeTier>body.proposedMaximumTier?(body.replacement==='EXPLICIT'?body.targetTier:body.proposedMaximumTier):row.beforeTier;return {...row,afterTier,changed:afterTier!==row.beforeTier};});
  return route.fulfill({json:{items,changedCount:items.filter(row=>row.changed).length,unchangedCount:items.filter(row=>!row.changed).length,blockedCount:items.filter(row=>row.afterTier>body.proposedMaximumTier).length,inputHash:'b'.repeat(64),subscriptionRevision:1,proposedMaximumTier:body.proposedMaximumTier,commercialSubscriptionChanged:false}});
 });
 await page.goto('/?mode=lifecycle-downgrade');await page.getByLabel('Proposed subscription ceiling').selectOption('2');
 await page.getByRole('button',{name:'Preview downgrade settings'}).click();let table=page.getByRole('table',{name:'Proposed strategy and event changes'});await expect(table).toContainText('Tier 1 · unchanged');expect(requests.at(-1)).toMatchObject({scope:'ABOVE_NEW_CEILING',replacement:'HIGHEST_AVAILABLE',proposedMaximumTier:2});
 await page.getByRole('radio',{name:/Choose a fallback for affected settings/}).check();await page.getByLabel('Replacement assistance tier').selectOption('1');await page.getByRole('button',{name:'Preview downgrade settings'}).click();await expect(table).toContainText('Tier 1 · unchanged');
 await page.getByRole('radio',{name:/Leave settings unchanged/}).check();await page.getByRole('button',{name:'Preview downgrade settings'}).click();await expect(page.getByText('No strategy settings will be saved.',{exact:false})).toBeVisible();await expect(page.getByRole('button',{name:'Save reviewed strategy settings'})).toHaveCount(0);
 await page.getByRole('radio',{name:/Set all configured events to one tier/}).check();await page.getByLabel('Replacement assistance tier').selectOption('0');await page.getByRole('button',{name:'Preview downgrade settings'}).click();
 await page.getByLabel('Reason for downgrade preparation').fill('Explicit reset to manual');await page.getByRole('button',{name:'Save reviewed strategy settings'}).click();expect(saves).toHaveLength(0);
 await page.getByRole('checkbox',{name:/I confirm replacing all/}).check();await page.getByRole('button',{name:'Save reviewed strategy settings'}).click();await expect(page.getByRole('status').filter({hasText:'subscription is unchanged'})).toBeVisible();expect(saves[0]).toMatchObject({scope:'ALL_CONFIGURED',targetTier:0,confirmReplaceAllowed:true});
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test('futures settings separate supported notifications from the commercial ceiling',async({page})=>{
 const writes:any[]=[];
 await page.route('**/api/lifecycle/assistance**',route=>{
  const request=route.request();if(request.method()==='POST'){writes.push(request.postDataJSON());return route.fulfill({json:{...event,eventType:'FUTURE_EXPIRY',selectedTier:1,availableTiers:[0,1],handlerSupported:false}});}
  const type=new URL(request.url()).searchParams.get('eventType');return route.fulfill({json:type==='FUTURE_EXPIRY'?{...event,eventType:type,selectedTier:0,availableTiers:[0,1],handlerSupported:false,processingMode:'MANUAL',notificationDiscoveryAvailable:true}:{...event,eventType:type}});
 });
 await page.goto('/?mode=lifecycle-strategy');await page.getByRole('button',{name:'Configure Futures milestones',exact:true}).click();
 await expect(page.getByRole('radio',{name:/Tier 1 — Notifications/})).toBeEnabled();await expect(page.getByRole('radio',{name:/Tier 2 — Assisted preparation/})).toBeDisabled();
 await expect(page.getByRole('group',{name:'Selected strategy assistance'})).toContainText('Not implemented for this event.');
 await page.getByRole('radio',{name:/Tier 1 — Notifications/}).check();await page.getByLabel('Reason for assistance change').fill('Track open future deadlines');
 await page.getByRole('button',{name:'Review assistance change',exact:true}).click();expect(writes).toHaveLength(0);await page.getByRole('button',{name:'Save assistance setting',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('saved');expect(writes[0]).toMatchObject({eventType:'FUTURE_EXPIRY',selectedTier:1});
});

test('option notification configuration cannot select unsupported financial assistance',async({page})=>{
 const writes:any[]=[];
 await page.route('**/api/lifecycle/assistance**',route=>{
  const request=route.request();if(request.method()==='POST'){writes.push(request.postDataJSON());return route.fulfill({json:{...event,eventType:'OPTION_EXPIRY',selectedTier:1,availableTiers:[0,1],handlerSupported:false}});}
  const type=new URL(request.url()).searchParams.get('eventType');return route.fulfill({json:type==='OPTION_EXPIRY'?{...event,eventType:type,selectedTier:0,availableTiers:[0,1],handlerSupported:false,processingMode:'MANUAL',notificationDiscoveryAvailable:true}:{...event,eventType:type}});
 });
 await page.goto('/?mode=lifecycle-strategy');await page.getByRole('button',{name:'Configure Option expiry',exact:true}).click();
 await expect(page.getByRole('radio',{name:/Tier 1 — Notifications/})).toBeEnabled();await expect(page.getByRole('radio',{name:/Tier 2 — Assisted preparation/})).toBeDisabled();
 await expect(page.getByRole('group',{name:'Selected strategy assistance'})).toContainText('Not implemented for this event.');
 await page.getByRole('radio',{name:/Tier 1 — Notifications/}).check();await page.getByLabel('Reason for assistance change').fill('Review option deadlines');
 await page.getByRole('button',{name:'Review assistance change',exact:true}).click();expect(writes).toHaveLength(0);await page.getByRole('button',{name:'Save assistance setting',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('saved');expect(writes[0]).toMatchObject({eventType:'OPTION_EXPIRY',selectedTier:1});
});

test('structured informational configuration cannot select unsupported financial assistance',async({page})=>{
 const writes:any[]=[];
 await page.route('**/api/lifecycle/assistance**',route=>{
  const request=route.request();if(request.method()==='POST'){writes.push(request.postDataJSON());return route.fulfill({json:{...event,eventType:'STRUCTURED_OBSERVATION',selectedTier:1,availableTiers:[0,1],handlerSupported:false}});}
  const type=new URL(request.url()).searchParams.get('eventType');return route.fulfill({json:type==='STRUCTURED_OBSERVATION'?{...event,eventType:type,selectedTier:0,availableTiers:[0,1],handlerSupported:false,processingMode:'MANUAL',notificationDiscoveryAvailable:true}:{...event,eventType:type}});
 });
 await page.goto('/?mode=lifecycle-strategy');await page.getByRole('button',{name:'Configure Structured product schedules',exact:true}).click();
 await expect(page.getByRole('radio',{name:/Tier 1 — Notifications/})).toBeEnabled();await expect(page.getByRole('radio',{name:/Tier 2 — Assisted preparation/})).toBeDisabled();
 await expect(page.getByRole('group',{name:'Selected strategy assistance'})).toContainText('Not implemented for this event.');
 await page.getByRole('radio',{name:/Tier 1 — Notifications/}).check();await page.getByLabel('Reason for assistance change').fill('Show sourced observations only');
 await page.getByRole('button',{name:'Review assistance change',exact:true}).click();expect(writes).toHaveLength(0);await page.getByRole('button',{name:'Save assistance setting',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('saved');expect(writes[0]).toMatchObject({eventType:'STRUCTURED_OBSERVATION',selectedTier:1});
});
