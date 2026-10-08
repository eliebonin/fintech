import {describe,it,expect,vi} from 'vitest';
import {referenceFetch} from './reference-fetch';
describe('reference API deadline',()=>{
  it('adds a deadline without discarding caller cancellation',async()=>{
    const controller=new AbortController();controller.abort();
    const fetch=vi.fn(async(_input:RequestInfo|URL,_init?:RequestInit)=>new Response('{}'));
    await referenceFetch(fetch)('http://api.test',{signal:controller.signal,method:'POST',body:'{}'});
    const init=fetch.mock.calls[0][1] as RequestInit;
    expect(init.signal?.aborted).toBe(true);expect(init.method).toBe('POST');expect(init.body).toBe('{}');
  });
});
