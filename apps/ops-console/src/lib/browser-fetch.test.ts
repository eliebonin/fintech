import {afterEach,expect,it,vi} from 'vitest';
import {browserFetch} from './browser-fetch';
afterEach(()=>vi.unstubAllGlobals());
it('echoes the rendered context without reading mutable session cookies',async()=>{
 let sent:RequestInit|undefined;
 vi.stubGlobal('window',{location:{href:'http://console.test/trades',origin:'http://console.test'}});
 vi.stubGlobal('document',{querySelector:()=>({content:'page-before-switch'})});
 vi.stubGlobal('fetch',async(_input:unknown,init:RequestInit)=>{sent=init;return Response.json({ok:true});});
 await browserFetch('/api/market-data/sources',{method:'POST',body:'{}'});
 expect(new Headers(sent?.headers).get('X-Page-Context')).toBe('page-before-switch');
});
it('does not forward context to other origins or attach it to reads',async()=>{
 vi.stubGlobal('window',{location:{href:'http://console.test/',origin:'http://console.test'}});
 vi.stubGlobal('document',{querySelector:()=>({content:'private-context'})});
 const headers:string[]=[];
 vi.stubGlobal('fetch',async(_input:unknown,init:RequestInit)=>{headers.push(new Headers(init?.headers).get('X-Page-Context')??'');return Response.json({});});
 await browserFetch('https://other.test/api/write',{method:'POST'});await browserFetch('/api/strategies');
 expect(headers).toEqual(['','']);
});
