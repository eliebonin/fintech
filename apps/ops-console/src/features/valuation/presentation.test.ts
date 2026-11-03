import {expect,it} from 'vitest';
import {displayAmount} from './presentation';

it.each([
 ['0.000001','<0.01'],['-0.000001','−<0.01'],
 ['0.005','<0.01'],['-0.005','−<0.01'],
 ['0.0000000000000000000000000000000000000000000000000000000000001','<0.01'],
 ['-0.0000000000000000000000000000000000000000000000000000000000001','−<0.01'],
])('does not turn nonzero amount %s into a zero or lose its sign',(value,want)=>{
 expect(displayAmount(value)).toBe(want);
});

it.each([
 ['0','0.00'],['-0.000000','0.00'],['0.005000000001','0.01'],['-0.005000000001','-0.01'],
 ['0.009999','0.01'],['1.005','1.00'],['-1.015','-1.02'],
 ['999999999999999999.995','1,000,000,000,000,000,000.00'],
 ['unknown','—'],['','—'],
])('keeps exact zero, normal half-even rounding and unavailable semantics for %s',(value,want)=>{
 expect(displayAmount(value)).toBe(want);
});
