import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {ValuationFailureSummary} from './valuation-failure-summary';

it.each([
 ['NO_VALID_ENTITLEMENT','Valuation permission is missing','/market-data/sources'],
 ['NO_MATCHING_POLICY_RULE','The pricing policy does not cover this instrument','/market-data/policies'],
 ['NO_ELIGIBLE_OBSERVATION','No price meets the policy requirements','/market-data/policies'],
])('explains %s without losing the original diagnosis',(code,title,href)=>{
 const reason=`Input selection blocked: ${code}. TTE (01a11297-b3c8-72f3-b80e-9ce8bfd3d775) on 2026-10-06: requires closing price / split-adjusted; available closing price / split-adjusted; visible data has no valuation-use coverage.`;
 const html=renderToStaticMarkup(<ValuationFailureSummary events={[{event_code:'FAILED',details:{reason}}]}/>);
 expect(html).toContain(title);expect(html).toContain(`href="${href}"`);
 expect(html).toContain('<dd>TTE</dd>');expect(html).toContain('<dd>2026-10-06</dd>');
 expect(html).toContain('Policy requires');expect(html).toContain('Available price types');
 expect(html).toContain(reason);
});

it('preserves unknown reasons without guessing a permissions diagnosis and escapes markup',()=>{
 const html=renderToStaticMarkup(<ValuationFailureSummary events={[{event_code:'FAILED',details:{reason:'Unsupported economics <script>bad()</script>'}}]}/>);
 expect(html).toContain('Valuation could not be calculated');expect(html).toContain('Unsupported economics &lt;script&gt;');
 expect(html).not.toContain('<script>');expect(html).not.toContain('Valuation permission is missing');
});

it('handles older events with no reason and does not render for successful logs',()=>{
 const html=renderToStaticMarkup(<ValuationFailureSummary events={[{event_code:'FAILED',details:null}]}/>);
 expect(html).toContain('No explanatory reason was recorded');
 expect(renderToStaticMarkup(<ValuationFailureSummary events={[{event_code:'STARTED',details:{}}]}/>)).toBe('');
});

it('uses the latest recorded failure rather than an earlier cause',()=>{
 const html=renderToStaticMarkup(<ValuationFailureSummary events={[
  {event_code:'FAILED',details:{reason:'Input selection blocked: NO_MATCHING_POLICY_RULE'}},
  {event_code:'FAILED',details:{reason:'Input selection blocked: NO_VALID_ENTITLEMENT'}},
 ]}/>);
 expect(html).toContain('Valuation permission is missing');expect(html).not.toContain('The pricing policy does not cover');
});
