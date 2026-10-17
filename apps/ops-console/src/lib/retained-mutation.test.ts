import {expect,it} from 'vitest';
import {submitRetained,type RetainedIntent} from './retained-mutation';
import {BffApiError} from './api-errors';

it('retains exact payload and key after an uncertain outcome and blocks edited intent',async()=>{
 const state:{current:RetainedIntent|null}={current:null};
 const sent:{body:unknown;key:string}[]=[];
 const send=async(body:unknown,key:string)=>{sent.push({body,key});if(sent.length===1)throw new Error('Connection lost');return 'saved';};
 await expect(submitRetained({amount:'0.00000001'},state,send)).rejects.toThrow('Connection lost');
 await expect(submitRetained({amount:'2'},state,send)).rejects.toThrow('Retry the unchanged request');
 expect(sent).toHaveLength(1);
 expect(await submitRetained({amount:'0.00000001'},state,send)).toBe('saved');
 expect(sent[1]).toEqual(sent[0]);expect(state.current).toBeNull();
 await submitRetained({amount:'3'},state,send);expect(sent[2].key).not.toBe(sent[0].key);
});
it('releases rejected validation intent, but not timeout or server-error intent',async()=>{
 const state:{current:RetainedIntent|null}={current:null};
 await expect(submitRetained({n:1},state,async()=>{throw new BffApiError(422,'Invalid');})).rejects.toThrow('Invalid');
 expect(state.current).toBeNull();
 await expect(submitRetained({n:2},state,async()=>{throw new BffApiError(503,'Unavailable');})).rejects.toThrow();
 expect(state.current).not.toBeNull();
});
