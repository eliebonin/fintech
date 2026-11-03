import {expect,it} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {MissingPricePositions} from './missing-price-positions';
import type {Batch} from './types';
it('keeps unknown cash FX visible without inventing a security or zero amount',()=>{
 const batch={summary:{inputCoverage:{missingCount:1,affectedPositionCount:0,unpricedPositions:[],unpricedCashAccounts:[{accountId:'account',currencyId:'eur',pnl:null,inputKeys:['gap']}],gaps:[{inputKey:'gap',role:'CASH_FX',selection:{pricing_date_requested:'2026-10-19'},request:{valuation_date:'2026-10-19'}}]}},presentation:{references:{},cashAccounts:{account:'Synthetic custodian'},currencies:{eur:'EUR'}}} as unknown as Batch;
 const html=renderToStaticMarkup(<MissingPricePositions batch={batch}/>);
 expect(html).toContain('Cash accounts with missing required FX');expect(html).toContain('Synthetic custodian');
 expect(html).toContain('FX P&amp;L unavailable');expect(html).not.toContain('0.00');
});

it('keeps unpriced holdings visible with dates and exact quantities, without a zero P&L',()=>{
 const batch={summary:{inputCoverage:{missingCount:1,affectedPositionCount:1,unpricedPositions:[{positionKey:'position',subjectId:'forward',currencyId:'gbp',product:'FX_FORWARD',pnl:null,bucket:{opening_quantity:'1000000',closing_quantity:'1000000'},inputKeys:['gap']}],gaps:[{inputKey:'gap',role:'PRICE',selection:{pricing_date_requested:'2026-10-19'},request:{valuation_date:'2026-10-19'}}]}},presentation:{references:{forward:'EUR/GBP forward'},instrumentTypes:{forward:{code:'FX_FORWARD',label:'FX Forward'}},currencies:{gbp:'GBP'}}} as unknown as Batch;
 const html=renderToStaticMarkup(<MissingPricePositions batch={batch}/>);
 expect(html).toContain('EUR/GBP forward');expect(html).toContain('1,000,000');expect(html).toContain('2026-10-19');
 expect(html).toContain('P&amp;L unavailable');expect(html).not.toContain('0.00');
});
