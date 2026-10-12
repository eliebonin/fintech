import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {PolicyCompatibilityReport,PolicySourceProfiles,PolicyRuleSources} from './pricing-policy-compatibility';

it('explains provider prices and adjustments without requiring storage-code knowledge',()=>{
 const html=renderToStaticMarkup(<PolicySourceProfiles data={{sources:[{datasetId:'source-one',label:'Personal daily feed',provider:'Yahoo',purposes:['INTERNAL_REPORTING'],nonDisplayAllowed:true,priceProfiles:[{seriesType:'CLOSE',closingMethod:'UNKNOWN',valueBasis:'SPLIT_ADJUSTED',seriesCount:2,valuationSeriesCount:0}]}]}}/>);
 expect(html).toContain('Closing price');expect(html).toContain('Split-adjusted');
 expect(html).toContain('Internal reporting');expect(html).toContain('Automated calculation permission: Recorded');
 expect(html).toContain('0 with valuation-use coverage');
});
it('distinguishes matching source definitions from incompatible ones without certifying scope',()=>{
 const data={sources:[{datasetId:'a',label:'Unadjusted feed',provider:'A',purposes:['VALUATION'],nonDisplayAllowed:true,priceProfiles:[{seriesType:'CLOSE',closingMethod:'EXCHANGE_OFFICIAL',valueBasis:'RAW',seriesCount:1,valuationSeriesCount:1}]},{datasetId:'b',label:'Adjusted feed',provider:'B',purposes:['INTERNAL_REPORTING'],nonDisplayAllowed:false,priceProfiles:[{seriesType:'CLOSE',closingMethod:'UNKNOWN',valueBasis:'SPLIT_ADJUSTED',seriesCount:1,valuationSeriesCount:0}]}]};
 const html=renderToStaticMarkup(<PolicyRuleSources data={data} seriesType="CLOSE" valueBasis="RAW"/>);
 expect(html).toContain('Sources recording this price definition: Unadjusted feed');
 expect(html).toContain('Sources with no matching recorded definition: Adjusted feed');
 expect(html).toContain('Source-wide definitions only');
});
it('does not describe unknown closing provenance as an official-only match',()=>{
 const data={sources:[{datasetId:'a',label:'Unknown close feed',provider:'A',purposes:['VALUATION'],nonDisplayAllowed:true,priceProfiles:[{seriesType:'CLOSE',closingMethod:'UNKNOWN',valueBasis:'RAW',seriesCount:1,valuationSeriesCount:1}]}]};
 const html=renderToStaticMarkup(<PolicyRuleSources data={data} seriesType="CLOSE" valueBasis="RAW" requireOfficialClose/>);
 expect(html).toContain('Sources recording this price definition: None');
 expect(html).toContain('Sources with no matching recorded definition: Unknown close feed');
});
it('shows actionable incompatibility notices without claiming valuation readiness',()=>{
 const html=renderToStaticMarkup(<PolicyCompatibilityReport report={{status:'ACTION_REQUIRED',scope:'Configuration metadata only',rules:[{ruleSequence:1,origin:'DEFAULT',matchingSeriesCount:0,eligibleSeriesCount:0,sourceLabels:['Yahoo daily'],issues:[{code:'PRICE_NOT_AVAILABLE',message:'Needs unadjusted; stored data is split-adjusted.',action:'Choose a compatible source.'}]}]}}/>);
 expect(html).toContain('Needs unadjusted');expect(html).toContain('Choose a compatible source');expect(html).toContain('role="status"');
 expect(html).not.toContain('Ready to value');
});
