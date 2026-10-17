import {it,expect,vi} from 'vitest';
import {openValuationInputs} from './valuation-navigation';
it('activates the input tab before opening and focusing its register',()=>{
 const order:string[]=[];const disclosure={open:false};
 const element={closest:()=>disclosure,setAttribute:vi.fn(),focus:()=>order.push('focus'),scrollIntoView:vi.fn()};
 vi.stubGlobal('document',{getElementById:()=>element});vi.stubGlobal('requestAnimationFrame',(fn:()=>void)=>{fn();return 1;});
 openValuationInputs(()=>order.push('activate'));
 expect(order).toEqual(['activate','focus']);expect(disclosure.open).toBe(true);expect(element.setAttribute).toHaveBeenCalledWith('tabindex','-1');
 vi.unstubAllGlobals();
});
