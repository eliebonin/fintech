import {formatTradeExactDecimal} from './trades';

/** Display-only, half-away-from-zero to two decimals. Never changes stored amounts. */
export function formatMeasureDisplay(amount:string):string {
 const match=/^(-?)(\d+)(?:\.(\d+))?$/.exec(amount);
 if(!match)return formatTradeExactDecimal(amount);
 const [,negative,integer,fraction='']=match;
 const nonzero=/[1-9]/.test(integer+fraction);
 const hundred=BigInt(100),zero=BigInt(0);
 const cents=BigInt(integer)*hundred+BigInt((fraction+'00').slice(0,2));
 if(nonzero&&cents===zero)return negative?'−<0.01':'<0.01';
 const rounded=cents+(fraction.length>2&&fraction[2]>='5'?BigInt(1):zero);
 const whole=formatTradeExactDecimal(String(rounded/hundred));
 return `${negative&&rounded!==zero?'-':''}${whole}.${String(rounded%hundred).padStart(2,'0')}`;
}
