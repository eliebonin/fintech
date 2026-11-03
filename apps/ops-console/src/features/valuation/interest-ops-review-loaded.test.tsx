import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {beforeEach,expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({view:null as any}));
vi.mock('./use-interest-data',()=>({useInterestData:()=>({data:h.view,error:'',loading:false})}));
import {InterestOpsReview} from './interest-ops-review';
const row=(n:number)=>({instrumentId:`bond-${n}`,instrumentName:`Example bond ${n}`,currencyId:'gbp',currency:'GBP',amount:'1000.123456789012',sourceAmount:'1000.123456789012',decision:'ASSESSED',coveredDays:1,
 openingBalance:'10000',dailyIncrement:'1000.123456789012',sourceReference:'Statement',reason:'',notes:[],details:{},reconciliation:null,
 benchmark:{average:'1000.123456789012',coveredDays:5,requestedDays:5,startDate:'2026-10-15',endDate:'2026-10-19'},warning:{status:'IN_LINE',normalizedDaily:'1000.123456789012',changePercent:'0',partialBaseline:false,thresholdPercent:'25'}});
beforeEach(()=>{h.view={strategyId:'s',strategyLabel:'Example strategy',valueDate:'2026-10-20',stage:'DAILY',sourceHash:'a'.repeat(64),rows:Array.from({length:60},(_,n)=>row(n)),canWrite:true,review:null,reviewCurrent:false,dailyValidated:false,dailyReviewId:null};});
it('makes bulk scope the complete population rather than the displayed 25 rows',()=>{
 const html=renderToStaticMarkup(<InterestOpsReview stage="DAILY" initialStrategy="s" initialDate="2026-10-20"/>);
 expect(html).toContain('Validate all 60 daily assessments');expect(html).toContain('1–25 of 60');expect(html.match(/<tr>/g)).toHaveLength(26);
 expect(html).toContain('1,000.123456789012');expect(html).toContain('±25%');expect(html).toContain('In line');
});
it('labels reviewed gaps explicitly and enables the next stage without calling a missing amount zero',()=>{
 h.view.rows=[{...row(0),amount:null,sourceAmount:null,decision:'NOT_SUPPLIED',warning:null,reason:'Provider file absent'}];
 h.view.review={review_id:'receipt',state:'VALIDATED',revision:1,gap_count:1,recorded_at:'2026-10-20T18:00:00Z'};h.view.reviewCurrent=true;h.view.dailyValidated=true;
 const html=renderToStaticMarkup(<InterestOpsReview stage="DAILY" initialStrategy="s" initialDate="2026-10-20"/>);
 expect(html).toContain('Reviewed with gaps');expect(html).toContain('Missing input acknowledged');expect(html).toContain('Not supplied');expect(html).toContain('Continue to balance review');
});
it('shows the balance bridge and source/schedule context separately from the daily view',()=>{
 h.view.stage='BALANCE';h.view.rows=[{...row(0),notes:['Coupon scheduled today: review the reset.']}];h.view.dailyValidated=true;
 const html=renderToStaticMarkup(<InterestOpsReview stage="BALANCE" initialStrategy="s" initialDate="2026-10-20"/>);
 expect(html).toContain('Before update');expect(html).toContain('Daily accrual to add');expect(html).toContain('New balance');expect(html).toContain('10,000');expect(html).toContain('Coupon scheduled today');
 expect(html).not.toContain('Previous 5-day average</th>');
});
