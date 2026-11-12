import {test,expect} from './console-check';
const strategy='00000000-0000-7000-8000-000000000555',instrument='00000000-0000-7000-8000-000000000556';
for(const scenario of ['cash','physical','stale'])test(`option inspection ${scenario} stays read-only and source-bound`,async({page},testInfo)=>{
 const calls:{path:string;method:string}[]=[];
 await page.route('**/api/lifecycle/**',route=>{
  const req=route.request(),url=new URL(req.url()),path=url.pathname.replace('/api/lifecycle/','');calls.push({path,method:req.method()});
  if(req.method()!=='GET')return route.fulfill({status:405,json:{detail:'No option financial commands'}});
  if(path==='worklist/options')return route.fulfill({json:{items:[{strategyId:strategy,label:'Options strategy'}],total:1}});
  const quantities=[{currency:'USD',unit:'CONTRACTS',netQuantity:'-1250',grossQuantity:'1250',entries:1}];
  if(path==='worklist')return route.fulfill({json:{items:[{eventKey:'option-event',eventType:'OPTION_EXPIRY',instrumentType:'OPTION',strategyId:strategy,strategyName:'Options strategy',instrumentId:instrument,instrumentName:'Synthetic option',eventDate:'2027-09-17',eventAtUtc:null,milestoneKind:'EXPIRY',sourceFingerprint:'option-v1',maturityDate:null,status:'UPCOMING',attention:'INFORMATION',quantities,remainingEntries:1,selectedTier:1,maximumTier:3,processingMode:'MANUAL',reasons:['Expiry does not confirm exercise.'],actionLabel:'Inspect option',actionHref:`/instruments/${instrument}`,positionAssessed:true}],total:1,limit:25,offset:0,fromDate:url.searchParams.get('fromDate'),toDate:url.searchParams.get('toDate'),evaluatedAt:'2026-11-11T10:00:00Z',statusCounts:{UPCOMING:1},subscription:{maximumTier:3},instrumentDisplays:{},discoveryEventTypes:['OPTION_EXPIRY']}});
  if(path==='worklist/option')return route.fulfill({json:{eventKey:'option-event',strategyId:strategy,instrumentId:instrument,sourceFingerprint:scenario==='stale'?'revised-v2':'option-v1',evaluatedAt:'2026-11-11T10:00:00Z',milestoneKind:'EXPIRY',milestones:[{kind:'LAST_TRADE',date:'2027-09-16',atUtc:'2027-09-16T21:00:00Z'},{kind:'EXPIRY',date:'2027-09-17',atUtc:null}],optionTermsId:'term-1',termsVersion:1,definitionId:'definition-1',sourceApprovedAt:'2026-09-01T12:00:00Z',underlyingId:'underlying-1',underlyingName:'S&P 500 Index',optionType:'PUT',strike:'5800',strikeCurrency:'USD',exerciseStyle:scenario==='physical'?'AMERICAN':'EUROPEAN',settlementMethod:scenario==='physical'?'PHYSICAL':'CASH',settlementCurrency:scenario==='physical'?null:'USD',premiumCurrency:'USD',premiumMultiplier:'100',deliverableUnits:'100',positionAssessed:true,quantities,reasons:['Expiry does not confirm exercise.'],financialTreatment:'NOT_ASSESSED'}});
  return route.fulfill({status:404,json:{detail:'Unexpected route'}});
 });
 await page.goto('/?mode=lifecycle-worklist');await page.getByRole('combobox',{name:'Event type',exact:true}).selectOption('OPTION_EXPIRY');await page.getByRole('button',{name:'Apply filters',exact:true}).click();
 const trigger=page.getByRole('button',{name:'Inspect option for Synthetic option in Options strategy',exact:true});await trigger.click();
 const panel=page.getByRole('dialog',{name:'Inspect option',exact:true});await expect(panel).toBeVisible();
 if(scenario==='stale'){await expect(panel.getByRole('alert')).toContainText('Option source changed');await expect(panel.getByRole('region',{name:'Option contract'})).toHaveCount(0);}
 else{await expect(panel.getByRole('region',{name:'Option contract'})).toContainText('S&P 500 Index');await expect(panel.getByRole('region',{name:'Option contract'})).toContainText('5,800');await expect(panel).toContainText('-1,250');await expect(panel).toContainText('2027-09-16T21:00:00Z');await expect(panel).toContainText(scenario==='physical'?'Physical delivery':'Cash settlement');await expect(panel).toContainText(scenario==='physical'?'before expiry':'European');}
 await expect(panel.locator('form')).toHaveCount(0);await expect(panel.getByRole('button',{name:/Book|Prepare|Approve|Exercise|Assign|Settle/})).toHaveCount(0);expect(calls.every(c=>c.method==='GET')).toBe(true);
 if(scenario==='cash')await page.screenshot({path:testInfo.outputPath('option-inspection-desktop.png')});
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 if(scenario==='cash')await page.screenshot({path:testInfo.outputPath('option-inspection-mobile.png')});
 await page.keyboard.press('Escape');await expect(panel).toHaveCount(0);await expect(trigger).toBeFocused();await expect(page.getByRole('combobox',{name:'Event type',exact:true})).toHaveValue('OPTION_EXPIRY');
});
