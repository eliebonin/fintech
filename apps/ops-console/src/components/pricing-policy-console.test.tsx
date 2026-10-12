import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {it,expect} from 'vitest';
import {PricingPolicyConsole} from './pricing-policy-console';
const options={canManage:false,cuts:[],venues:[],instrumentTypes:[],calendars:[],strategies:[],datasets:[]};
it('offers economic price requirements independently of advanced source filters',()=>{
 const html=renderToStaticMarkup(<PricingPolicyConsole options={{...options,canManage:true}} initialPolicies={[]}/>);
 expect(html).toContain('As-traded valuation price');expect(html).toContain('Allow verified conversion');
 expect(html).toContain('Advanced source adjustment filter');
 const reader=renderToStaticMarkup(<PricingPolicyConsole options={options} initialPolicies={[]}/>);
 expect(reader).not.toContain('Allow verified conversion');
});
it('starts in flexible EoD mode and distinguishes policy context from actual rule pricing times',()=>{
 const html=renderToStaticMarkup(<PricingPolicyConsole options={{...options,canManage:true}} initialPolicies={[]}/>);
 expect(html).toMatch(/value="FLEXIBLE" selected=""/);
 expect(html).toContain('Latest available EoD');expect(html).toContain('Flexible default 1');
 expect(html).not.toContain('Explicit rule 1');
 expect(html).toContain('Policy valuation context');expect(html).not.toContain('Default policy cut');
 expect(html).toContain('16:30 London');expect(html).toContain('Missing expected-session prices fail');
});
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
it('lets an administrator choose strict or flexible behaviour and inspect the default safeguard',()=>{
 const html=renderToStaticMarkup(<PricingPolicyConsole options={{...options,canManage:true}} initialPolicies={[]}/>);
 expect(html).toContain('Policy behaviour');expect(html).toContain('Flexible');expect(html).toContain('Strict');
 expect(html).toContain('matching explicit rule');
});
it('separates price timing, adjustments, provider permission and compatibility checks',()=>{
 const html=renderToStaticMarkup(<PricingPolicyConsole options={{...options,canManage:true}} initialPolicies={[]}/>);
 expect(html).toContain('When is the price taken?');expect(html).toContain('Price adjustments');
 expect(html).toContain('Unadjusted');expect(html).toContain('Split-adjusted');
 expect(html).toContain('Check data compatibility');expect(html).toContain('Recorded permitted use');
});
it('offers one close family with an independent unchecked official-close requirement',()=>{
 const html=renderToStaticMarkup(<PricingPolicyConsole options={{...options,canManage:true}} initialPolicies={[]}/>);
 expect(html).toContain('Require exchange-official close');
 expect(html).not.toContain('value="OFFICIAL_CLOSE"');
 expect(html).toMatch(/<input type="checkbox"\/>Require exchange-official close/);
});
