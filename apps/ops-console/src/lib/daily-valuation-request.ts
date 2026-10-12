export function dailyValuationRequest(fields:FormData,scope:Record<string,string>,now=new Date().toISOString()):Record<string,string>{
 return {...scope,openingDate:String(fields.get('openingDate')??''),closingDate:String(fields.get('closingDate')??''),
  informationCutoff:String(fields.get('informationCutoff')||now)};
}

export class ValuationHttpError extends Error{
 constructor(public status:number,message:string,public validationRejected=false){super(message);}
}
export function valuationError(response:{status:number},body:Record<string,any>){
 const fields=body.errors?.map((item:any)=>`${(item.location??item.loc??[]).filter((x:string)=>x!=='body').join('.')||'Request'}: ${item.message??item.msg}`).join('; ');
 const bffFields=Object.entries(body.error?.fieldErrors??{}).map(([key,value])=>`${key}: ${Array.isArray(value)?value.join('; '):value}`).join('; ');
 return new ValuationHttpError(response.status,fields||bffFields||body.detail||body.error?.message||'Valuation request failed.',
  response.status===422&&[body.code,body.error?.code].includes('request.validation_failed'));
}
