import {describe,expect,it} from 'vitest';
import {parseBookingDecimal,formatBookingDecimal,exactBookingAmount} from './booking-decimal';

describe('exact booking decimals',()=>{
  it.each([['1E-12',BigInt(1),12],['2.500E+2',BigInt(250),0],['-.25',BigInt(-25),2],['-0',BigInt(0),0]])('parses %s without monetary floats',(text,value,scale)=>{
    expect(parseBookingDecimal(text)).toEqual({value,scale});
  });
  it.each(['1E999','NaN','Infinity','1000000000000000000','0.0000000000001',''])('refuses unsupported %s',text=>expect(parseBookingDecimal(text)).toBeNull());
  it.each([
    [['400000','2'],'100','8000'],[['-200000','-2'],'100','4000'],
    [['1E-12','1'],'1E-8','0.0001'],[['1000000','1.10'],'1','1100000'],
    [['10','2.5','100'],'1','2500'],[['100000','98.5'],'100','98500'],
    [['2','6000','50'],'1','600000'],[['0','-2'],'100','0'],
    [['1'],'3','—'],[['999999999999999999','2'],'1','—'],
  ])('calculates %j / %s exactly',(factors,divisor,expected)=>expect(exactBookingAmount(factors,divisor)).toBe(expected));
  it('normalizes negative zero and preserves significant fractional digits',()=>{
    expect(formatBookingDecimal(BigInt(0),12)).toBe('0');
    expect(formatBookingDecimal(BigInt(-123400),5)).toBe('-1.234');
  });
});
