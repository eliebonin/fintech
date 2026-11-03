import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {ResultWorkspace} from './result-workspace';
import type {Batch,Item} from './types';

const item:Item={attribution_id:'line',subject_id:'listing',trade_id:null,version:1,market_pnl:'422',gross_pnl:'434.5',net_pnl:'434.5',components:{PRICE:'337.5',FX:'80',PRICE_FX_CROSS:'4.5',ACCRUAL:'12.5'},
 evidence:{identity:{openingCutoff:'2026-10-19T23:59:59Z',closingCutoff:'2026-10-20T23:59:59Z',reportingCurrency:'gbp',
  openingValue:'6000',closingValue:'7980',executionValue:'1558',bucket:{opening_quantity:'100',closing_quantity:'125',key:{subject_id:'listing',currency_id:'usd',quantity_unit:'SHARES',product_basis:'EQUITY',unit_multiplier:'1',quote_factor:'1'}}},
  selections:[{valuation_date:'2026-10-19',selected_value:'80',pricing_date_used:'2026-10-19'},
   {valuation_date:'2026-10-20',selected_value:'84',pricing_date_used:'2026-10-20'},
   {input_role:'FX',valuation_date:'2026-10-19',valuation_source_currency_id:'usd',selected_value:'1.333333333333',pricing_date_used:'2026-10-19',conversion:{rate:'0.75',method:'RECIPROCAL',sourceCurrencyId:'usd',targetCurrencyId:'gbp'}},
   {input_role:'FX',valuation_date:'2026-10-20',valuation_source_currency_id:'usd',selected_value:'0.76',pricing_date_used:'2026-10-20',conversion:{rate:'0.76',method:'DIRECT',sourceCurrencyId:'usd',targetCurrencyId:'gbp'}}],
  executionInputs:[{event_id:'buy',effective_at:'2026-10-20T12:00:00Z',booking:{trade_id:'buy',quantity:'25',price:'82',unit_multiplier:'1',quote_factor:'1'}}]}};
const batch:Batch={batch_id:'batch',status:'STAGED',staged_by:'maker',reviews:[],items:[item],
 summary:{scope:'ECONOMIC_RECORDED_INPUTS',marketPnl:'422',openingValue:'6000',closingValue:'7980',executionValue:'1558',reportingCurrencyId:'gbp',externalComparison:'NOT_COMPARED',limitations:[]},
 presentation:{references:{listing:'Example equity'},currencies:{usd:'USD',gbp:'GBP'},datasets:{},rules:{},users:{},context:{},totals:{interest:'12.5',other:null},pendingAmendments:0}};
function report(evidence:unknown=item.evidence,overrides:Partial<Item>={}){
 return renderToStaticMarkup(<ResultWorkspace batch={{...batch,items:[{...item,...overrides,evidence}]}} currency="GBP" activeTab="positions" onNavigate={()=>{}}/>);
}
function manual(evidence:unknown=item.evidence,overrides:Partial<Item>={}){
 return report(evidence,overrides).match(/<section[^>]*aria-label="Manual P&amp;L check"[\s\S]*?<\/section>/)?.[0]??'';
}
const original=item.evidence as any;

it('leads inspection with exact boundary inputs, a signed execution bridge and an unrounded recorded result',()=>{
 const html=report(),summary=manual();
 expect(summary).toContain('Reproduce this P&amp;L');
 expect(summary).toContain('Opening · 2026-10-19');expect(summary).toContain('Closing · 2026-10-20');
 for(const number of ['100','125','80','84','0.75','0.76','6,000','7,980','1,558','422'])expect(summary).toContain(`>${number}<`);
 expect(summary).toContain('GBP per 1 USD');expect(summary).toContain('Price/FX P&amp;L = closing value − opening value − signed execution value');
 expect(summary).toContain('Signed quantity');expect(summary).toContain('>25<');expect(summary).toContain('>82<');
 expect(summary).not.toContain('1.333333333333');
 expect(html.indexOf('Reproduce this P&amp;L')).toBeLessThan(html.indexOf('<caption>P&amp;L components'));
 expect(html).toContain('<summary>Sources, applied rules and technical proof</summary>');
});

it('uses normalized valuation prices and actual price dates rather than provider-adjusted inputs',()=>{
 const summary=manual({...original,selections:original.selections.map((s:any)=>s.valuation_date==='2026-10-19'&&!s.input_role?
  {...s,selected_value:'40',valuation_value:'80',pricing_date_used:'2026-10-18',pricing_evidence:{priceBasis:{valuationValue:'80'}}}:s)});
 expect(summary).toContain('>80<');expect(summary).toContain('>2026-10-18<');expect(summary).not.toContain('>40<');
});

