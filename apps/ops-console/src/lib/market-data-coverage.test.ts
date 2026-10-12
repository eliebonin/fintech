import {expect,it} from 'vitest';
import {coverageRows,coverageTotals} from './market-data-coverage';
it('retains requirements with no resolver row as unknown, rather than excluding them',()=>{
 const rows=coverageRows(['a','b','c'],[{subjectReferenceNodeId:'a',status:'SELECTED',selectedValue:'0',entitlementDecision:'ALLOWED',exceptionCode:null},{subjectReferenceNodeId:'b',status:'MISSING',selectedValue:null,entitlementDecision:'ALLOWED',exceptionCode:'NO_DATA'}] as never);
 expect(rows).toHaveLength(3);expect(rows[2].state).toBe('unknown');
 expect(coverageTotals(rows)).toEqual({required:3,selected:1,exceptions:1,unknown:1});
});
it('does not label a selected row with missing value or restricted rights as usable',()=>{
 const rows=coverageRows(['a','b'],[{subjectReferenceNodeId:'a',status:'SELECTED',selectedValue:null,entitlementDecision:'ALLOWED',exceptionCode:null},{subjectReferenceNodeId:'b',status:'SELECTED',selectedValue:'10',entitlementDecision:'DENIED',exceptionCode:null}] as never);
 expect(coverageTotals(rows).selected).toBe(0);
});
