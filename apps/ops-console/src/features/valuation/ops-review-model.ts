import type {Item,Presentation} from './types';

export function positionLabel(item:Pick<Item,'subject_id'|'trade_id'|'cash_account_id'>,presentation?:Pick<Presentation,'references'|'cashAccounts'|'instrumentDisplays'>){
 if(item.cash_account_id)return presentation?.cashAccounts?.[item.cash_account_id]??'Cash account name unavailable';
 if(presentation?.instrumentDisplays)return presentation.instrumentDisplays[item.subject_id??'']?.primaryName??'Instrument name unavailable';
 return presentation?.references[item.subject_id??'']??(item.subject_id?'Instrument name unavailable':'Historical trade attribution');
}
/** Current accessible classification is navigation metadata, never a valuation rule. */
export function positionInstrumentType(item:Pick<Item,'subject_id'>,presentation?:Pick<Presentation,'instrumentTypes'>){
 return presentation?.instrumentTypes?.[item.subject_id??'']??{code:'UNKNOWN',label:'Type unavailable'};
}
export function positionContext(item:Pick<Item,'evidence'>,presentation?:Pick<Presentation,'currencies'>){
 if((item.evidence as {resultFormat?:string}|null)?.resultFormat==='ACCRUED_RECEIVABLE_V1')return 'Outstanding accrued interest · security holding closed';
 const cash=(item.evidence as {cashFx?:{currency_id?:string}}|null)?.cashFx;
 if(cash)return `Cash · ${presentation?.currencies[cash.currency_id??'']??'Currency name unavailable'} · opening-balance FX`;
 const key=(item.evidence as {identity?:{bucket?:{key?:{currency_id?:string;quantity_unit?:string;unit_multiplier?:string;quote_factor?:string}}}}|null)?.identity?.bucket?.key;
 if(!key)return '';
 return [presentation?.currencies[key.currency_id??''],key.quantity_unit,key.unit_multiplier?`multiplier ${key.unit_multiplier}`:'',key.quote_factor?`quote factor ${key.quote_factor}`:''].filter(Boolean).join(' · ');
}
export function positionAttention(item:Item):string[]{
 if(item.display)return item.display.attention;
 const evidence=item.evidence as {economicInputs?:{kind:string;days?:{reason?:string|null;balance?:{warnings?:string[]}}[]}[];selections?:{staleness_business_days?:number|null}[]}|null;
 const inputs=evidence?.economicInputs??[],notes=new Set<string>();
 if(inputs.some(i=>i.kind==='MISSING_DAILY_ACCRUAL'))notes.add('Interest not supplied');
 if(inputs.some(i=>i.kind==='MISSING_DAILY_ACCRUAL_FX'))notes.add('Interest FX unavailable');
 const days=inputs.filter(i=>i.kind==='ACCRUED_BALANCE_FX').flatMap(i=>i.days??[]);
 if(days.some(d=>d.reason==='ACCRUED_BALANCE_FX_UNAVAILABLE'))notes.add('Accrued FX unavailable');
 if(days.some(d=>d.reason&&d.reason!=='ACCRUED_BALANCE_FX_UNAVAILABLE'))notes.add('Accrued balance unavailable');
 if(days.some(d=>d.balance?.warnings?.some(w=>w.includes('ANCHOR_DIFFERS'))))notes.add('Accrued balance mismatch');
 if(days.some(d=>d.balance?.warnings?.some(w=>['TRADE_ACCRUAL_UNAVAILABLE','COUPON_CURRENCY_CONVERSION_UNAVAILABLE'].includes(w))))notes.add('Accrued movements unavailable');
 if(evidence?.selections?.some(s=>(s.staleness_business_days??0)>0))notes.add('Prior-session input');
 return [...notes];
}
function compareDecimal(a:string,b:string){
 if(!/^-?\d+(\.\d+)?$/.test(a)||!/^-?\d+(\.\d+)?$/.test(b))return 0;
 const scale=Math.max(a.split('.')[1]?.length??0,b.split('.')[1]?.length??0);
 const integer=(value:string)=>{const [whole,fraction='']=value.split('.');return BigInt(`${whole}${fraction.padEnd(scale,'0')}`);};
 const left=integer(a),right=integer(b);return left<right?-1:left>right?1:0;
}
/** Ordering/filtering stored rows only. Never calculate or allocate financial values. */
export function selectPositionRows(items:Item[],presentation:Presentation|undefined,filters:{query:string;attentionOnly:boolean;sort:string;instrumentType?:string;componentCodes?:string[]}){
 const query=filters.query.trim().toLocaleLowerCase();
 return items.filter(item=>(!query||`${positionLabel(item,presentation)} ${presentation?.instrumentDisplays?.[item.subject_id??'']?.searchText??''} ${positionContext(item,presentation)}`.toLocaleLowerCase().includes(query))&&
  (!filters.attentionOnly||positionAttention(item).length>0)&&
  (!filters.instrumentType||positionInstrumentType(item,presentation).code===filters.instrumentType)&&
  (!filters.componentCodes?.length||filters.componentCodes.some(code=>Object.hasOwn(item.components,code)))).sort((a,b)=>filters.sort==='pnl-desc'?
  compareDecimal(b.net_pnl??b.market_pnl,a.net_pnl??a.market_pnl)||a.attribution_id.localeCompare(b.attribution_id):
  positionLabel(a,presentation).localeCompare(positionLabel(b,presentation))||a.attribution_id.localeCompare(b.attribution_id));
}
