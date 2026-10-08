import type {components} from 'api-contracts';
export type PricingRule=components['schemas']['PolicyRuleInput'];
export type PricingPolicy=components['schemas']['PolicyView'];
export type PricingPolicyCreate=components['schemas']['PolicyCreate'];
export type PricingOptions=components['schemas']['PolicyOptions'];
export type PricingPreview=components['schemas']['ResolutionPreview'];

export function newPricingRule(sequence:number):PricingRule {
 return {ruleSequence:sequence,seriesType:'CLOSE',pricingConvention:'SESSION_CLOSE',pricingDateRule:'SAME_DAY',maxStalenessBusinessDays:0,missingDataAction:'FAIL',lagBusinessDays:0,selectionMethod:'OFFICIAL'};
}
export function previewSubjects(text:string):string[] {
 const values=[...new Set(text.trim().split(/[\s,]+/).filter(Boolean))];
 if(!values.length||values.length>50||values.some(id=>!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)))throw new Error('Enter 1–50 explicit listing/reference UUIDs.');
 return values;
}
export function stalenessLimit(text:string):number|null {
 if(!text.trim())return null;
 const value=Number(text);
 if(!Number.isInteger(value)||value<0||value>366)throw new Error('Staleness must be a whole number from 0 to 366, or explicitly uncapped.');
 return value;
}
export function pricingEvidenceLabel(evidence:Record<string,unknown>|null|undefined):string {
 if(!evidence)return 'Legacy policy: no composite target evidence recorded.';
 const calendar=evidence.calendarEvidence as Record<string,unknown>|undefined;
 return `${evidence.convention??'Unknown convention'} · ${evidence.pricingTargetUtc??'Target not assessed'} · ${calendar?.source??'Calendar not assessed'}${calendar?.authoritative===false?' (non-authoritative comparison)':''}`;
}
