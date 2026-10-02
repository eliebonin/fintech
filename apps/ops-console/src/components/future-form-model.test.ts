import {expect,it} from 'vitest';
import {futureSymbol,deliveryMonths,allowedFutureMonth} from './future-form-model';
it('shows one or two year digits without changing the full canonical year',()=>{expect(futureSymbol('BTC','2027-03',1)).toBe('BTCH7');expect(futureSymbol('BTC','2027-03',2)).toBe('BTCH27');expect(futureSymbol('BTC','2037-03',1)).toBe('BTCH7');});
it('maps all delivery month letters and rejects malformed months',()=>{expect(Array.from({length:12},(_,i)=>futureSymbol('R',`2027-${String(i+1).padStart(2,'0')}`,2)).join(',')).toBe('RF27,RG27,RH27,RJ27,RK27,RM27,RN27,RQ27,RU27,RV27,RX27,RZ27');expect(futureSymbol('R','2027-13',1)).toBe('—');});
it('handles monthly, quarterly and custom cycles',()=>{expect(deliveryMonths('MONTHLY',[])).toHaveLength(12);expect(deliveryMonths('QUARTERLY',[])).toEqual([3,6,9,12]);expect(deliveryMonths('CUSTOM',[12,2])).toEqual([2,12]);expect(allowedFutureMonth('2027-02',[3,6,9,12])).toBe(false);});
