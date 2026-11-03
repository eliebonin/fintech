import {afterEach,expect,it,vi} from 'vitest';
import {readInterest,writeInterest} from './interest-api';
import {submitRetained,type RetainedIntent} from '@/lib/retained-mutation';
import type {InterestIntent} from './interest-types';
afterEach(()=>{vi.unstubAllGlobals();vi.useRealTimers();});
it('retries only read-only capacity responses after the server delay',async()=>{
 vi.useFakeTimers();const fetch=vi.fn().mockResolvedValueOnce(Response.json({detail:'Busy'},{status:429,headers:{'Retry-After':'5'}})).mockResolvedValueOnce(Response.json({items:[]}));vi.stubGlobal('fetch',fetch);
 const request=readInterest('interest-review',new AbortController().signal);
 await Promise.resolve();await Promise.resolve();
 await vi.advanceTimersByTimeAsync(4999);expect(fetch).toHaveBeenCalledTimes(1);
 await vi.advanceTimersByTimeAsync(1);expect(await request).toEqual({items:[]});expect(fetch).toHaveBeenCalledTimes(2);
 expect(fetch.mock.calls.every(call=>!call[1].method||call[1].method==='GET')).toBe(true);
});
it('cancels a pending read retry when the scope changes',async()=>{
 vi.useFakeTimers();const fetch=vi.fn().mockResolvedValue(Response.json({detail:'Busy'},{status:429,headers:{'Retry-After':'5'}}));vi.stubGlobal('fetch',fetch);
 const controller=new AbortController(),request=readInterest('interest-review',controller.signal),rejected=expect(request).rejects.toMatchObject({name:'AbortError'});
 await Promise.resolve();await Promise.resolve();controller.abort();await rejected;await vi.advanceTimersByTimeAsync(6000);expect(fetch).toHaveBeenCalledTimes(1);
});
it('retains an exact mutation after a malformed success and retries the same payload/key',async()=>{
 const receipt={input_id:'retained-input',strategy_id:'s',instrument_id:'b',currency_id:'c',value_date:'2026-10-20'};
 const fetch=vi.fn().mockResolvedValueOnce(Response.json({ok:true})).mockResolvedValueOnce(Response.json(receipt));
 vi.stubGlobal('fetch',fetch);
 const state:{current:RetainedIntent|null}={current:null},intent:InterestIntent={path:'balance-inputs',body:{strategyId:'s',instrumentId:'b',currencyId:'c',valueDate:'2026-10-20',closingBalance:'1000000.123456789012',status:'ACTIVE'}};
 await expect(submitRetained(intent,state,writeInterest)).rejects.toThrow(/incomplete confirmation/);
 expect(state.current).not.toBeNull();const key=state.current!.key;
 await submitRetained(intent,state,writeInterest);
 expect(state.current).toBeNull();
 const first=fetch.mock.calls[0][1],second=fetch.mock.calls[1][1];
 expect(first.body).toBe(second.body);expect(first.headers['Idempotency-Key']).toBe(key);expect(second.headers['Idempotency-Key']).toBe(key);
});
it('does not acknowledge a receipt for another instrument',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(Response.json({input_id:'retained-input',strategy_id:'s',instrument_id:'other',currency_id:'c',value_date:'2026-10-20'})));
 const state:{current:RetainedIntent|null}={current:null};
 await expect(submitRetained({path:'accrual-inputs',body:{strategyId:'s',instrumentId:'b',currencyId:'c',valueDate:'2026-10-20'}} as InterestIntent,state,writeInterest)).rejects.toThrow(/incomplete confirmation/);
 expect(state.current).not.toBeNull();
});
it('allows editing after a definitive server validation rejection',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(Response.json({error:{message:'Revision changed',code:'valuation.invalid_input'}},{status:422})));
 const state:{current:RetainedIntent|null}={current:null};
 await expect(submitRetained({path:'balance-inputs',body:{}} as InterestIntent,state,writeInterest)).rejects.toThrow();
 expect(state.current).toBeNull();
});
