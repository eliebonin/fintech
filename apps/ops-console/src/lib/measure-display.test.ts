import {expect,it} from 'vitest';
import {formatMeasureDisplay} from './measure-display';

it.each([
 ['15654.91341903484424450337888','15,654.91'],
 ['999.995','1,000.00'],['-999.995','-1,000.00'],
 ['9007199254740993.125','9,007,199,254,740,993.13'],
 ['-0.000000001','−<0.01'],['0.000000001','<0.01'],
 ['0','0.00'],['-0.00','0.00'],['12.5','12.50'],
])('formats %s for scanning without floating-point conversion',(amount,expected)=>{
 expect(formatMeasureDisplay(amount)).toBe(expected);
});
