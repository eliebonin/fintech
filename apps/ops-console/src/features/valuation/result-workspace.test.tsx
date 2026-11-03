import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {ResultWorkspace as ReportWorkspace} from './result-workspace';
import {displayAmount} from './presentation';

const ResultWorkspace=(props:Omit<React.ComponentProps<typeof ReportWorkspace>,'activeTab'|'onNavigate'>)=><ReportWorkspace {...props} activeTab="breakdown" onNavigate={()=>{}}/>;

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
 expect(html).toContain('Close position details');
 expect(html).toContain('aria-expanded="false"');
 expect(html).toMatch(/<aside[^>]*hidden=""[^>]*aria-label="Position inspection"/);
 expect(html).toContain('pnl-result-grid pnl-inspector-closed');
 expect(html).not.toContain('Trade null');
});

it('uses an icon-only close control while retaining an accessible action name',()=>{
 const html=renderToStaticMarkup(<ResultWorkspace batch={batch} currency="GBP"/>);
 const close=html.match(/<button[^>]*aria-label="Close position details"[^>]*>[\s\S]*?<\/button>/)![0];
 expect(close).not.toContain('>Close details<');
 expect(close).toContain('aria-hidden="true"');
 expect(close).toContain('pnl-inspector-close');
});

it('displays canonical instrument types and offers all full-result types including off-page and unavailable rows',()=>{
 const many={...batch,items:Array.from({length:27},(_,index)=>({...batch.items[0],attribution_id:`a${index}`,subject_id:`s${index}`})),
  presentation:{references:{},currencies:{},datasets:{},rules:{},users:{},context:{},totals:{interest:null,other:null},pendingAmendments:0,
   instrumentTypes:Object.fromEntries(Array.from({length:26},(_,i)=>[`s${i}`,i===25?{code:'BOND',label:'Bond'}:{code:'EQUITY',label:'Equity'}]))}};
 const html=renderToStaticMarkup(<ResultWorkspace batch={many} currency="GBP"/>);
 expect(html).toContain('<th scope="col" class="pnl-instrument-type">Instrument type</th>');
 expect(html).toContain('<td class="pnl-instrument-type">Equity</td>');
 expect(html).toContain('<option value="" selected="">All instrument types</option>');
 expect(html).toContain('<option value="BOND">Bond</option>');
 expect(html).toContain('<option value="EQUITY">Equity</option>');
 expect(html).toContain('<option value="UNKNOWN">Type unavailable</option>');
 expect(html).toContain('1–25 of 27 positions');
});

it('defaults to 25 position rows and offers 50, 100 and all without changing whole-result totals',()=>{
 const many={...batch,items:Array.from({length:127},(_,index)=>({...batch.items[0],attribution_id:`a${index}`,subject_id:`listing${index}`}))};
 const html=renderToStaticMarkup(<ResultWorkspace batch={many} currency="GBP"/>);
 const table=html.match(/<table class="pnl-table pnl-ops-table">[\s\S]*?<\/table>/)![0];
 expect(table.match(/<tr/g)).toHaveLength(26);
 expect(html).toContain('<option value="25" selected="">25</option>');
 for(const size of ['50','100','all'])expect(html).toContain(`<option value="${size}">${size==='all'?'All':size}</option>`);
 expect(html).toContain('1–25 of 127 positions');
 expect(html).toContain('Page 1 of 6');
 expect(html).toContain('18,809.84');
 const pagination=html.match(/<nav[^>]*aria-label="Position pagination"[\s\S]*?<\/nav>/)![0];
 expect(pagination).toContain('Positions per page');
 expect(html.indexOf('Positions per page')).toBeGreaterThan(html.indexOf(table)+table.length);
});

it('separates breakdown from mounted position details while retaining shared totals',()=>{
 const html=renderToStaticMarkup(<ResultWorkspace batch={batch} currency="GBP"/>);
 expect(html).toContain('aria-label="Selected valuation report"');
 expect(html).toMatch(/id="pnl-report-positions-panel"[^>]*hidden=""/);
 expect(html).not.toMatch(/id="pnl-report-breakdown-panel"[^>]*hidden=""/);
 expect(html.indexOf('Daily review summary')).toBeLessThan(html.indexOf('pnl-report-breakdown-panel'));
});

