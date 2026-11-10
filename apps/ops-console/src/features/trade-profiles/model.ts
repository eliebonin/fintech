import type {Rule} from './client';
export const standardLabels={COUNTERPARTY:'Counterparty',EXECUTING_BROKER:'Executing broker',TRADER:'Trader',COMMENT:'Comment'} as const;
export function fieldKey(rule:Rule){return rule.standardFieldKey?`STANDARD:${rule.standardFieldKey}`:`CUSTOM:${rule.propertyCode}`;}
export function defaultRules():Rule[]{return Object.keys(standardLabels).map(key=>({standardFieldKey:key as keyof typeof standardLabels,propertyCode:null,propertyVersion:null,requirement:'OPTIONAL',lifecycleBehavior:'INPUT'}));}
export function updateRule(rules:Rule[],rule:Rule){
 const next=rule.requirement==='NOT_USED'?{...rule,lifecycleBehavior:'INPUT' as const}:rule;
 return rules.some(r=>fieldKey(r)===fieldKey(next))?rules.map(r=>fieldKey(r)===fieldKey(next)?next:r):[...rules,next];
}
export function ruleLabel(value:string){return ({ALLOCATION:'Keep exposure separate by this field',INHERIT:'Copy when source values agree',INPUT:'Operator supplies when needed'} as Record<string,string>)[value]??value;}

export function ruleDescription(value:string){return ({
 INPUT:'Do not copy this field from source trades. Ops supplies a value when required; optional fields may be left blank.',
 INHERIT:'Copy the value when contributing source trades agree within a prepared entry. Conflicting values need Ops input; this does not split exposure.',
 ALLOCATION:'Group exposure by this field and prepare separately classified closing entries. For example, Protection and Income are closed separately.',
} as Record<string,string>)[value]??'';}
