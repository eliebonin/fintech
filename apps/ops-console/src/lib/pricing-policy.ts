import type {components} from 'api-contracts';
export type PricingRule=components['schemas']['PolicyRuleInput'];
export type PricingPolicy=components['schemas']['PolicyView'];
export type PricingPolicyCreate=components['schemas']['PolicyCreate'];
export type PricingOptions=components['schemas']['PolicyOptions'];
export type PricingPreview=components['schemas']['ResolutionPreview'];
export type PricingCompatibility=components['schemas']['PolicyCompatibility'];
export type PricingDataOptions=components['schemas']['PolicyDataOptions'];

export function newPricingRule(sequence:number):PricingRule {
 return {ruleSequence:sequence,seriesType:'CLOSE',requireOfficialClose:false,priceRequirement:'AS_TRADED',allowSplitConversion:true,allowInverseFx:false,pricingConvention:'SESSION_CLOSE',pricingDateRule:'SAME_DAY',maxStalenessBusinessDays:0,missingDataAction:'FAIL',lagBusinessDays:0,selectionMethod:'OFFICIAL'};
}
export function newDefaultPricingRule(sequence:number):PricingRule {
 return {...newPricingRule(sequence),subjectType:'LISTING'};
}
/** Use the existing governed session-close resolver, never an arbitrary last tick. */
export function newPricingPolicyDraft(validFrom:string):PricingPolicyCreate {
 return {policyCode:'',displayName:'',valuationCutId:'',validFrom,selectionMode:'FLEXIBLE',rules:[],defaultRules:[newDefaultPricingRule(1)]};
}
export function withPricingPolicyMode(draft:PricingPolicyCreate,mode:'STRICT'|'FLEXIBLE'):PricingPolicyCreate {
 const rules=draft.rules??[],defaults=draft.defaultRules??[];
 const sequence=Math.max(0,...[...rules,...defaults].map(rule=>rule.ruleSequence))+1;
 // Existing overrides remain explicit. Re-selecting flexible must not reset edited defaults.
 return mode==='FLEXIBLE'?{...draft,selectionMode:mode,defaultRules:defaults.length?defaults:[newDefaultPricingRule(sequence)]}:
  {...draft,selectionMode:mode,rules:rules.length?rules:[newPricingRule(sequence)],defaultRules:[]};
}
export function patchPricingRule(rule:PricingRule,patch:Partial<PricingRule>):PricingRule {
 const next={...rule,...patch};
 if(next.seriesType!=='CLOSE'||next.pricingConvention==='LEGACY'){
  next.priceRequirement=null;next.allowSplitConversion=false;
 }
 if(next.seriesType!=='CLOSE')next.requireOfficialClose=false;
 if(next.seriesType!=='FX_SPOT'||!['EXPLICIT_TIME','NAMED_FIXING'].includes(next.pricingConvention))next.allowInverseFx=false;
 if(next.pricingConvention==='LEGACY')next.valueBasis=null;
 return next;
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
 const origin=evidence.policyMode?`${evidence.policyMode} · ${evidence.ruleOrigin??'No matching rule'} · `:'';
 return `${origin}${evidence.convention??'Unknown convention'} · ${evidence.pricingTargetUtc??'Target not assessed'} · ${calendar?.source??'Calendar not assessed'}${calendar?.authoritative===false?' (non-authoritative comparison)':''}${evidence.closingMethod?` · Closing method: ${evidence.closingMethod}`:''}${evidence.requireOfficialClose?' · Exchange-official close required':''}`;
}
