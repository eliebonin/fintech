import {expect,it} from 'vitest';
import {reportingLabel,exactQuantity} from './presentation';
it('distinguishes preparation readiness from inclusion and legal assessment',()=>{
 expect(reportingLabel('READY')).toBe('Preparation checks passed');
 expect(reportingLabel('NEEDS_ASSESSMENT')).toBe('Needs assessment');
 expect(reportingLabel('HOLD')).toBe('Held');
});
it('formats exact quantities without float coercion',()=>{
 expect(exactQuantity('123456789.123456789012')).toBe('123,456,789.123456789012');
 expect(exactQuantity('-2500')).toBe('-2,500');
 expect(exactQuantity(null)).toBe('Not supplied');
});