it('offers an Ops report with labels, component columns and visible review warnings',()=>{
 const enriched={...batch,presentation:{references:{listing:'Example equity · EXM · London · GBP'},currencies:{gbp:'GBP'},datasets:{},rules:{},users:{},context:{},totals:{interest:null,other:null},pendingAmendments:2},
  items:batch.items.map(item=>({...item,display:{interest:null,other:null,attention:['Interest not supplied']}}))};
 const html=renderToStaticMarkup(<ResultWorkspace batch={enriched} currency="GBP"/>);
 expect(html).toContain('Example equity');expect(html).toContain('Other components');
 expect(html).toContain('Search positions');expect(html).toContain('Attention only');
 expect(html).toContain('Publication blockers');expect(html).toContain('2 pending amendment');
 expect(html).toContain('Total recorded P&amp;L');expect(html).not.toContain('Ready to publish');
 expect(html).toContain('Exact batch totals');
});

it('never discloses financial fields or ledger links when display evidence is denied',()=>{
 const html=renderToStaticMarkup(<ResultWorkspace batch={{...batch,summary:{...batch.summary,evidenceAccess:'DENIED',reason:'Current DISPLAY rights required'}}} currency="GBP"/>);
 expect(html).toContain('Current DISPLAY rights required');
 expect(html).not.toContain('18,809');expect(html).not.toContain('/trades/original');
 expect(html).not.toContain('Position attribution');
 expect(html).not.toContain('P&amp;L sources');
});

it('keeps an unavailable breakdown explicit without stacking historical cash warnings',()=>{
 const html=renderToStaticMarkup(<ResultWorkspace batch={batch} currency="GBP"/>);
 expect(html).toContain('P&amp;L sources &amp; coverage');
 expect(html).toContain('Coverage breakdown unavailable');
 expect(html).not.toContain('pnl-cash-gap');
});

it('separates missing amounts, recorded zero, partial interest and exact reconciliation',()=>{
 const enriched={...batch,presentation:{references:{},currencies:{},datasets:{},rules:{},users:{},context:{},
  totals:{interest:'1.25',other:null},pendingAmendments:0,sourceCoverage:{basis:'STORED_REPORTING_CURRENCY_COMPONENTS' as const,
   includedTotal:'18809.844746795077',recordedNet:'18809.844746795077',reconciliation:'MATCH' as const,rows:[
    {code:'PRICE',label:'Price movements',description:'Stored price movement.',componentCodes:['PRICE'],amount:'0',status:'INCLUDED' as const,positionCount:1,missingCount:0},
    {code:'ACCRUAL',label:'Daily interest earned',description:'Daily added interest only.',componentCodes:['ACCRUAL'],amount:'1.25',status:'PARTIAL' as const,positionCount:1,missingCount:2},
    {code:'RESET',label:'Resets',description:'Recorded reset flows.',componentCodes:['RESET'],amount:null,status:'NOT_RECORDED' as const,positionCount:0,missingCount:0},
    {code:'CASH_BALANCE_FX',label:'Cash-balance FX P&L',description:'Inputs unavailable.',componentCodes:['CASH_FX'],amount:null,status:'NOT_ASSESSED' as const,positionCount:0,missingCount:0}
   ]}}};
 const html=renderToStaticMarkup(<ResultWorkspace batch={enriched} currency="GBP"/>);
 expect(html).toContain('<caption>P&amp;L sources · GBP');
 expect(html).toContain('0.00');expect(html).toContain('Partial · missing interest');
 expect(html).toContain('2 missing instrument/date inputs');expect(html).toContain('No recorded entries');
 expect(html).toContain('Reconciles to recorded total');
 expect(html).toContain('18809.844746795077');
 expect(html).toContain('Inspect positions: Price movements');
 expect(html).toContain('does not certify that every income or cost due was supplied');
});

it('prominently discloses omitted daily interest rather than a zero accrual',()=>{
 const partial={...batch,summary:{...batch.summary,accrualCoverage:{mode:'OPTIONAL',suppliedCount:1,missingCount:2,
  missing:[{instrumentId:'bond',valueDate:'2026-10-06'},{instrumentId:'bond',valueDate:'2026-10-07'}]}}};
 const html=renderToStaticMarkup(<ResultWorkspace batch={partial} currency="GBP"/>);
 expect(html).toContain('Inputs to review');
 expect(html).toContain('2 daily-interest / FX inputs not included');
 expect(html).toContain('not confirmed zero');
 const denied=renderToStaticMarkup(<ResultWorkspace batch={{...partial,summary:{...partial.summary,evidenceAccess:'DENIED'}}} currency="GBP"/>);
 expect(denied).not.toContain('2 daily-interest / FX inputs');
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
