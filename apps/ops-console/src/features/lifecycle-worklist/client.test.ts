import {beforeEach,expect,it,vi} from 'vitest';
const transport=vi.hoisted(()=>vi.fn(async(_url:string,_init?:RequestInit)=>({ok:true,json:async()=>({items:[]})})));
vi.mock('@/lib/browser-fetch',()=>({browserFetch:transport}));
import {worklistRead,queryFor} from './client';
beforeEach(()=>transport.mockClear());
it('does not start a read for an effect abandoned in the same render turn',async()=>{
 const controller=new AbortController();const read=worklistRead('tenant','worklist?limit=25',controller.signal);controller.abort();
 await expect(read).rejects.toThrow();expect(transport).not.toHaveBeenCalled();
});
it('starts an active scoped read without sharing data across contexts',async()=>{
 const controller=new AbortController();await worklistRead('tenant','worklist?limit=25',controller.signal);
 expect(transport).toHaveBeenCalledOnce();expect(transport.mock.calls[0]?.[0]).toBe('/api/lifecycle/worklist?limit=25');
});

it('includes the selected event type in the server filter query',()=>{
 const filters={fromDate:'2026-10-01',toDate:'2026-12-01',strategyId:'',strategyLabel:'All',attention:'ALL',status:'ALL',includeEarlierOverdue:true,offset:25,limit:25 as const,eventType:'FX_FORWARD_MATURITY' as const};
 expect(queryFor(filters).get('eventType')).toBe('FX_FORWARD_MATURITY');
});
