import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {StrategyMeasures,type MeasureData} from './strategy-measures';

it('shows unavailable separately from genuine zero and labels preview/evidence',()=>{
 const measure={localAmount:'0',currency:'GBP',strategyAmount:'0',strategyCurrency:'GBP',status:'AVAILABLE'};
 const data={status:'PREVIEW_NOT_PUBLISHED',asOf:'2026-10-14',informationCutoff:'2026-10-15T10:00:00Z',total:1,limit:25,offset:0,items:[{positionId:'p',instrumentId:'i',name:'Example swap',quantity:'25000',quantityUnit:'UNITS',measures:{referenceNotional:{...measure,localAmount:'206250000',strategyAmount:'206250000'},economicExposure:{...measure,localAmount:null,strategyAmount:null,status:'UNAVAILABLE'},marketValue:measure},evidence:{issues:{underlyingPrice:'Required underlying price is missing'},route:'WHOLE_SWAP_MARK'},evidenceHash:'hash'}]} as MeasureData;
 const html=renderToStaticMarkup(<StrategyMeasures strategyId="s" query={new URLSearchParams('asOf=2026-10-14&policyId=p')} policies={[{id:'p',label:'EOD v3'}]} data={data}/>);
 expect(html).toContain('Not staged or published');expect(html).toContain('206,250,000');expect(html).toContain('Unavailable');expect(html).toContain('0 GBP');expect(html).toContain('Required underlying price is missing');expect(html).toContain('Inputs and calculation');expect(html).not.toContain('weight_pct');
});

function reportFixture():MeasureData {
 const available={localAmount:'1000.1234567890123456789',currency:'USD',strategyAmount:'800.09876543120987654312',strategyCurrency:'GBP',status:'AVAILABLE'};
 const empty={localAmount:null,currency:'USD',strategyAmount:null,strategyCurrency:'GBP',status:'UNAVAILABLE',reasonCode:'NOT_SUPPORTED_YET'};
 const row={positionId:'p',instrumentId:'i',name:'Alpha equity',instrumentType:'EQUITY',instrumentTypeLabel:'Equities',quantity:'10',quantityUnit:'SHARES',measures:{referenceNotional:available,economicExposure:available,marketValue:available},evidence:{route:'SECURITY_PRICE',positionKey:{unit_multiplier:'1',quote_factor:'1'},bookingTradeIds:['booked-trade-id'],selections:{securityPrice:{selection:{selected_value:'100.01234567890123456789',currency_id:'ccy',pricing_date_used:'2026-10-14'}}}},evidenceHash:'hash'};
 return {status:'PREVIEW_NOT_PUBLISHED',asOf:'2026-10-14',informationCutoff:'2026-10-15T10:00:00Z',total:30,limit:25,offset:0,reportingCurrency:'GBP',items:[row,{...row,positionId:'future',name:'Index future',instrumentType:'FUTURE',instrumentTypeLabel:'Futures',quantityUnit:'CONTRACTS',measures:{...row.measures,marketValue:empty},evidence:{issues:{marketValue:'Settlement tracking is deferred'},route:'FUTURE_CURRENT_NOTIONAL'}}]} as MeasureData;
}

it('groups the server page, distinguishes partial support and never implies a full-book valuation total',()=>{
 const html=renderToStaticMarkup(<StrategyMeasures strategyId="s" query={new URLSearchParams('asOf=2026-10-14&policyId=p')} policies={[]} data={reportFixture()}/>);
 expect(html).toContain('Position values &amp; exposure');expect(html).toContain('Load measures');
 expect(html).toContain('scope="rowgroup"');expect(html.indexOf('Equities')).toBeLessThan(html.indexOf('Alpha equity'));expect(html.indexOf('Futures')).toBeLessThan(html.indexOf('Index future'));
 expect(html).toContain('Not supported yet');expect(html).toContain('Partial');expect(html).toContain('Settlement tracking is deferred');
 expect(html).toContain('Showing 1–2 of 30');expect(html).not.toContain('Total market value');
 expect(html).toContain('1,000.1234567890123456789 USD');expect(html).toContain('800.09876543120987654312 GBP');
 expect(html).toContain('Preview only');expect(html).not.toContain('Publish');
});

