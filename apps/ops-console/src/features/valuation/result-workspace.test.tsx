import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {ResultWorkspace} from './result-workspace';
import {displayAmount} from './presentation';

const batch={batch_id:'batch',status:'STAGED',staged_by:'maker',reviews:[],
 summary:{scope:'MARKET_ONLY',resultFormat:'POSITION_V2' as const,marketPnl:'18809.844746795077',grossPnl:'18809.844746795077',netPnl:'18809.844746795077',
 openingValue:'638626.35760792854055110365',closingValue:'657436.2023547236174570024',executionValue:'0',reportingCurrencyId:'gbp',externalComparison:'NOT_COMPARED',limitations:[]},
 items:[{attribution_id:'a',trade_id:null,position_key:'position',subject_id:'listing',version:1,market_pnl:'18809.844746795077',components:{PRICE:'18290.046468352919',FX:'505.325912387842',PRICE_FX_CROSS:'14.472366054316'},
 evidence:{},lineage:[{trade_id:'original',event_id:'booked',role:'OPENING_EVIDENCE'}]}]};

it('makes positions scannable and retains a separate ledger inspector',()=>{
 const html=renderToStaticMarkup(<ResultWorkspace batch={batch} currency="GBP"/>);
 expect(html).toContain('<caption>Position attribution');
 expect(html).toContain('Inspect position');
 expect(html).toContain('18,809.84');
 expect(html).toContain('Position inspection');
 expect(html).toContain('href="/trades/original"');
 expect(html).toContain('Frozen inputs and method');
 expect(html).not.toContain('Trade null');
});

it('never discloses financial fields or ledger links when display evidence is denied',()=>{
 const html=renderToStaticMarkup(<ResultWorkspace batch={{...batch,summary:{...batch.summary,evidenceAccess:'DENIED',reason:'Current DISPLAY rights required'}}} currency="GBP"/>);
 expect(html).toContain('Current DISPLAY rights required');
 expect(html).not.toContain('18,809');expect(html).not.toContain('/trades/original');
 expect(html).not.toContain('Position attribution');
});

it('prominently discloses omitted daily interest rather than a zero accrual',()=>{
 const partial={...batch,summary:{...batch.summary,accrualCoverage:{mode:'OPTIONAL',suppliedCount:1,missingCount:2,
  missing:[{instrumentId:'bond',valueDate:'2026-10-06'},{instrumentId:'bond',valueDate:'2026-10-07'}]}}};
 const html=renderToStaticMarkup(<ResultWorkspace batch={partial} currency="GBP"/>);
 expect(html).toContain('Accrual not supplied—not included');
 expect(html).toContain('2 bond/date inputs');
 expect(html).toContain('not confirmed zero');
 const denied=renderToStaticMarkup(<ResultWorkspace batch={{...partial,summary:{...partial.summary,evidenceAccess:'DENIED'}}} currency="GBP"/>);
 expect(denied).not.toContain('2 bond/date inputs');
});

it('formats decimal strings for display without floating point precision loss',()=>{
 expect(displayAmount('999999999999999999.123456')).toBe('999,999,999,999,999,999.12');
 expect(displayAmount('-1.005')).toBe('-1.00');
 expect(displayAmount('1.015')).toBe('1.02');
 expect(displayAmount('unknown')).toBe('—');
});

it('shows server-evidenced split quantities without altering the original ledger',()=>{
 const adjusted={...batch,items:batch.items.map(item=>({...item,evidence:{splitAdjustments:[{
  quantity_before:'100',quantity_after:'110',event:{action_id:'issuer-action',review_id:'review-proof',
   ratio:'1.1',effective_date:'2026-06-08',evidence:{review:{entitlementScope:'BASIC_RATIO_ONLY'}}}}]}}))};
 const html=renderToStaticMarkup(<ResultWorkspace batch={adjusted} currency="GBP"/>);
 expect(html).toContain('Share quantity adjustments');
 expect(html).toContain('100 → 110');expect(html).toContain('2026-06-08');
 expect(html).toContain('review-proof');expect(html).toContain('/trades/original');
 const denied=renderToStaticMarkup(<ResultWorkspace batch={{...adjusted,summary:{...adjusted.summary,evidenceAccess:'DENIED'}}} currency="GBP"/>);
 expect(denied).not.toContain('review-proof');expect(denied).not.toContain('100 → 110');
});
