/** Base-10 coefficients only. Number is used for bounded scales, never monetary values. */
export type BookingDecimal = {value:bigint;scale:number};
type Limits = {integerDigits:number;fractionDigits:number};
const databaseLimits:Limits={integerDigits:18,fractionDigits:12};
const ZERO=BigInt(0),ONE=BigInt(1),TEN=BigInt(10);

export function parseBookingDecimal(text:string,limits:Limits=databaseLimits):BookingDecimal|null {
  if(text.length>80)return null;
  text=text.replace(/^(-?)\./,'$10.');
  const match=/^(-?\d+)(?:\.(\d+))?(?:[eE]([+-]?\d{1,2}))?$/.exec(text);
  if(!match)return null;
  const fraction=match[2]??'';
  if(!match[3]&&(match[1].replace('-','').length>limits.integerDigits||fraction.length>limits.fractionDigits))return null;
  let value=BigInt(match[1]+fraction),scale=fraction.length-Number(match[3]??0);
  if(scale<0){value*=TEN**BigInt(-scale);scale=0;}
  while(scale>0&&value%TEN===ZERO){value/=TEN;scale--;}
  const integerDigits=(value<ZERO?-value:value).toString().length-scale;
  if(scale>limits.fractionDigits||integerDigits>limits.integerDigits)return null;
  return {value,scale};
}

export function formatBookingDecimal(value:bigint,scale:number):string {
  if(value===ZERO)return '0';
  const negative=value<ZERO,digits=(negative?-value:value).toString().padStart(scale+1,'0');
  const text=scale?`${digits.slice(0,-scale)}.${digits.slice(-scale)}`.replace(/0+$/,'').replace(/\.$/,''):digits;
  return `${negative?'-':''}${text}`;
}

export function exactBookingAmount(factors:string[],divisor='1',limits:Limits=databaseLimits):string {
  const parts=factors.map(value=>parseBookingDecimal(value,limits)),denom=parseBookingDecimal(divisor,limits);
  if(!parts.length||parts.some(value=>!value)||!denom||denom.value<=ZERO)return '—';
  const values=parts as BookingDecimal[];
  const numerator=values.reduce((value,next)=>value*next.value,ONE)*TEN**BigInt(denom.scale+12);
  const denominator=denom.value*TEN**BigInt(values.reduce((scale,next)=>scale+next.scale,0));
  if(numerator%denominator!==ZERO)return '—';
  const result=numerator/denominator;
  if((result<ZERO?-result:result)>=TEN**BigInt(30))return '—';
  return formatBookingDecimal(result,12);
}

/** Legacy cash/FX multiplication preview; consumers separately validate execution bounds. */
export function multiplyBookingDecimals(factors:string[]):string {
  const parts=factors.map(value=>parseBookingDecimal(value,{integerDigits:80,fractionDigits:80}));
  if(!parts.length||parts.some(value=>!value||value.value<ZERO))return '—';
  const values=parts as BookingDecimal[];
  return formatBookingDecimal(values.reduce((value,next)=>value*next.value,ONE),values.reduce((scale,next)=>scale+next.scale,0));
}