it('shows zero-boundary marks as unnecessary and new holdings using their actual execution and closing FX',()=>{
 const summary=manual({...original,identity:{...original.identity,bucket:{...original.identity.bucket,opening_quantity:'0'}},
  selections:original.selections.filter((s:any)=>s.valuation_date==='2026-10-20')});
 expect(summary).toContain('Not needed · zero position');expect(summary).toContain('Closing FX used · no opening exposure');
 expect(summary).toContain('>0.76<');expect(summary).toContain('>82<');
});

it('shows identity FX only when frozen currencies match and retains percentage/option factors exactly',()=>{
 for(const [product,unit,multiplier,divisor] of [['BOND','NOMINAL','1','100'],['OPTION','CONTRACTS','100','1']]){
  const summary=manual({...original,identity:{...original.identity,bucket:{...original.identity.bucket,key:{...original.identity.bucket.key,currency_id:'gbp',product_basis:product,quantity_unit:unit,unit_multiplier:multiplier,quote_factor:divisor}}},selections:original.selections.filter((s:any)=>!s.input_role)});
  expect(summary).toContain('Same currency · FX = 1');expect(summary).toContain(`>${multiplier}<`);expect(summary).toContain(`>${divisor}<`);
  expect(summary).toContain('Unit multiplier');expect(summary).toContain('Quote divisor');
 }
});

it('shows the frozen note quote basis and denomination once without inventing extra leverage',()=>{
 const summary=manual({...original,identity:{...original.identity,facts:[{booking:{product_evidence:{notePriceType:'CLEAN'}}}],
  bucket:{...original.identity.bucket,key:{...original.identity.bucket.key,product_basis:'STRUCTURED_PRODUCT',quantity_unit:'UNITS',unit_multiplier:'1000',quote_factor:'100'}}}});
 expect(summary).toContain('Note quotation: CLEAN');expect(summary).toContain('>1000<');
 expect(summary).toContain('Underlying returns and embedded leverage are already reflected');
 expect(summary).toContain('later payment confirmation');
});

it('explains whole-wrapper quotes and spot-crypto venue/peg boundaries',()=>{
 for(const [product,phrase] of [['ETN','Underlying exposure and embedded leverage are not applied again'],['DIGITAL_ASSET','A stablecoin is not assumed equal to USD']]){
  const summary=manual({...original,identity:{...original.identity,bucket:{...original.identity.bucket,key:{...original.identity.bucket.key,product_basis:product,quantity_unit:'UNITS'}}}});
  expect(summary).toContain(phrase);
 }
});

it('distinguishes a forward outright rate from its agreed rate and ignores maturity spot suggestions',()=>{
 const summary=manual({...original,identity:{...original.identity,bucket:{...original.identity.bucket,key:{...original.identity.bucket.key,product_basis:'FX_FORWARD'}},
  facts:[{booking:{product_evidence:{agreedRate:'1.10'}}}]},selections:[...original.selections,
  {input_role:'FX_MATURITY_SUGGESTION',valuation_date:'2026-10-20',selected_value:'999.123',pricing_date_used:'2026-10-20'}]});
 expect(summary).toContain('Frozen agreed rate');expect(summary).toContain('>1.10<');
 expect(summary).toContain('(contract rate − agreed rate)');expect(summary).not.toContain('999.123');
});

it('does not turn missing or ambiguous prices/FX into one, zero or the first candidate',()=>{
 const missing=manual({...original,selections:[]});
 expect(missing).toContain('Not recorded');expect(missing).not.toContain('Same currency');
 const ambiguous=manual({...original,selections:[...original.selections,{...original.selections[1],selected_value:'85'}]});
 expect(ambiguous).toContain('Multiple recorded inputs · inspect proof');
 const unknown=manual({});expect(unknown).toContain('Boundary inputs are not recorded');
});

it('keeps intermediate daily inputs visible instead of presenting a multi-day run as one daily price move',()=>{
 const summary=manual({...original,identity:{...original.identity,closingCutoff:'2026-10-21T23:59:59Z'},selections:[...original.selections,
  {valuation_date:'2026-10-21',selected_value:'86',pricing_date_used:'2026-10-21'},
  {input_role:'FX',valuation_date:'2026-10-21',valuation_source_currency_id:'usd',conversion:{rate:'0.77'},pricing_date_used:'2026-10-21'}]});
 expect(summary).toContain('Daily inputs within the period');expect(summary).toContain('2026-10-20');expect(summary).toContain('>84<');expect(summary).toContain('>0.76<');
 expect(summary).toContain('each execution uses its own economic day');
});