it.each([['local','1,000.1234567890123456789 USD','800.09876543120987654312 GBP'],['strategy','800.09876543120987654312 GBP','1,000.1234567890123456789 USD']])('uses %s display without recalculating or relabelling amounts',(mode,visible,hidden)=>{
 const data=reportFixture();data.items=data.items.slice(0,1);
 const html=renderToStaticMarkup(<StrategyMeasures strategyId="s" query={new URLSearchParams(`displayCurrency=${mode}`)} policies={[]} data={data}/>);
 // Currency mode governs the scan row; the closed inspector retains both exact currencies.
 const table=html.slice(html.indexOf('<table')).split(/<tr[^>]*hidden=""[^>]*>/)[0];
 expect(table).toContain(visible);expect(table).not.toContain(hidden);
});

it('keeps missing FX visible even in strategy-only display and preserves context in inspection and paging links',()=>{
 const data=reportFixture();data.items=data.items.slice(0,1);
 data.items[0].measures.marketValue={...data.items[0].measures.marketValue,strategyAmount:null,status:'LOCAL_ONLY',reasonCode:'FX_UNAVAILABLE'};
 const html=renderToStaticMarkup(<StrategyMeasures strategyId="s" query={new URLSearchParams('asOf=2026-10-14&policyId=p&displayCurrency=strategy&basis=EXECUTED')} policies={[]} data={data}/>);
 expect(html).toContain('Strategy FX unavailable');expect(html).toContain('Local amount only');
 expect(html).toContain('displayCurrency=strategy');expect(html).toContain('informationCutoff=2026-10-15T10%3A00%3A00Z');
 expect(html).toContain('position=p');expect(html).toContain('offset=25');
 expect(html).toContain('/trades/booked-trade-id');expect(html).toContain('Actual price date');expect(html).toContain('2026-10-14');
});

it('hides calculation controls when forbidden and keeps errors distinct from empty results',()=>{
 const html=renderToStaticMarkup(<StrategyMeasures strategyId="s" query={new URLSearchParams()} policies={[]} canCalculate={false} error="Strategy access is required."/>);
 expect(html).not.toContain('Load measures');expect(html).toContain('role="alert"');expect(html).toContain('Strategy access is required.');expect(html).not.toContain('No positions');
});

it('does not label a wholly unsupported product as a partially valued position',()=>{
 const data=reportFixture();data.items=data.items.slice(1);
 const unavailable={localAmount:null,currency:'USD',strategyAmount:null,strategyCurrency:'GBP',status:'UNAVAILABLE',reasonCode:'NOT_SUPPORTED_YET'};
 data.items[0].measures={referenceNotional:unavailable,economicExposure:unavailable,marketValue:unavailable};
 const html=renderToStaticMarkup(<StrategyMeasures strategyId="s" query={new URLSearchParams()} policies={[]} data={data}/>);
 expect(html).toMatch(/class="measure-status [^"]*">Not supported yet<\/span>/);
});

