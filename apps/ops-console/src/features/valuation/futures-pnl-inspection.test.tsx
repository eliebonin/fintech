import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {PositionCalculation} from './position-calculation';
import {FuturesPnlInspection} from './futures-pnl-inspection';
import type {Item,Presentation} from './types';

const metadata:Presentation={references:{},currencies:{usd:'USD'},datasets:{},rules:{},users:{},context:{},totals:{interest:null,other:null},pendingAmendments:0};
const day={valueDate:'2026-10-20',openingDate:'2026-10-19',openingQuantity:'1000',closingQuantity:'1002',openingPrice:'6000',closingPrice:'6010',
 monetaryMultiplier:'50',quoteFactor:'1',localVariation:'500500',closingFx:'0.75',reportingVariation:'375375',
 executions:[{tradeId:'buy',quantity:'2',price:'6005',effectiveAt:'2026-10-20T10:00:00Z'}]};
function render(overrides:Record<string,unknown>={}){
 const item:Item={attribution_id:'future',trade_id:null,version:1,market_pnl:'375375',components:{PRICE:'375375',FX:'0',PRICE_FX_CROSS:'0'},
  evidence:{identity:{bucket:{key:{product_basis:'FUTURE',currency_id:'usd'}}},economicInputs:[{kind:'FUTURES_DAILY_VARIATION',currencyId:'usd',days:[{...day,...overrides}]}]}};
 return renderToStaticMarkup(<PositionCalculation item={item} metadata={metadata} currency="GBP"/>);
}
it('shows exact futures inputs and variation without presenting notional as an asset value',()=>{
 const html=render();
 expect(html).toContain('Futures daily P&amp;L');
 for(const value of ['1,000','1,002','6,000','6,010','6,005','50','500,500','0.75','375,375'])expect(html).toContain(`>${value}<`);
 expect(html).toContain('GBP per 1 USD');expect(html).toContain('/trades/buy');
 expect(html).toContain('Margin cash is assessed separately');
 expect(html).not.toContain('Price/FX P&amp;L = closing value');
});
it('does not turn an unnecessary zero-boundary price into zero MTM',()=>{
 const html=render({openingQuantity:'0',openingPrice:null});
 expect(html).toContain('Not required · zero contracts');
 expect(html).not.toContain('>null<');
});
it('explains retained physical crypto conventions without implying a token or cash delivery posting',()=>{
 const item:Item={attribution_id:'crypto',trade_id:null,market_pnl:'375375',components:{PRICE:'375375'},version:1,evidence:{economicInputs:[{kind:'FUTURES_DAILY_VARIATION',currencyId:'usd',days:[day],
  contractConvention:{priceBasis:'UNDERLYING_UNIT',settlementMethod:'PHYSICAL',contractSize:'5',lastTradingAtUtc:'2027-03-17T16:00:00Z',finalSettlementDate:'2027-03-19',deliveryStartDate:'2027-03-19',deliveryEndDate:'2027-03-19'}}]}};
 const html=renderToStaticMarkup(<FuturesPnlInspection item={item} metadata={metadata} currency="GBP"/>);
 for(const text of ['Underlying-unit quote','Physical delivery','2027-03-19','No cash or underlying delivery is posted'])expect(html).toContain(text);
});
