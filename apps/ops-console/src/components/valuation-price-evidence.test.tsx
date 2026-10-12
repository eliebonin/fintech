import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {ValuationPriceEvidence} from './valuation-price-evidence';

it('distinguishes original provider price from normalized valuation price',()=>{
 const html=renderToStaticMarkup(<ValuationPriceEvidence evidence={{selections:[{valuation_date:'2026-10-07',selected_value:'40',pricing_evidence:{priceBasis:{sourceBasis:'SPLIT_ADJUSTED',valuationValue:'80',valuationBasis:'AS_TRADED',factor:'0.5',anchorDate:'2026-10-08'}}}]}}/>);
 expect(html).toContain('Source price');expect(html).toContain('Valuation price');
 expect(html).toContain('80');expect(html).toContain('SPLIT_ADJUSTED');expect(html).toContain('0.5');expect(html).toContain('2026-10-08');
});

it('shows requested and actual market dates and selected-rule provenance',()=>{
 const html=renderToStaticMarkup(<ValuationPriceEvidence evidence={{identity:{openingCutoff:'2026-10-06T23:59:59Z',closingCutoff:'2026-10-07T23:59:59Z',facts:[]},selections:[{valuation_date:'2026-10-07',selected_value:'123.4500',pricing_date_requested:'2026-10-07',pricing_date_used:'2026-10-06',dataset_id:'dataset-one',policy_rule_id:'rule-one',staleness_status:'WITHIN_TOLERANCE',staleness_business_days:1,pricing_evidence:{convention:'SESSION_CLOSE',policyMode:'FLEXIBLE',ruleOrigin:'DEFAULT'}}]}}/>);
 expect(html).toContain('Closing market mark');expect(html).toContain('123.4500');expect(html).toContain('2026-10-06');
 expect(html).toContain('dataset-one');expect(html).toContain('FLEXIBLE · DEFAULT');expect(html).toContain('WITHIN_TOLERANCE');
});
it('shows period executions as booked-price bridges, never manufactured opening market marks',()=>{
 const html=renderToStaticMarkup(<ValuationPriceEvidence evidence={{identity:{openingCutoff:'2026-10-06T23:59:59Z',closingCutoff:'2026-10-07T23:59:59Z'},executionInputs:[{event_id:'event-one',effective_at:'2026-10-07T00:00:00Z',booking:{trade_id:'trade-one',price:'120.00',quantity:'10',quote_factor:'1',unit_multiplier:'1'}}],selections:[]}}/>);
 expect(html).toContain('Booked execution price');expect(html).toContain('120.00');expect(html).toContain('trade-one');
 expect(html).not.toContain('Opening market mark');
});