it('shows applied currencies, factors and frozen swap conventions as readable inputs',()=>{
 const data=reportFixture();data.items=data.items.slice(0,1);
 data.items[0].evidence={route:'WHOLE_SWAP_MARK',positionKey:{unit_multiplier:'1',quote_factor:'100'},
  selections:{swapMark:{currencyCode:'USD',selection:{selected_value:'2.5',pricing_date_used:'2026-10-14'},series:{source_system_id:'SYNTHETIC'}},
   swapTerms:{terms:{leverage:'1.5',performanceDirection:'RECEIVE',notionalPerUnit:'8250'}},
   marketValueFx:{rate:'0.8',sourceCurrencyCode:'USD',targetCurrencyCode:'GBP',observationDate:'2026-10-14',method:'DIRECT'}}};
 const html=renderToStaticMarkup(<StrategyMeasures strategyId="s" query={new URLSearchParams()} policies={[]} data={data}/>);
 expect(html).toContain('Applied currency');expect(html).toContain('USD → GBP');expect(html).toContain('Leverage');expect(html).toContain('1.5');expect(html).toContain('RECEIVE');expect(html).toContain('8250');
 expect(html).toContain('Source');expect(html).toContain('SYNTHETIC');
});

it('requires a policy and preserves its version label without choosing one automatically',()=>{
 const html=renderToStaticMarkup(<StrategyMeasures strategyId="s" query={new URLSearchParams('asOf=2026-10-14')} policies={[{id:'p',label:'EOD · v3'}]}/>);
 expect(html).toContain('Select pricing policy');expect(html).toContain('EOD · v3');expect(html).toContain('Load measures');expect(html).not.toContain('0 GBP');
});

it('renders contractual FX legs without hiding them behind a null scalar or netting them',()=>{
 const unavailable={localAmount:null,currency:null,strategyAmount:null,strategyCurrency:'GBP',status:'UNAVAILABLE'};
 const data={status:'PREVIEW_NOT_PUBLISHED',asOf:'2026-10-14',informationCutoff:'2026-10-15T10:00:00Z',total:1,limit:25,offset:0,items:[{positionId:'p',instrumentId:'i',name:'EUR/USD forward',quantity:'1000000',quantityUnit:'CURRENCY_AMOUNT',measures:{referenceNotional:{localAmount:'1000000',currency:'EUR',strategyAmount:'850000',strategyCurrency:'GBP',status:'AVAILABLE'},economicExposure:{...unavailable,status:'MULTI_CURRENCY',representation:'CONTRACTUAL_CURRENCY_LEGS',legs:[{role:'BASE',localAmount:'1000000',currency:'EUR',strategyAmount:'850000',strategyCurrency:'GBP',status:'AVAILABLE'},{role:'QUOTE',localAmount:'-1100000',currency:'USD',strategyAmount:null,strategyCurrency:'GBP',status:'LOCAL_ONLY'}]},marketValue:unavailable},evidence:{issues:{marketValue:'Discounted contract MTM is unavailable'},route:'FX_FORWARD_CONTRACTUAL_LEGS'},evidenceHash:'hash'}]} as MeasureData;
 const html=renderToStaticMarkup(<StrategyMeasures strategyId="s" query={new URLSearchParams()} policies={[]} data={data}/>);
 expect(html).toContain('Contractual currency legs');expect(html).toContain('Receive');expect(html).toContain('Pay');
 expect(html).toContain('1,000,000 EUR');expect(html).toContain('-1,100,000 USD');expect(html).toContain('850,000 GBP');
 expect(html).toContain('Strategy FX unavailable');expect(html).toContain('Undiscounted');expect(html).toContain('not delta');
 expect(html).toContain('Discounted contract MTM is unavailable');
});

it('keeps scan amounts compact and exact amounts in an accessible full-width inspector',()=>{
 const data=reportFixture();data.items=data.items.slice(0,1);
 const html=renderToStaticMarkup(<StrategyMeasures strategyId="s" query={new URLSearchParams()} policies={[]} data={data}/>);
 expect(html).toMatch(/>1,000\.12 USD<\/strong>/);
 expect(html).toContain('Exact monetary amounts');
 expect(html).toContain('1,000.1234567890123456789 USD');
 expect(html).toContain('Amounts shown to 2 decimals');
 expect(html).toMatch(/<button[^>]*aria-expanded="false"[^>]*aria-controls=/);
 expect(html).toMatch(/<tr[^>]*hidden=""[^>]*><td colSpan="7"/);
});
