import {expect,it,vi} from 'vitest';
vi.mock('next/navigation',()=>({redirect:(path:string)=>{throw new Error('redirect:'+path);}}));
import Page from './page';
it('routes legacy tenant-selection links to the actor-aware selector',()=>{
 expect(()=>Page()).toThrow('redirect:/select-context');
});
