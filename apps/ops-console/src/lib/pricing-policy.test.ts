import {expect,it} from 'vitest';
import {newPricingRule,previewSubjects,pricingEvidenceLabel,stalenessLimit} from './pricing-policy';

it('creates an explicit session-close rule with no implicit dataset or fixing',()=>{
 const rule=newPricingRule(2);
 expect(rule).toMatchObject({ruleSequence:2,pricingConvention:'SESSION_CLOSE',seriesType:'CLOSE',pricingDateRule:'SAME_DAY',maxStalenessBusinessDays:0});
 expect(rule.fixingCode).toBeUndefined();expect(rule.datasetId).toBeUndefined();
});
it('requires a bounded explicit unique subject universe for preview',()=>{
 const id='00000000-0000-7000-8000-000000000001';
 expect(previewSubjects(id+'\n'+id)).toEqual([id]);
 expect(()=>previewSubjects('')).toThrow();expect(()=>previewSubjects('not-an-id')).toThrow();
});
it('distinguishes legacy evidence from versioned non-authoritative calendars',()=>{
 expect(pricingEvidenceLabel(null)).toContain('Legacy');
 expect(pricingEvidenceLabel({convention:'SESSION_CLOSE',pricingTargetUtc:'2026-08-28T20:00:00Z',calendarEvidence:{authoritative:false,source:'VERSIONED_EXCHANGE_SCHEDULE'}})).toContain('non-authoritative');
});
it('preserves an explicitly uncapped legacy tolerance instead of displaying it as zero',()=>{
 expect(stalenessLimit('')).toBeNull();expect(stalenessLimit('0')).toBe(0);expect(stalenessLimit('3')).toBe(3);
 expect(()=>stalenessLimit('3.5')).toThrow();
});
