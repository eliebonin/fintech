import {expect,it} from 'vitest';
import {newPricingRule,newDefaultPricingRule,newPricingPolicyDraft,withPricingPolicyMode,previewSubjects,pricingEvidenceLabel,stalenessLimit,patchPricingRule} from './pricing-policy';

it('starts a new policy with a venue-neutral EoD default rather than a competing explicit catch-all',()=>{
 const draft=newPricingPolicyDraft('2026-10-06');
 expect(draft.selectionMode).toBe('FLEXIBLE');expect(draft.rules).toEqual([]);
 expect(draft.defaultRules).toHaveLength(1);
 expect(draft.defaultRules?.[0]).toMatchObject({subjectType:'LISTING',seriesType:'CLOSE',pricingConvention:'SESSION_CLOSE',pricingDateRule:'SAME_DAY',maxStalenessBusinessDays:0,missingDataAction:'FAIL',priceRequirement:'AS_TRADED'});
 expect(draft.defaultRules?.[0].pricingCutId).toBeUndefined();
 expect(draft.defaultRules?.[0].marketCalendarId).toBeUndefined();
 expect(draft.defaultRules?.[0].datasetId).toBeUndefined();
 expect(draft.validFrom).toBe('2026-10-06');
});
it('keeps explicit FX overrides when configuring a flexible EoD default',()=>{
 const fx=patchPricingRule(newPricingRule(7),{seriesType:'FX_SPOT',pricingConvention:'EXPLICIT_TIME',pricingCutId:'00000000-0000-7000-8000-000000000001'});
 const draft={...newPricingPolicyDraft('2026-10-06'),selectionMode:'STRICT' as const,rules:[fx],defaultRules:[]};
 const flexible=withPricingPolicyMode(draft,'FLEXIBLE');
 expect(flexible.rules).toEqual([fx]);expect(flexible.defaultRules?.[0].ruleSequence).toBe(8);
});
it('makes a default-only draft valid when switching to strict and preserves configured defaults on repeated flexible selection',()=>{
 const draft=newPricingPolicyDraft('2026-10-06');
 const strict=withPricingPolicyMode(draft,'STRICT');
 expect(strict.defaultRules).toEqual([]);expect(strict.rules).toHaveLength(1);
 const custom={...draft,defaultRules:[{...newDefaultPricingRule(4),pricingDateRule:'PRIOR_AVAILABLE' as const,maxStalenessBusinessDays:2}]};
 expect(withPricingPolicyMode(custom,'FLEXIBLE').defaultRules).toEqual(custom.defaultRules);
});

it('clears inapplicable economic controls when changing price family or timing',()=>{
 const fx=patchPricingRule(newPricingRule(1),{seriesType:'FX_SPOT'});
 expect(fx.priceRequirement).toBeNull();expect(fx.allowSplitConversion).toBe(false);expect(fx.requireOfficialClose).toBe(false);
 const legacy=patchPricingRule(newPricingRule(1),{pricingConvention:'LEGACY'});
 expect(legacy.priceRequirement).toBeNull();expect(legacy.allowSplitConversion).toBe(false);
});

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
it('creates an as-traded default with verified conversion and no implied carry-forward',()=>{
 expect(newDefaultPricingRule(3)).toMatchObject({ruleSequence:3,subjectType:'LISTING',seriesType:'CLOSE',priceRequirement:'AS_TRADED',allowSplitConversion:true,pricingDateRule:'SAME_DAY',maxStalenessBusinessDays:0,missingDataAction:'FAIL'});
 expect(newDefaultPricingRule(3).valueBasis).toBeUndefined();
});
it('makes flexible default provenance readable instead of hiding it in JSON',()=>{
 expect(pricingEvidenceLabel({policyMode:'FLEXIBLE',ruleOrigin:'DEFAULT',convention:'SESSION_CLOSE'})).toContain('FLEXIBLE · DEFAULT');
});
