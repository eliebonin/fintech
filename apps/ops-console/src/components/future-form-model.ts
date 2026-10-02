export const FUTURE_MONTHS=[['F','January'],['G','February'],['H','March'],['J','April'],['K','May'],['M','June'],['N','July'],['Q','August'],['U','September'],['V','October'],['X','November'],['Z','December']] as const;
export function futureSymbol(root:string,month:string,digits:1|2):string {
  if(!/^[A-Z0-9]+$/.test(root)||!/^\d{4}-(0[1-9]|1[0-2])$/.test(month))return '—';
  return `${root}${FUTURE_MONTHS[Number(month.slice(5))-1][0]}${month.slice(0,4).slice(-digits)}`;
}
export function deliveryMonths(cycle:string,custom:number[]):number[]{return cycle==='MONTHLY'?Array.from({length:12},(_,i)=>i+1):cycle==='QUARTERLY'?[3,6,9,12]:[...custom].sort((a,b)=>a-b);}
export function allowedFutureMonth(month:string,allowed:number[]):boolean{return /^\d{4}-(0[1-9]|1[0-2])$/.test(month)&&allowed.includes(Number(month.slice(5)));}
