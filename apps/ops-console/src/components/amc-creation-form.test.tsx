import {describe,it,expect} from 'vitest';
import {amcPayload} from './amc-creation-form';
describe('AMC creation payload',()=>{
  it('preserves certificate identity, explicit unit economics and unknown timing',()=>{
    const result=amcPayload({name:'Certificate A',issuer:'issuer',currency:'GBP',start:'2024-01-01',redemption:'UNKNOWN',
      distribution:'UNKNOWN',collateral:'UNKNOWN',source:'Reviewed terms',quantityUnit:'UNITS',priceBasis:'UNIT_PRICE',
      factor:'1',minimum:'0.0001',increment:'0.0001',otc:'YES',lag:''});
    expect(result.convention.kind).toBe('ACTIVELY_MANAGED_CERTIFICATE');
    expect(result.convention.quantityIncrement).toBe('0.0001');
    expect(result.publicationLagBusinessDays).toBeNull();
    expect(result.pricingFrequency).toBeNull();
    expect(result.adviserOrganisationId).toBeNull();
    expect(result.maturityDate).toBeNull();
    expect(result).not.toHaveProperty('fundId');
    expect(result).not.toHaveProperty('etpKind');
  });
});
