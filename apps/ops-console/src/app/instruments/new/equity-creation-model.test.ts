import {describe,it,expect} from 'vitest';

import {equityCreationPayload,equityIssuerLabel} from './equity-creation-model';



describe('governed equity creation choices',()=>{

  const draft={canonicalName:'Real security',baseCurrencyId:'currency',effectiveFrom:'2026-11-03'};

  it('leaves an unresolved issuer explicit and never sends a seeded source on manual requests',()=>{

    const result=equityCreationPayload(draft,'MANUAL');

    expect(result.issuerOrganisationId).toBeUndefined();

    expect(result).not.toHaveProperty('sourceSystemId');

    expect(result.submissionMode).toBe('MANUAL');

  });

  it('binds the selected source, namespace and policy instead of defaults',()=>{

    const option={sourceSystemId:'provider',sourceName:'Provider',sourceNamespace:'REAL_INSTRUMENTS',policyCode:'CREATE_EQ',policyName:'Reviewed',policyVersion:4};

    const result=equityCreationPayload({...draft,issuerOrganisationId:'issuer'},'AUTOMATED',option,{sourceExternalId:'ABC',confidenceScore:'0.98'});

    expect(result).toMatchObject({issuerOrganisationId:'issuer',sourceSystemId:'provider',sourceNamespace:'REAL_INSTRUMENTS',automationPolicyCode:'CREATE_EQ',sourceObjectType:'INSTRUMENT',sourceExternalId:'ABC'});

  });

  it('rejects automated submission without a configured choice or source identifier',()=>{

    expect(()=>equityCreationPayload(draft,'AUTOMATED')).toThrow(/configured/i);

    const option={sourceSystemId:'provider',sourceName:'Provider',sourceNamespace:'REAL',policyCode:'CREATE',policyName:'Reviewed',policyVersion:1};

    expect(()=>equityCreationPayload(draft,'AUTOMATED',option)).toThrow(/identifier/i);

  });

});



it('omits absent or duplicate issuer legal names',()=>{

  expect(equityIssuerLabel({displayName:'Northern Trust',legalName:null})).toBe('Northern Trust');

  expect(equityIssuerLabel({displayName:'Northern Trust',legalName:'Northern Trust'})).toBe('Northern Trust');

  expect(equityIssuerLabel({displayName:'NT',legalName:'Northern Trust'})).toBe('NT · Northern Trust');

});
