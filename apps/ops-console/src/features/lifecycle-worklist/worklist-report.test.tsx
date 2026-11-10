import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {WorklistReport} from './worklist-report';
const event={eventKey:'event-key',eventType:'BOND_MATURITY',instrumentType:'BOND',strategyId:'strategy-uuid',strategyName:'GBP Income',instrumentId:'instrument-uuid',instrumentName:'Treasury Gilt',identifier:'GB00TEST',maturityDate:'2026-11-05',status:'BLOCKED',attention:'ACTIONABLE',quantities:[],remainingEntries:null,selectedTier:2,maximumTier:3,processingMode:'REVIEW',reasons:['Original position evidence is missing'],actionLabel:'Review blocked event',actionHref:'/trades/lifecycle?strategyId=strategy-uuid',positionAssessed:false};
it('shows unknown exposure and readable event identity without an open inspection panel',()=>{
 const result={items:[event],total:31,offset:0,limit:25,evaluatedAt:'2026-11-05T10:00:00Z',fromDate:'2026-11-01',toDate:'2026-11-30',statusCounts:{BLOCKED:31},instrumentDisplays:{}} as any;
 const html=renderToStaticMarkup(<WorklistReport result={result} scopeLabel="GBP Income" onInspect={()=>{}} onPage={()=>{}} onLimit={()=>{}}/>);
 expect(html).toContain('Not assessed');expect(html).toContain('Treasury Gilt');expect(html).toContain('31 events');expect(html).toContain('Lifecycle events');expect(html).not.toContain('Event inspection');expect(html).not.toContain('0 nominal');
});

it('directs a disabled strategy to its own assistance settings without implying missing holdings',()=>{
 const result={items:[],total:0,offset:0,limit:25,evaluatedAt:'2026-11-05T10:00:00Z',fromDate:'2026-11-01',toDate:'2026-11-30',statusCounts:{},unavailableReason:'Bond maturity notifications are not enabled for this strategy.'} as any;
 const html=renderToStaticMarkup(<WorklistReport result={result} scopeLabel="GBP Income" settingsHref="/strategies/selected?view=overview" onInspect={()=>{}} onPage={()=>{}} onLimit={()=>{}}/>);
 expect(html).toContain('not enabled for this strategy');expect(html).toContain('href="/strategies/selected?view=overview"');expect(html).not.toContain('No events match');
});
