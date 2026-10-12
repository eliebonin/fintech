import {expect,it} from 'vitest';
import {recognitionDate,recognitionPayload,recognitionErrors} from './valuation-recognition';

it('defaults to UTC date rather than execution text date',()=>{
 expect(recognitionDate({tradeDatetime:'2026-10-06T23:30:00-04:00'})).toBe('2026-10-07');
});
it('carries a built-in override and reason outside custom properties',()=>{
 const draft={tradeDatetime:'2026-10-07T10:00:00Z',valuationEffectiveDate:'2026-10-08',valuationOverrideReason:' After boundary '};
 expect(recognitionPayload(draft)).toEqual({valuationEffectiveDate:'2026-10-08',valuationOverrideReason:'After boundary'});
 expect(recognitionErrors(draft)).toEqual([]);
 expect(recognitionErrors({...draft,valuationOverrideReason:''})[0]?.field).toBe('valuationOverrideReason');
 expect(recognitionErrors({...draft,valuationEffectiveDate:'2026-10-06'})[0]?.field).toBe('valuationEffectiveDate');
});
