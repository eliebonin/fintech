import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {MarketDataSourcesConsole} from './market-data-sources-console';
const catalogue={canManage:false,canManagePlatform:false,sources:[],instrumentTypes:[{id:'equity',label:'EQUITY'}],priorities:[]};
it('offers source discovery without advertising writes to readers',()=>{
 const html=renderToStaticMarkup(<MarketDataSourcesConsole initial={catalogue}/>);
 expect(html).toContain('Providers &amp; scope');
 expect(html).toContain('Source priorities');
 expect(html).toContain('Read-only');
 expect(html).not.toContain('Save tenant priorities');
});
it('distinguishes reporting-only access from a valuation activity warning',()=>{
 const source={datasetId:'report-only',provider:'Personal source',product:'Daily',code:'REPORT_ONLY',label:'History',tenantOwned:false,
 coverageDescription:null,coverageMode:'DATASET',packages:[],purposes:['INTERNAL_REPORTING'],entitlementScopes:[],nonDisplayAllowed:false,validFrom:'2026-01-01',validTo:null};
 const html=renderToStaticMarkup(<MarketDataSourcesConsole initial={{...catalogue,sources:[source]}}/>);
 expect(html).toContain('No valuation entitlement');
 expect(html).not.toContain('Non-display not permitted');
});
