import {expect,it} from 'vitest';
import {formatTradeNumber} from './trades';
it.each([['9007199254740993.123456','9,007,199,254,740,993.123456'],['0.00000001','0.00000001'],['-1.000000001','-1.000000001']])('retains exact cash/fee decimal %s',(input,want)=>expect(formatTradeNumber(input)).toBe(want));
