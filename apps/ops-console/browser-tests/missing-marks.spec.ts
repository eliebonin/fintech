import {test,expect} from './console-check';
const batchId='00000000-0000-7000-8000-000000000001',subject='00000000-0000-7000-8000-000000000002',series='00000000-0000-7000-8000-000000000003',inputKey='a'.repeat(64);
const batch={batch_id:batchId,status:'STAGED',staged_by:'maker',reviews:[],items:[],summary:{scope:'MARKET_ONLY',resultFormat:'POSITION_V2',marketPnl:'0',netPnl:'0',openingValue:'0',closingValue:'0',executionValue:'0',reportingCurrencyId:'GBP',externalComparison:'NOT_COMPARED',limitations:[],requiredInputsComplete:false,hasCalculatedContributions:false,inputCoverage:{missingCount:1,affectedPositionCount:1,unpricedPositions:[{positionKey:'position',subjectId:subject,product:'FX_FORWARD',pnl:null,bucket:{opening_quantity:'1000000',closing_quantity:'1000000'},inputKeys:[inputKey]}],gaps:[{inputKey,role:'PRICE',request:{valuation_date:'2026-10-19'},selection:{pricing_date_requested:'2026-10-19'}}]}},presentation:{references:{[subject]:'EUR/GBP forward'},currencies:{},datasets:{},rules:{},users:{},context:{},totals:{interest:null,other:null},pendingAmendments:0}};
const gap={inputKey,subjectId:subject,valueDate:'2026-10-19',role:'PRICE',notice:null,options:[{seriesId:series,label:'Synthetic closing rate · GBP',currency:'GBP',dirtyBond:false}]};

test('all-unpriced report shows unavailable P&L rather than a zero total',async({page})=>{
 await page.route('**/api/test-instrument-report',route=>route.fulfill({json:batch}));
 await page.goto('/?mode=instrument-report');
 await expect(page.getByText('Calculated subtotal · incomplete')).toBeVisible();
 await expect(page.getByRole('table',{name:'Positions with missing required inputs'})).toContainText('1,000,000');
 await expect(page.getByText('P&L unavailable')).toBeVisible();
 await expect(page.getByText('This is a calculated, evidenced zero result.')).toHaveCount(0);
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test('retains uncertain mark request exactly and requires independent review',async({page})=>{
 let status='PENDING',posted=false;const writes:{key:string|null;body:unknown}[]=[];
 await page.route('**/api/test-instrument-report',route=>route.fulfill({json:batch}));
 await page.route(`**/api/valuation/batches/${batchId}/mark-overrides`,route=>route.fulfill({json:{gaps:[gap],canRequest:true,canReview:false,requests:posted?[{requestId:batchId,inputKey,subjectId:subject,valueDate:'2026-10-19',value:'0.841234567891',currency:'GBP',reason:'Counterparty supplied quote',sourceReference:'Synthetic confirmation',requestedBy:'maker',reviewedBy:null,reviewComment:null,status,canReview:false,canWithdraw:false}]:[]}}));
 await page.route('**/api/valuation/mark-overrides',async route=>{
  writes.push({key:route.request().headers()['idempotency-key'],body:route.request().postDataJSON()});posted=true;
  await route.fulfill(writes.length===1?{status:503,json:{detail:'Outcome unknown'}}:{status:201,json:{requestId:batchId}});
 });
 await page.goto('/?mode=mark-review');await page.getByText('EUR/GBP forward · 2026-10-19 · Price / rate',{exact:true}).click();
 await page.getByLabel('Exact mark · GBP').fill('0.841234567891');await page.getByLabel('Reason',{exact:true}).fill('Counterparty supplied quote');await page.getByLabel('Source / supporting reference').fill('Synthetic confirmation');
 await page.getByLabel('I checked the currency, units and quote convention against the booked position.').check();
 await page.getByRole('button',{name:'Request independent mark review'}).click();
 await expect(page.getByRole('alert')).toContainText('Outcome unknown');
 await page.getByRole('button',{name:'Retry unchanged mark request'}).click();
 await expect(page.getByText('An independent user and real operator with review permission must decide this request.')).toBeVisible();
 expect(writes).toHaveLength(2);expect(writes[1]).toEqual(writes[0]);
 await expect(page.getByRole('button',{name:'Approve mark',exact:true})).toHaveCount(0);
 await expect(page.getByText('Approved marks apply only after a new calculation',{exact:false})).toBeVisible();
});

test('independent mark approval keeps recalculation explicit',async({page})=>{
 let approved=false;
 await page.route('**/api/test-instrument-report',route=>route.fulfill({json:batch}));
 await page.route(`**/api/valuation/batches/${batchId}/mark-overrides`,route=>route.fulfill({json:{gaps:[gap],canRequest:false,canReview:true,requests:[{requestId:batchId,inputKey,subjectId:subject,valueDate:'2026-10-19',value:'0.84',currency:'GBP',reason:'Reviewed synthetic source',sourceReference:'Test confirmation',requestedBy:'maker',reviewedBy:approved?'reviewer':null,reviewComment:approved?'Checked source':null,status:approved?'APPROVED':'PENDING',canReview:!approved,canWithdraw:approved}]}}));
 await page.route(`**/api/valuation/mark-overrides/${batchId}/approve`,async route=>{expect(route.request().postDataJSON()).toEqual({comment:'Checked source'});approved=true;await route.fulfill({json:{decisionId:batchId}});});
 await page.goto('/?mode=mark-review');await page.getByLabel('Review explanation').fill('Checked source');await page.getByRole('button',{name:'Approve mark',exact:true}).click();
 await expect(page.getByRole('button',{name:'Withdraw approved mark'})).toBeVisible();
 await expect(page.getByText('Approved marks apply only after a new calculation',{exact:false})).toBeVisible();
});
