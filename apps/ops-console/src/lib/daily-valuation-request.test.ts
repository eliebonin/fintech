import {expect,it} from 'vitest';
import {dailyValuationRequest,valuationError} from './daily-valuation-request';

it('sends dates and freezes information cutoff without inventing price times',()=>{
 const form=new FormData();form.set('openingDate','2026-10-06');form.set('closingDate','2026-10-07');
 expect(dailyValuationRequest(form,{strategyId:'strategy',policyId:'policy',cutId:'cut',reportingCurrencyId:'gbp'},'2026-10-08T10:00:00Z')).toEqual({strategyId:'strategy',policyId:'policy',cutId:'cut',reportingCurrencyId:'gbp',openingDate:'2026-10-06',closingDate:'2026-10-07',informationCutoff:'2026-10-08T10:00:00Z'});
});

it('unlocks only rejected validation while retaining uncertain/calculation retries',()=>{
 const invalid=valuationError({status:422},{code:'request.validation_failed',errors:[{location:['body','openingDate'],message:'Invalid date'}]});
 expect(invalid.message).toContain('openingDate: Invalid date');expect(invalid.validationRejected).toBe(true);
 expect(valuationError({status:422},{code:'valuation.blocked',detail:'Price missing'}).validationRejected).toBe(false);
 expect(valuationError({status:504},{detail:'Timeout'}).validationRejected).toBe(false);
});
