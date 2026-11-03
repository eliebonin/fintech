import {beforeEach,expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({cell:null as unknown,effect:null as null|(()=>void|(()=>void)),read:vi.fn()}));
vi.mock('react',()=>({useState:(initial:unknown)=>{if(h.cell===null)h.cell=initial;return [h.cell,(value:unknown)=>{h.cell=value;}];},useEffect:(effect:()=>void|(()=>void))=>{h.effect=effect;}}));
vi.mock('./interest-api',()=>({readInterest:h.read}));
import {useInterestData} from './use-interest-data';
beforeEach(()=>{h.cell=null;h.effect=null;h.read.mockReset();});
const valid=(value:unknown)=>Array.isArray(value);
it('hides old data immediately when changing strategy and ignores obsolete responses',async()=>{
 let oldResolve!:(value:string[])=>void,newResolve!:(value:string[])=>void;
 h.read.mockImplementationOnce(()=>new Promise(resolve=>{oldResolve=resolve;})).mockImplementationOnce(()=>new Promise(resolve=>{newResolve=resolve;}));
 expect(useInterestData<string[]>('daily?strategy=A',0,valid).loading).toBe(true);const cleanup=h.effect!() as ()=>void;
 cleanup();expect(useInterestData<string[]>('daily?strategy=B',0,valid).data).toBeNull();h.effect!();
 newResolve(['B']);await Promise.resolve();await Promise.resolve();
 oldResolve(['A']);await Promise.resolve();await Promise.resolve();
 expect(useInterestData<string[]>('daily?strategy=B',0,valid).data).toEqual(['B']);
 expect(h.read.mock.calls[0][1].aborted).toBe(true);
});
it('keeps malformed responses local to their dataset and offers a clean retry',async()=>{
 h.read.mockResolvedValue({incorrect:true});useInterestData('daily',0,valid);h.effect!();await Promise.resolve();await Promise.resolve();
 expect(useInterestData('daily',0,valid).error).toMatch(/incomplete/);
 expect(useInterestData('daily',1,valid)).toMatchObject({data:null,error:'',loading:true});
});
