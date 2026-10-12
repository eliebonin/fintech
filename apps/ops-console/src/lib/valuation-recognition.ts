/** Built-in trade fields, independent of tenant-defined property catalogues. */
export type RecognitionDraft={tradeDatetime:string;valuationEffectiveDate?:string;valuationOverrideReason?:string};
function utcDate(value:string){const parsed=new Date(value);return Number.isNaN(parsed.getTime())?'':parsed.toISOString().slice(0,10);}
export function recognitionDate(draft:RecognitionDraft){return draft.valuationEffectiveDate||utcDate(draft.tradeDatetime);}
export function recognitionPayload(draft:RecognitionDraft){
 return {...(draft.valuationEffectiveDate?{valuationEffectiveDate:draft.valuationEffectiveDate}:{}),
  ...(draft.valuationOverrideReason?.trim()?{valuationOverrideReason:draft.valuationOverrideReason.trim()}: {})};
}
export function recognitionErrors(draft:RecognitionDraft):{field:string;message:string}[]{
 const day=draft.valuationEffectiveDate;if(!day)return [];
 const parsed=new Date(`${day}T00:00:00Z`),defaultDay=utcDate(draft.tradeDatetime);
 if(!/^\d{4}-\d{2}-\d{2}$/.test(day)||Number.isNaN(parsed.getTime())||parsed.toISOString().slice(0,10)!==day||day<defaultDay)
  return [{field:'valuationEffectiveDate',message:'Choose a valid valuation date on or after the UTC execution date.'}];
 if(day!==defaultDay&&!draft.valuationOverrideReason?.trim())return [{field:'valuationOverrideReason',message:'Explain the later valuation recognition date.'}];
 return [];
}
