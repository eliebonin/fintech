import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {it,expect} from 'vitest';
import {PricingPolicyConsole} from './pricing-policy-console';
const options={canManage:false,cuts:[],venues:[],instrumentTypes:[],calendars:[],strategies:[],datasets:[]};
it('lets readers inspect and preview while explaining missing configuration authority',()=>{
 const html=renderToStaticMarkup(<PricingPolicyConsole options={options} initialPolicies={[]}/>);
 expect(html).toContain('Read-only configuration');expect(html).toContain('tenant administrator');
 expect(html).toContain('Information cutoff');expect(html).not.toContain('Save new immutable version');
});
it('exposes rule-specific targets and separates information time from pricing time',()=>{
 const html=renderToStaticMarkup(<PricingPolicyConsole options={{...options,canManage:true}} initialPolicies={[]}/>);
 expect(html).toContain('Exchange session close');expect(html).toContain('Named fixing');
 expect(html).toContain('Read-only preview');expect(html).toContain('Save new immutable version');
});