it('explains a flow-only row without manufacturing market prices or investment quantities',()=>{
 const summary=manual({...original,identity:{...original.identity,bucket:{...original.identity.bucket,key:{...original.identity.bucket.key,product_basis:'ECONOMIC_FLOW'}}},
  economicInputs:[{tradeId:'reset',booking:{economicDate:'2026-10-20',amount:'1000',currencyId:'usd',component:'RESET',recognitionRole:'INCOME'},fx:{method:'DIRECT',rate:'0.76'}}]});
 expect(summary).toContain('Recorded income / cost');expect(summary).toContain('>1,000<');expect(summary).toContain('>0.76<');
 expect(summary).not.toContain('Boundary prices and quantities');expect(summary).toContain('not an investment position');
});

it('retains closing-sale and round-trip executions without inventing prices on flat boundaries',()=>{
 const closed=manual({...original,identity:{...original.identity,bucket:{...original.identity.bucket,closing_quantity:'0'},closingValue:'0',executionValue:'-6300'},
  selections:original.selections.filter((s:any)=>s.valuation_date!=='2026-10-20'||s.input_role==='FX'),
  executionInputs:[{effective_at:'2026-10-20T12:00:00Z',booking:{trade_id:'sale',quantity:'-100',price:'84'}}]});
 expect(closed).toContain('Sell / decrease');expect(closed).toContain('>-100<');expect(closed).toContain('>-6,300<');
 expect(closed).toContain('Not needed · zero position');
 const roundtrip=manual({...original,identity:{...original.identity,bucket:{...original.identity.bucket,opening_quantity:'0',closing_quantity:'0'}},
  selections:original.selections.filter((s:any)=>s.input_role==='FX')});
 expect(roundtrip.match(/Not needed · zero position/g)).toHaveLength(2);
 expect(roundtrip).toContain('Trades during the period');
});

it('shows reviewed quantity changes separately from executions without hiding exact precision',()=>{
 const summary=manual({...original,identity:{...original.identity,bucket:{...original.identity.bucket,closing_quantity:'200.000000000001'}},
  splitAdjustments:[{quantity_before:'100',quantity_after:'200',event:{effective_date:'2026-10-20',ratio:'2'}}]});
 expect(summary).toContain('>200.000000000001<');expect(summary).toContain('Reviewed share adjustments · not trades');
 expect(summary).toContain('>2<');
});

it('does not disclose the manual worksheet when DISPLAY access is denied',()=>{
 const html=renderToStaticMarkup(<ResultWorkspace batch={{...batch,summary:{...batch.summary,evidenceAccess:'DENIED'}}} currency="GBP" activeTab="positions" onNavigate={()=>{}}/>);
 expect(html).not.toContain('Manual P&amp;L check');expect(html).not.toContain('>1558<');expect(html).not.toContain('>0.76<');
});

it('groups large signed nominal quantities and amounts without rounding decimals or formatting prices and FX',()=>{
 const evidence={...original,identity:{...original.identity,bucket:{...original.identity.bucket,
  opening_quantity:'-123456789012345678.123456789012',closing_quantity:'1000000.000000000001',
  key:{...original.identity.bucket.key,quantity_unit:'NOMINAL',product_basis:'BOND'}}},
  executionInputs:[{effective_at:'2026-10-20T12:00:00Z',booking:{trade_id:'large-sale',quantity:'-25000.500000000001',price:'1234.567890123456'}}],
  splitAdjustments:[{quantity_before:'1000000',quantity_after:'2000000',event:{effective_date:'2026-10-20',ratio:'2'}}]};
 const before=JSON.stringify(evidence),summary=manual(evidence);
 for(const value of ['-123,456,789,012,345,678.123456789012','1,000,000.000000000001','-25,000.500000000001','1,000,000','2,000,000'])expect(summary).toContain(`>${value}<`);
 expect(summary).toContain('>1234.567890123456<');expect(summary).not.toContain('>1,234.567890123456<');
 expect(summary).toContain('>0.75<');expect(summary).toContain('>0.76<');
 expect(JSON.stringify(evidence)).toBe(before);
 const proof=report(evidence);
 expect(proof).toContain('>-25,000.500000000001<');
});
