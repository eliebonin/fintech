/** Display-only half-even rounding; never disguise a signed nonzero as zero. */
export function displayAmount(value: string | undefined): string {
 if(!value || !/^-?\d+(\.\d+)?$/.test(value)) return '—';
 const negative=value.startsWith('-');const [whole,fraction='']=(negative?value.slice(1):value).split('.');
 let pennies=BigInt(whole)*BigInt(100)+BigInt((fraction+'00').slice(0,2));
 const tail=fraction.slice(2);const halfway=tail.startsWith('5')&&!/[1-9]/.test(tail.slice(1));
 if(tail && (tail[0]>'5'||tail[0]==='5'&&(!halfway||pennies%BigInt(2)===BigInt(1))))pennies++;
 // Inspect the original digits, not a Number conversion which can underflow.
 if(pennies===BigInt(0)&&/[1-9]/.test(whole+fraction))return negative?'−<0.01':'<0.01';
 const digits=pennies.toString().padStart(3,'0');
 return `${negative&&pennies!==BigInt(0)?'-':''}${digits.slice(0,-2).replace(/\B(?=(\d{3})+(?!\d))/g,',')}.${digits.slice(-2)}`;
}
export const componentLabel=(name:string)=>({PRICE:'Price movement',FX:'FX movement',PRICE_FX_CROSS:'Price × FX',MODEL_MARK_CHANGE:'Model mark change',ACCRUAL:'Interest earned',CARRY:'FX on accrued interest',ADJUSTMENT:'Controlled adjustment'}[name]??name.toLowerCase().replaceAll('_',' '));
export function displayTime(value:string){const date=new Date(value);return Number.isNaN(date.valueOf())?value:new Intl.DateTimeFormat('en-GB',{dateStyle:'medium',timeStyle:'short',timeZone:'Europe/London'}).format(date);}
