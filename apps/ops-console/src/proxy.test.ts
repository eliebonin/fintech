import {expect,it,vi} from 'vitest';
import {NextRequest} from 'next/server';
vi.mock('server-only',()=>({}));
import {proxy} from './proxy';
import {contextFingerprint} from './lib/server/context-fingerprint';

function request(path='/api/market-data/sources',method='POST',expected?:string,cookie='session-a'){
 return new NextRequest('http://console.test'+path,{method,headers:{Cookie:`local_access_session=${cookie}`,
  ...(expected?{'X-Page-Context':expected}:{})}});
}
it('rejects a stale document before any mutation handler runs',()=>{
 const stale=contextFingerprint('session-a',undefined)!;
 const response=proxy(request(undefined,undefined,stale,'session-b'));
 expect(response.status).toBe(409);
});
it('fails closed for unbound API mutations but allows same-context writes',()=>{
 expect(proxy(request()).status).toBe(409);
 expect(proxy(request(undefined,undefined,contextFingerprint('session-a',undefined)!)).headers.get('x-middleware-next')).toBe('1');
});
it('keeps reads and explicit session switches available',()=>{
 expect(proxy(request(undefined,'GET')).headers.get('x-middleware-next')).toBe('1');
 expect(proxy(request('/api/session/context')).headers.get('x-middleware-next')).toBe('1');
 expect(proxy(request('/api/session/context','DELETE')).headers.get('x-middleware-next')).toBe('1');
});
