import {expect,it} from 'vitest';
import {moveSource,initialOrder} from './market-data-sources';

it('moves sources without losing exclusions or duplicating entries',()=>{
 expect(moveSource(['a','b','c'],'b',-1)).toEqual(['b','a','c']);
 expect(moveSource(['a','b'],'a',-1)).toEqual(['a','b']);
 expect(moveSource(['a','b'],'missing',1)).toEqual(['a','b']);
});
it('suggests tenant sources first only when no saved order exists',()=>{
 const sources=[{datasetId:'a',tenantOwned:false},{datasetId:'b',tenantOwned:true}];
 expect(initialOrder(sources,null)).toEqual(['b','a']);
 expect(initialOrder(sources,[])).toEqual([]);
 expect(initialOrder(sources,['a'])).toEqual(['a']);
});
