import {expect,it} from 'vitest';
import {forwardWorkloadHeaders} from './workload-response';

it('retains bounded busy retry guidance and correlation without forwarding unrelated headers',()=>{
 const upstream=new Response('',{status:429,headers:{'Retry-After':'5','X-Request-ID':'10000000-0000-4000-8000-000000000001','Set-Cookie':'untrusted=value'}});
 const response=forwardWorkloadHeaders(upstream,new Response(''));
 expect(response.headers.get('Retry-After')).toBe('5');expect(response.headers.get('X-Request-ID')).toBe('10000000-0000-4000-8000-000000000001');
 expect(response.headers.has('Set-Cookie')).toBe(false);expect(response.headers.get('Cache-Control')).toBe('no-store');
});
