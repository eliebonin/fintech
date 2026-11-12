import {test,expect} from './console-check';
const strategy='00000000-0000-7000-8000-000000000555',instrument='00000000-0000-7000-8000-000000000556';
for(const stale of [false,true])test(stale?'future inspection rejects revised source evidence':'future notifications inspect signed contracts without financial controls',async({page},testInfo)=>{
 const calls:{path:string;method:string}[]=[];
 await page.route('**/api/lifecycle/**',route=>{
  const req=route.request(),url=new URL(req.url()),path=url.pathname.replace('/api/lifecycle/','');calls.push({path,method:req.method()});
  if(req.method()!=='GET')return route.fulfill({status:405,json:{detail:'Read-only future'}});
  if(path==='worklist/options')return route.fulfill({json:{items:[{strategyId:strategy,label:'Futures strategy'}],total:1}});
  const quantities=[{currency:'USD',unit:'CONTRACTS',netQuantity:'-1250',grossQuantity:'1250',entries:1}];
  if(path==='worklist')return route.fulfill({json:{items:[{eventKey:'future-event',eventType:'FUTURE_EXPIRY',instrumentType:'FUTURE',strategyId:strategy,strategyName:'Futures strategy',instrumentId:instrument,instrumentName:'Synthetic physical future',eventDate:'2027-03-19',eventAtUtc:'2027-03-19T13:30:00Z',milestoneKind:'LAST_TRADE',sourceFingerprint:'source-v1',maturityDate:null,status:'UPCOMING',attention:'INFORMATION',quantities,remainingEntries:1,selectedTier:1,maximumTier:3,processingMode:'MANUAL',reasons:['Notifications only.'],actionLabel:'Inspect future',actionHref:`/instruments/${instrument}`,positionAssessed:true}],total:1,limit:25,offset:0,fromDate:url.searchParams.get('fromDate'),toDate:url.searchParams.get('toDate'),evaluatedAt:'2026-11-11T10:00:00Z',statusCounts:{UPCOMING:1},subscription:{maximumTier:3},instrumentDisplays:{},discoveryEventTypes:['FUTURE_EXPIRY']}});
  if(path==='worklist/future')return route.fulfill({json:{eventKey:'future-event',strategyId:strategy,instrumentId:instrument,sourceFingerprint:stale?'revised-v2':'source-v1',evaluatedAt:'2026-11-11T10:00:00Z',milestoneKind:'LAST_TRADE',milestones:[{kind:'LAST_TRADE',date:'2027-03-19',atUtc:'2027-03-19T13:30:00Z'},{kind:'DELIVERY_START',date:'2027-03-21',atUtc:null}],settlementMethod:'PHYSICAL',familyName:'Synthetic crypto family',contractMonth:'2027-03-01',conventionId:'source-1',conventionVersion:1,sourceReference:'Synthetic exchange specification',sourceApprovedAt:'2026-09-01T12:00:00Z',quantityUnit:'CONTRACTS',monetaryMultiplier:'5',quoteFactor:'1',positionAssessed:true,quantities,reasons:['No financial effects.'],firstNoticeDate:null,financialTreatment:'NOT_ASSESSED'}});
  return route.fulfill({status:404,json:{detail:'Unexpected route'}});
 });
 await page.goto('/?mode=lifecycle-worklist');await page.getByRole('combobox',{name:'Event type',exact:true}).selectOption('FUTURE_EXPIRY');await page.getByRole('button',{name:'Apply filters',exact:true}).click();
 const trigger=page.getByRole('button',{name:'Inspect future for Synthetic physical future in Futures strategy',exact:true});await trigger.click();
 const panel=page.getByRole('dialog',{name:'Inspect future',exact:true});await expect(panel).toBeVisible();
 if(stale){await expect(panel.getByRole('alert')).toContainText('Futures source changed');await expect(panel.getByRole('region',{name:'Futures contract'})).toHaveCount(0);}
 else{await expect(panel.getByRole('region',{name:'Futures contract'})).toContainText('Physical delivery');await expect(panel).toContainText('2027-03-19T13:30:00Z');await expect(panel).toContainText('-1,250');await expect(panel).toContainText('First-notice date');await expect(panel).toContainText('Not recorded');}
 await expect(panel.locator('form')).toHaveCount(0);await expect(panel.getByRole('button',{name:/Book|Prepare|Approve|Confirm/})).toHaveCount(0);
 expect(calls.every(c=>c.method==='GET')).toBe(true);
 if(!stale)await page.screenshot({path:testInfo.outputPath('future-inspection-desktop.png')});
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 if(!stale)await page.screenshot({path:testInfo.outputPath('future-inspection-mobile.png')});
 await page.keyboard.press('Escape');await expect(panel).toHaveCount(0);await expect(trigger).toBeFocused();await expect(page.getByRole('combobox',{name:'Event type',exact:true})).toHaveValue('FUTURE_EXPIRY');
});
