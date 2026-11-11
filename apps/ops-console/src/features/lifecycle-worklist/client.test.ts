import {beforeEach,expect,it,vi} from 'vitest';
const transport=vi.hoisted(()=>vi.fn(async(_url:string,_init?:RequestInit)=>({ok:true,json:async()=>({items:[]})})));
vi.mock('@/lib/browser-fetch',()=>({browserFetch:transport}));
import {worklistRead} from './client';
beforeEach(()=>transport.mockClear());
it('does not start a read for an effect abandoned in the same render turn',async()=>{
 const controller=new AbortController();const read=worklistRead('tenant','worklist?limit=25',controller.signal);controller.abort();
 await expect(read).rejects.toThrow();expect(transport).not.toHaveBeenCalled();
});
it('starts an active scoped read without sharing data across contexts',async()=>{
 const controller=new AbortController();await worklistRead('tenant','worklist?limit=25',controller.signal);
 expect(transport).toHaveBeenCalledOnce();expect(transport.mock.calls[0]?.[0]).toBe('/api/lifecycle/worklist?limit=25');
});
