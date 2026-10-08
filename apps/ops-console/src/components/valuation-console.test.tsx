import React,{useState} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it,vi} from 'vitest';
vi.mock('react',async()=>{const actual=await vi.importActual<typeof import('react')>('react');return {...actual,useState:vi.fn(actual.useState)};});
import {ValuationConsole} from './valuation-console';

it('keeps read-only users out of calculation and publication controls',()=>{
 const html=renderToStaticMarkup(<ValuationConsole canManage={false} actorId="viewer"/>);
 expect(html).toContain('Run history');expect(html).toContain('Read-only');
 expect(html).not.toContain('Calculate and stage');expect(html).not.toContain('Publish reviewed');
});
it('labels the economic scope and excludes full NAV claims',()=>{
 const html=renderToStaticMarkup(<ValuationConsole canManage actorId="admin"/>);
 expect(html).toContain('Calculate and stage');expect(html).toContain('Opening cutoff');
 expect(html).toContain('Information cutoff');expect(html).toContain('market-only');
 expect(html).toContain('income');expect(html).toContain('not full fund NAV');
});
it('explains restricted evidence and hides review and financial controls',async()=>{
 const real=(await vi.importActual<typeof import('react')>('react')).useState;
 const detail={attempt:{status:'COMPLETED',correlation_id:'safe-correlation'},events:[],batch:{batch_id:'batch',status:'STAGED',items:[],reviews:[],
  summary:{scope:'MARKET_ONLY',evidenceAccess:'DENIED',reason:'Current DISPLAY rights are required.'}}};
 // Only the loaded detail state is supplied; all other hooks stay real.
 vi.mocked(useState).mockImplementationOnce(real).mockImplementationOnce(real).mockImplementationOnce(real).mockImplementationOnce(real)
  .mockImplementationOnce(()=>[detail,()=>{}] as unknown as ReturnType<typeof useState>);
 const html=renderToStaticMarkup(<ValuationConsole canManage actorId="admin"/>);
 expect(html).toContain('Current DISPLAY rights are required.');
 expect(html).not.toContain('Save explanation');expect(html).not.toContain('Publish reviewed');
 expect(html).not.toContain('Opening securities value');
});

it('renders position-owned results and original execution links without fake trade owners',async()=>{
 const real=(await vi.importActual<typeof import('react')>('react')).useState;
 const detail={attempt:{status:'COMPLETED',correlation_id:'position-run'},events:[],batch:{batch_id:'batch',status:'STAGED',staged_by:'admin',reviews:[],
  summary:{scope:'MARKET_ONLY',resultFormat:'POSITION_V2',marketPnl:'20',openingValue:'0',closingValue:'0',executionValue:'-20',reportingCurrencyId:'gbp',externalComparison:'NOT_COMPARED'},
  items:[{attribution_id:'attr',trade_id:null,position_key:'position-key',subject_id:'listing-id',version:1,market_pnl:'20',components:{PRICE:'20'},evidence:{},
   lineage:[{trade_id:'original-trade',event_id:'booked-event',role:'PERIOD_EXECUTION'}]}]}};
 vi.mocked(useState).mockImplementationOnce(real).mockImplementationOnce(real).mockImplementationOnce(real).mockImplementationOnce(real)
  .mockImplementationOnce(()=>[detail,()=>{}] as unknown as ReturnType<typeof useState>);
 const html=renderToStaticMarkup(<ValuationConsole canManage actorId="admin"/>);
 expect(html).toContain('Position listing-id');expect(html).toContain('original-trade');
 expect(html).toContain('/trades/original-trade');expect(html).not.toContain('Trade null');
});

it('distinguishes a calculated empty position result from missing run history',async()=>{
 const real=(await vi.importActual<typeof import('react')>('react')).useState;
 const detail={attempt:{status:'COMPLETED',correlation_id:'empty-run'},events:[],batch:{batch_id:'batch',status:'STAGED',staged_by:'admin',reviews:[],items:[],
  summary:{resultFormat:'POSITION_V2',marketPnl:'0',openingValue:'0',closingValue:'0',executionValue:'0',reportingCurrencyId:'gbp',externalComparison:'NOT_COMPARED'}}};
 vi.mocked(useState).mockImplementationOnce(real).mockImplementationOnce(real).mockImplementationOnce(real).mockImplementationOnce(real)
  .mockImplementationOnce(()=>[detail,()=>{}] as unknown as ReturnType<typeof useState>);
 const html=renderToStaticMarkup(<ValuationConsole canManage actorId="admin"/>);
 expect(html).toContain('No relevant positions or period movements');
});
