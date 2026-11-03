import {expect,it,vi} from 'vitest';
vi.mock('server-only',()=>({}));
import type {components} from 'api-contracts';
import {getSwapTermsLabels} from './reference-api-client';
it('uses canonical identities and trusted tenant to label details without unrelated search matches',async()=>{
  const requested:URL[]=[];
  const fetchImpl:typeof fetch=async(input,options)=>{
    const url=new URL(String(input));requested.push(url);const headers=new Headers(options?.headers);expect(headers.get('X-Tenant-Id')).toBe('tenant');expect(headers.get('X-User-Account-Id')).toBe('actor');
    const data=url.pathname.includes('reference-nodes')?[{referenceNodeId:url.searchParams.get('q'),canonicalName:url.searchParams.get('q')==='ref'?'Visible equity':'SONIA'},{referenceNodeId:'unrelated',canonicalName:'Unrelated result'}]:url.pathname.includes('currencies')?[{items:[{currencyId:'gbp',currencyCode:'GBP'}]}]:url.pathname.includes('return-profiles')?[{returnProfileId:'total',displayName:'Gross total'}]:[{dayCountConventionId:'act365',displayName:'Actual / 365'}];
    return Response.json({data});
  };
  const terms={performanceReferenceId:'ref',fundingReferenceId:'sonia',dayCountConventionId:'act365'} as components['schemas']['GenericSwapTerms-Output'];
  expect(await getSwapTermsLabels({tenantId:'tenant',userAccountId:'actor',fetchImpl},terms)).toEqual({ref:'Visible equity',sonia:'SONIA',gbp:'GBP',total:'Gross total',act365:'Actual / 365'});
  expect(requested.find(u=>u.searchParams.get('q')==='sonia')?.searchParams.get('node_type')).toBe('RATE_INDEX');
});
it('keeps identifiers displayable when catalogue labels are unavailable',async()=>{
  const fetchImpl:typeof fetch=async()=>Response.json({detail:'Unavailable'},{status:503});
  expect(await getSwapTermsLabels({tenantId:'tenant',userAccountId:'actor',fetchImpl},{performanceReferenceId:'ref'} as components['schemas']['GenericSwapTerms-Output'])).toEqual({});
});
it('resolves both rate legs and day counts without a fictitious performance reference',async()=>{
  const requested:URL[]=[];
  const fetchImpl:typeof fetch=async(input,options)=>{
    const url=new URL(String(input));requested.push(url);
    expect(new Headers(options?.headers).get('X-Tenant-Id')).toBe('tenant');
    const data=url.pathname.includes('reference-nodes')
      ?[{referenceNodeId:url.searchParams.get('q'),canonicalName:url.searchParams.get('q')==='sofr'?'SOFR':'SONIA'},{referenceNodeId:'unrelated',canonicalName:'Other rate'}]
      :url.pathname.includes('currencies')?[{items:[{currencyId:'usd',currencyCode:'USD'},{currencyId:'gbp',currencyCode:'GBP'}]}]
      :[{dayCountConventionId:'act360',displayName:'Actual / 360'},{dayCountConventionId:'act365',displayName:'Actual / 365'}];
    return Response.json({data});
  };
  const terms={swapKind:'RATE_EXCHANGE',legs:[{rateReferenceId:'sofr'},{rateReferenceId:'sonia'}]} as components['schemas']['RateSwapTerms-Output'];
  expect(await getSwapTermsLabels({tenantId:'tenant',userAccountId:'actor',fetchImpl},terms)).toEqual({sofr:'SOFR',sonia:'SONIA',usd:'USD',gbp:'GBP',act360:'Actual / 360',act365:'Actual / 365'});
  expect(requested.filter(u=>u.pathname.includes('reference-nodes')).map(u=>[u.searchParams.get('q'),u.searchParams.get('node_type')])).toEqual([['sofr','RATE_INDEX'],['sonia','RATE_INDEX']]);
  expect(requested.some(u=>u.pathname.includes('return-profiles'))).toBe(false);
});
