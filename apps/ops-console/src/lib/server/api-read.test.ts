import {afterEach,expect,it,vi} from 'vitest';
import {apiRead} from './api-read';
import {referenceFetch} from '../reference-fetch';
afterEach(()=>vi.unstubAllEnvs());
const abortingFetch:typeof fetch=async(_input,init)=>new Promise((_resolve,reject)=>{const signal=init!.signal!;if(signal.aborted)reject(signal.reason);else signal.addEventListener('abort',()=>reject(signal.reason),{once:true});});
it('bounds a hanging read with the configured deadline',async()=>{vi.stubEnv('REFERENCE_API_READ_TIMEOUT_MS','15');await expect(apiRead('http://example.test',{},abortingFetch)).rejects.toMatchObject({name:'TimeoutError'});});
it('preserves caller cancellation',async()=>{const controller=new AbortController();const result=apiRead('http://example.test',{signal:controller.signal},abortingFetch);controller.abort();await expect(result).rejects.toMatchObject({name:'AbortError'});});
it('keeps the write deadline at 35 seconds without retrying',async()=>{vi.stubEnv('REFERENCE_API_READ_TIMEOUT_MS','1');const response=await referenceFetch(async(_input,init)=>{await new Promise(resolve=>setTimeout(resolve,20));expect(init!.signal!.aborted).toBe(false);return Response.json({ok:true});})('http://example.test',{method:'POST'});expect(response.ok).toBe(true);});
