import type {ClosingBalanceInput,DailyInterestInput} from './interest-types';

export const interestToday=()=>new Date().toISOString().slice(0,10);
export class InterestFieldError extends Error{constructor(readonly field:string,message:string){super(message);}}
function fieldAmount(value:string,field='amount'){try{return exactInterestAmount(value);}catch(cause){throw new InterestFieldError(field,cause instanceof Error?cause.message:'Enter an exact amount.');}}
function validDate(value:string){return /^\d{4}-\d{2}-\d{2}$/.test(value)&&Number.isFinite(Date.parse(`${value}T00:00:00Z`))&&new Date(`${value}T00:00:00Z`).toISOString().slice(0,10)===value;}
export function interestRange(from:string,to:string){
 if(!validDate(from)||!validDate(to))return 'Enter valid From and To dates.';
 if(from>to)return 'From date must be on or before To date.';
 if((Date.parse(to)-Date.parse(from))/86_400_000>366)return 'Choose a window of at most 366 days.';
 return '';
}
/** Strings only: no float conversion, implicit rounding or comma stripping of invalid groups. */
export function exactInterestAmount(value:string){
 const raw=value.trim();
 if(!/^[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?$/.test(raw))throw new Error('Enter an exact amount, for example 1,234.56.');
 const result=raw.replaceAll(',','').replace(/^\+/,''),[whole,fraction='']=result.replace(/^-/,'').split('.');
 if(whole.replace(/^0+/,'').length>18||fraction.length>12)throw new Error('Use at most 18 whole digits and 12 decimal places; amounts are never rounded.');
 return result;
}
export type InterestFields={instrumentId:string;currencyId:string;valueDate:string;amount:string;source:string;reason?:string;openingBalance?:string;closingBalance?:string;balanceMovements?:string};
function identity(fields:InterestFields,row?:DailyInterestInput|ClosingBalanceInput){
 if(!fields.instrumentId)throw new InterestFieldError('instrumentId','Choose a bond.');
 if(!fields.currencyId)throw new InterestFieldError('currencyId','Choose a currency.');
 if(!validDate(fields.valueDate))throw new InterestFieldError('valueDate','Enter a valid value date.');
 if(row&&(fields.instrumentId!==row.instrument_id||fields.currencyId!==row.currency_id||fields.valueDate!==row.value_date))throw new Error('A correction must preserve the original input identity.');
}
function source(value:string,max:number){const result=value.trim();if(!result||result.length>max)throw new InterestFieldError('sourceReference',`Enter a source reference of 1–${max} characters.`);return result;}
export function dailyInterestBody(strategyId:string,fields:InterestFields,row?:DailyInterestInput):Record<string,unknown>{
 identity(fields,row);
 const body:Record<string,unknown>={strategyId,instrumentId:fields.instrumentId,currencyId:fields.currencyId,valueDate:fields.valueDate,
  dailyEarned:fieldAmount(fields.amount),sourceReference:source(fields.source,500)};
 if(row){
  body.supersedesInputId=row.input_id;
  for(const key of ['eligibleNominal','eligibilityConvention'] as const)if(row.payload[key]!=null)body[key]=row.payload[key];
  if(row.payload.inputs){
   for(const key of ['policyId','cutId','reportingCurrencyId'] as const){if(!row.payload[key])throw new Error('Retained reconciliation context is incomplete. Reload the source before correcting it.');body[key]=row.payload[key];}
   for(const key of ['openingBalance','closingBalance','balanceMovements'] as const)body[key]=fieldAmount(fields[key]??row.payload.inputs[key],key);
  }
 }
 return body;
}
export function closingBalanceBody(strategyId:string,fields:InterestFields,row?:ClosingBalanceInput,withdraw=false):Record<string,unknown>{
 identity(fields,row);if(withdraw&&(!row||row.status!=='ACTIVE'))throw new Error('Only a current active closing-balance input can be withdrawn.');
 const reason=(fields.reason??'').trim();if(!reason||reason.length>2000)throw new InterestFieldError('reason','Enter an assessment or correction reason of 1–2000 characters.');
 return {strategyId,instrumentId:fields.instrumentId,currencyId:fields.currencyId,valueDate:fields.valueDate,closingBalance:withdraw?null:fieldAmount(fields.amount),
  status:withdraw?'WITHDRAWN':'ACTIVE',sourceReference:source(fields.source,2000),reason,...(row?{supersedesInputId:row.input_id}:{})};
}
export function filterInterestRows<T extends {instrument_id:string}>(rows:T[],instrument:string){return instrument?rows.filter(row=>row.instrument_id===instrument):rows;}
