import {afterEach,expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({slots:[] as any[],cursor:0,request:vi.fn()}));
vi.mock('react',()=>({useCallback:(f:unknown)=>f,useEffect:()=>{},useState:(v:unknown)=>{const i=h.cursor++;if(!(i in h.slots))h.slots[i]=v;return[h.slots[i],(next:any)=>h.slots[i]=typeof next==='function'?next(h.slots[i]):next];}}));
vi.mock('@/lib/access-administration',()=>({accessRequest:h.request}));
import {useAccessData} from './access-loader';
const render=()=>{h.cursor=0;return useAccessData('/api/access',{version:1});};
afterEach(()=>{h.slots=[];h.request.mockReset();});
it('locks stale data after a committed write and failed refresh, recovering by read only',async()=>{
 h.request.mockResolvedValueOnce({saved:true}).mockRejectedValueOnce(new Error('offline'));
 expect(await render().command('/api/access/users',{},'PUT')).toBe(false);
 expect(render().stale).toBe(true);expect(render().error).toContain('saved');
 expect(await render().command('/api/access/users',{},'PUT')).toBe(false);
 expect(h.request).toHaveBeenCalledTimes(2);
 h.request.mockResolvedValueOnce({version:2});expect(await render().reload()).toBe(true);
 expect(render().stale).toBe(false);expect(render().data).toEqual({version:2});
});
